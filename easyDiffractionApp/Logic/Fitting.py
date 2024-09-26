# SPDX-FileCopyrightText: 2023 EasyDiffraction contributors
# SPDX-License-Identifier: BSD-3-Clause
# © 2023 Contributors to the EasyDiffraction project <https://github.com/easyscience/EasyDiffraction>

import copy
import lmfit
import numpy as np
from funcy import print_durations

from PySide6.QtCore import QObject, Signal, Slot, Property, QThreadPool

from EasyApp.Logic.Logging import console
from Logic.Helpers import IO
from Logic.Data import Data

try:
    import cryspy
    from cryspy.procedure_rhochi.rhochi_by_dictionary import \
        rhochi_calc_chi_sq_by_dictionary
    #console.debug('CrysPy module imported')
except ImportError:
    console.error('No CrysPy module found')


class Worker(QObject):
    finished = Signal()

    def __init__(self, proxy):
        super().__init__()
        self._proxy = proxy
        self._needCancel = False

        self._cryspyDictInitial = copy.deepcopy(self._proxy.data._cryspyDict)
        self._cryspyUsePrecalculatedData = False
        self._cryspyCalcAnalyticalDerivatives = False

        #self._paramsInit = lmfit.Parameters()
        self._paramsFinal = lmfit.Parameters()
        self._paramsBest = lmfit.Parameters()

        self._gofPrevIter = np.inf
        self._gofLastIter = np.inf
        self._gofBest = np.inf

        self._fitIteration = 0
        self._iterStart = 1

        #QThread.setTerminationEnabled()  # Not needed for Lmfit

    def callbackFunc(self, params, iter, resid, *args, **kws):
        # Calc reduced Chi2 == goodness-of-fit (GOF)
        chiSq = np.sum(np.square(resid))
        self._proxy.fitting.chiSq = chiSq / (self._proxy.fitting._pointsCount - self._proxy.fitting._freeParamsCount)
        console.info(IO.formatMsg('main', f'Iteration: {iter:5d}', f'Reduced Chi2: {self._proxy.fitting.chiSq:16g}'))

        # Calc goodness-of-fit (GOF) value shift between iterations
        gofStart = self._proxy.fitting.chiSqStart
        if iter == self._iterStart:
            self._gofPrevIter = self._proxy.fitting.chiSqStart
        self._gofLastIter = self._proxy.fitting.chiSq
        gofShift = abs(self._gofLastIter - self._gofPrevIter)
        self._gofPrevIter = self._gofLastIter

        # Save best goodness-of-fit (GOF) and params
        if self._gofLastIter < self._gofBest:
            self._gofBest = self._gofLastIter
            self._paramsBest = copy.deepcopy(params)

        # Update goodness-of-fit (GOF) value in the status bar
        if iter == self._iterStart or gofShift > 0.0099:
            self._proxy.status.goodnessOfFit = f'{gofStart:0.2f} → {self._gofLastIter:0.2f}'  # NEED move to connection
            self._proxy.fitting.chiSqSignificantlyChanged.emit()

        # Update iteration number in the status bar
        self._proxy.status.fitIteration = f'{iter}'

        # Check if fitting termination is requested
        if self._needCancel:
            self._needCancel = False
            console.error('Terminating the execution of the optimization thread')
            #QThread.terminate()  # Not needed for Lmfit
            return True  # Cancel minimization and return back to after lmfit.minimize

        return  # Continue minimization

    def residFunc(self, params):
        # Update CrysPy dict from Lmfit params during minimization
        for param in params:
            block, group, idx = Data.strToCryspyDictParamPath(param)
            self._proxy.data._cryspyDict[block][group][idx] = params[param].value

        # Calculate diffraction pattern based on updated CrysPy dict
        rhochi_calc_chi_sq_by_dictionary(
            self._proxy.data._cryspyDict,
            dict_in_out=self._proxy.data._cryspyInOutDict,
            flag_use_precalculated_data=self._cryspyUsePrecalculatedData,
            flag_calc_analytical_derivatives=self._cryspyCalcAnalyticalDerivatives)

        # Create total residual array
        totalResid = np.empty(0)
        for dataBlock in self._proxy.experiment.dataBlocksNoMeas:
            diffrn_radiation_type = dataBlock['params']['_diffrn_radiation']['type']['value']
            sample_type = dataBlock['params']['_sample']['type']['value']

            if diffrn_radiation_type == 'cwl' and sample_type == 'pd':
                experiment_prefix = 'pd'
            elif diffrn_radiation_type == 'tof' and sample_type == 'pd':
                experiment_prefix = 'tof'
            elif diffrn_radiation_type == 'cwl' and sample_type == 'sg':
                experiment_prefix = 'diffrn'

            ed_name = dataBlock['name']['value']
            cryspy_name = f'{experiment_prefix}_{ed_name}'
            cryspyInOutDict = self._proxy.data._cryspyInOutDict
            cryspyDict = self._proxy.data._cryspyDict

            if sample_type == 'sg':
                y_meas_array = cryspyDict[cryspy_name]['intensity_es'][0]
                sy_meas_array = cryspyDict[cryspy_name]['intensity_es'][1]
                y_calc_array = cryspyInOutDict[cryspy_name]['intensity_calc']

                resid = (y_meas_array - y_calc_array) / sy_meas_array
                totalResid = np.append(totalResid, resid)

            elif sample_type == 'pd':
                y_meas_array = cryspyInOutDict[cryspy_name]['signal_exp'][0]
                sy_meas_array = cryspyInOutDict[cryspy_name]['signal_exp'][1]
                y_bkg_array = cryspyInOutDict[cryspy_name]['signal_background']
                y_calc_all_phases_array = cryspyInOutDict[cryspy_name]['signal_plus'] + \
                                          cryspyInOutDict[cryspy_name]['signal_minus']
                y_calc_all_phases_array_with_bkg = y_calc_all_phases_array + y_bkg_array

                #resid = (y_calc_all_phases_array_with_bkg - y_meas_array) / sy_meas_array
                resid = (y_meas_array - y_calc_all_phases_array_with_bkg) / sy_meas_array
                totalResid = np.append(totalResid, resid)

        return totalResid

    def runLmfit(self):
        self._proxy.fitting._freezeChiSqStart = True

        # Save initial state of cryspyDict if cancel fit is requested
        self._cryspyDictInitial = copy.deepcopy(self._proxy.data._cryspyDict)

        # Preliminary calculations
        self._cryspyUsePrecalculatedData = False
        self._cryspyCalcAnalyticalDerivatives = False
        #self._proxy.fitting.chiSq, self._proxy.fitting._pointsCount, _, _, freeParamNames = rhochi_calc_chi_sq_by_dictionary(
        chiSq, pointsCount, _, _, freeParamNames = rhochi_calc_chi_sq_by_dictionary(
            self._proxy.data._cryspyDict,
            dict_in_out=self._proxy.data._cryspyInOutDict,
            flag_use_precalculated_data=self._cryspyUsePrecalculatedData,
            flag_calc_analytical_derivatives=self._cryspyCalcAnalyticalDerivatives)

        # Reduce the number of free parameters from CrysPy
        # Namely, atomic coordinates y and z if they are constrained to be == coordinate x
        freeParamNamesReduced = []
        cryspyObjBlockNames = [item.data_name for item in self._proxy.data._cryspyObj.items]
        for param in freeParamNames:
            addParam = True
            rawBlockName, groupName, pathIndices = param
            if groupName == 'atom_fract_xyz':
                blockName = rawBlockName.replace('crystal_', '')
                cryspyObjBlockIdx = cryspyObjBlockNames.index(blockName)
                cryspyObjBlock = self._proxy.data._cryspyObj.items[cryspyObjBlockIdx]
                for category in cryspyObjBlock.items:
                    if type(category) == cryspy.C_item_loop_classes.cl_1_atom_site.AtomSiteL:
                        cryspyAtoms = category.items
                        for atomIdx, cryspyAtom in enumerate(cryspyAtoms):
                            if atomIdx == pathIndices[1]:
                                if pathIndices[0] == 1 and cryspyAtom.fract_y_constraint == True and cryspyAtom.fract_y_refinement == False:
                                    addParam = False
                                    break
                                elif pathIndices[0] == 2 and cryspyAtom.fract_z_constraint == True and cryspyAtom.fract_z_refinement == False:
                                    addParam = False
                                    break
            if addParam:
                freeParamNamesReduced.append(param)

        # Number of measured data points
        self._proxy.fitting._pointsCount = pointsCount

        # Number of free parameters
        self._proxy.fitting._freeParamsCount = len(freeParamNamesReduced)
        if self._proxy.fitting._freeParamsCount != self._proxy.fittables._freeParamsCount:
            console.error(f'Number of free parameters differs. Expected {self._proxy.fittables._freeParamsCount}, got {self._proxy.fitting._freeParamsCount}')

        # Reduced chi-squared goodness-of-fit (GOF)
        self._proxy.fitting.chiSq = chiSq / (self._proxy.fitting._pointsCount - self._proxy.fitting._freeParamsCount)

        # Create lmfit parameters to be optimized
        freeParamValuesStart = [self._proxy.data._cryspyDict[way[0]][way[1]][way[2]] for way in freeParamNamesReduced]
        paramsLmfit = lmfit.Parameters()
        for cryspyParamPath, val in zip(freeParamNamesReduced, freeParamValuesStart):
            #val = np.float32(val)
            lmfitParamName = Data.cryspyDictParamPathToStr(cryspyParamPath)  # Only ascii letters and numbers allowed for lmfit.Parameters()???
            left = self._proxy.model.paramValueByFieldAndCrypyParamPath('min', cryspyParamPath)
            if left is None:
                left = self._proxy.experiment.paramValueByFieldAndCrypyParamPath('min', cryspyParamPath)
            if left is None:
                left = -np.inf
            right = self._proxy.model.paramValueByFieldAndCrypyParamPath('max', cryspyParamPath)
            if right is None:
                right = self._proxy.experiment.paramValueByFieldAndCrypyParamPath('max', cryspyParamPath)
            if right is None:
                right = np.inf
            paramsLmfit.add(lmfitParamName, value=val, min=left, max=right)

        # Minimization: lmfit.minimize
        self._proxy.fitting.chiSqStart = self._proxy.fitting.chiSq
        self._cryspyUsePrecalculatedData = True

        mini = lmfit.Minimizer(self.residFunc,
                               paramsLmfit,
                               iter_cb=self.callbackFunc,
                               nan_policy='propagate',
                               max_nfev=self._proxy.fitting.minimizerMaxIter)

        tol = self._proxy.fitting.minimizerTol
        method = self._proxy.fitting.minimizerMethod.lower()

        @print_durations()
        def minimize(method=method, **kwargs):
            result = mini.minimize(method=method, **kwargs)
            return result

        if method in ['leastsq', 'least_squares']:
            self._iterStart == -1
            result = minimize(method=method,
                              ftol=tol,
                              xtol=tol)
        elif method in ['bfgs', 'lbfgsb', 'l-bfgs-b']:
            self._iterStart == 1
            result = minimize(method=method,
                              tol=tol)
        else:
            self.finished.emit()
            console.error(f'Optimization method {method} is not supported.')
            return

        # Print results of the optimization
        lmfit.report_fit(result, min_correl=0.5)

        # Optimization status
        if result.success:  # NEED FIX: Move to connections. Pass names via signal.emit(names)
            console.info('Optimization successfully finished')
            paramsBest = result.params
            self._proxy.status.fitStatus = 'Success'
        else:
            console.info('Optimization unsuccessfully finished')
            paramsBest = self._paramsBest
            if result.aborted:
                console.info('Optimization aborted')
                self._proxy.status.fitStatus = 'Aborted'
                #self.cancelled.emit()
            else:
                console.info('Optimization failed')
                self._proxy.status.fitStatus = 'Failure'

        # /Users/as/Development/GitHub/easyScience/EasyDiffractionBeta/.venv_3.11/lib/python3.11/site-packages/cryspy/A_functions_base/powder_diffraction_const_wavelength.py:161: RuntimeWarning: invalid value encountered in power
        #  res = numpy.power(hh, 0.2)
        # /Users/as/Development/GitHub/easyScience/EasyDiffractionBeta/.venv_3.11/lib/python3.11/site-packages/cryspy/A_functions_base/powder_diffraction_const_wavelength.py:165: RuntimeWarning: invalid value encountered in power
        #  c_help = -0.2*numpy.power(hh, -0.8)

        # Update CrysPy dict with the best params after minimization finished/aborted/failed
        for param in paramsBest:
            block, group, idx = Data.strToCryspyDictParamPath(param)
            self._proxy.data._cryspyDict[block][group][idx] = paramsBest[param].value

        # Calculate optimal chi2
        self._cryspyUsePrecalculatedData = False
        self._cryspyCalcAnalyticalDerivatives = False
        chiSq, _, _, _, _ = rhochi_calc_chi_sq_by_dictionary(
            self._proxy.data._cryspyDict,
            dict_in_out=self._proxy.data._cryspyInOutDict,
            flag_use_precalculated_data=self._cryspyUsePrecalculatedData,
            flag_calc_analytical_derivatives=self._cryspyCalcAnalyticalDerivatives)
        self._proxy.fitting.chiSq = chiSq / (self._proxy.fitting._pointsCount - self._proxy.fitting._freeParamsCount)
        console.info(f"Optimal reduced chi2 per {self._proxy.fitting._pointsCount} points and {self._proxy.fitting._freeParamsCount} free params: {self._proxy.fitting.chiSq:.2f}")

        self._proxy.status.goodnessOfFit = f'{self._proxy.fitting.chiSqStart:0.2f} → {self._proxy.fitting.chiSq:0.2f}'  # NEED move to connection
        self._proxy.fitting.chiSqSignificantlyChanged.emit()

        # Update internal dicts with the best params
        self._proxy.experiment.editDataBlockByLmfitParams(paramsBest)
        self._proxy.model.editDataBlockByLmfitParams(paramsBest)

        # Update models considering that symmetry constraints applied
        # This is needed to update, e.g., symmetry constrained cell parameters in CIF
        # However, it triggers recalculating pattern and updating GOF in status bar.
        # NEED FIX
        #self._proxy.model.replaceAllModels()

        # Finishing
        self._proxy.fitting._freezeChiSqStart = False
        self.finished.emit()
        console.info('Optimization process has been finished')

class Fitting(QObject):
    isFittingNowChanged = Signal()
    fitFinished = Signal()
    chiSqStartChanged = Signal()
    chiSqChanged = Signal()
    chiSqSignificantlyChanged = Signal()
    minimizerMethodChanged = Signal()
    minimizerMaxIterChanged = Signal()
    minimizerTolChanged = Signal()

    def __init__(self, parent):
        super().__init__(parent)
        self._proxy = parent
        self._threadpool = QThreadPool.globalInstance()
        self._worker = Worker(self._proxy)
        self._isFittingNow = False

        self._chiSq = None
        self._chiSqStart = None
        self._freezeChiSqStart = False

        self._pointsCount = None
        self._freeParamsCount = 0

        self._minimizerMethod = 'leastsq'
        self._minimizerMaxIter = 500
        self._minimizerTol = 1e-5

        self._worker.finished.connect(self.setIsFittingNowToFalse)
        self._worker.finished.connect(self.fitFinished)

    @Property(str, notify=minimizerMethodChanged)
    def minimizerMethod(self):
        return self._minimizerMethod

    @minimizerMethod.setter
    def minimizerMethod(self, newValue):
        if self._minimizerMethod == newValue:
            return
        self._minimizerMethod = newValue
        self.minimizerMethodChanged.emit()

    @Property(int, notify=minimizerMaxIterChanged)
    def minimizerMaxIter(self):
        return self._minimizerMaxIter

    @minimizerMaxIter.setter
    def minimizerMaxIter(self, newValue):
        if self._minimizerMaxIter == newValue:
            return
        self._minimizerMaxIter = newValue
        self.minimizerMaxIterChanged.emit()

    @Property(float, notify=minimizerTolChanged)
    def minimizerTol(self):
        return self._minimizerTol

    @minimizerTol.setter
    def minimizerTol(self, newValue):
        if self._minimizerTol == newValue:
            return
        self._minimizerTol = newValue
        self.minimizerTolChanged.emit()

    @Property(bool, notify=isFittingNowChanged)
    def isFittingNow(self):
        return self._isFittingNow

    @isFittingNow.setter
    def isFittingNow(self, newValue):
        if self._isFittingNow == newValue:
            return
        self._isFittingNow = newValue
        self.isFittingNowChanged.emit()

    @Property(float, notify=chiSqStartChanged)
    def chiSqStart(self):
        return self._chiSqStart

    @chiSqStart.setter
    def chiSqStart(self, newValue):
        if self._chiSqStart == newValue:
            return
        self._chiSqStart = newValue
        self.chiSqStartChanged.emit()

    @Property(float, notify=chiSqChanged)
    def chiSq(self):
        return self._chiSq

    @chiSq.setter
    def chiSq(self, newValue):
        if self._chiSq == newValue:
            return
        self._chiSq = newValue
        self.chiSqChanged.emit()

    @Slot()
    def startStop(self):
        self._proxy.status.fitStatus = ''

        if self._worker._needCancel:
            console.debug('Minimization process has been already requested to cancel')
            return

        if self.isFittingNow:
            self._worker._needCancel = True
            console.debug('Minimization process has been requested to cancel')
        else:
            if self._proxy.fittables._freeParamsCount > 0:
                self.isFittingNow = True
                self._worker.runLmfit()
                #self._threadpool.start(self._worker.runLmfit)
                console.debug('Minimization process has been started in a separate thread')
            else:
                self._proxy.status.fitStatus = 'No free params'
                console.debug('Minimization process has not been started. No free parameters found.')

    def setIsFittingNowToFalse(self):
        self.isFittingNow = False


#https://stackoverflow.com/questions/30843876/using-qthreadpool-with-qrunnable-in-pyqt4
#https://stackoverflow.com/questions/70868493/what-is-the-best-way-to-stop-interrupt-qrunnable-in-qthreadpool
#https://stackoverflow.com/questions/24825441/stop-scipy-minimize-after-set-time
#https://stackoverflow.com/questions/22390479/qrunnable-trying-to-abort-a-task
