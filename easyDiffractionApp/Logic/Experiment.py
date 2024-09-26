# SPDX-FileCopyrightText: 2023 EasyDiffraction contributors
# SPDX-License-Identifier: BSD-3-Clause
# © 2023 Contributors to the EasyDiffraction project <https://github.com/easyscience/EasyDiffraction>

import os
import re
import copy
from io import StringIO
import numpy as np
import time
from PySide6.QtCore import QObject, Signal, Slot, Property
from PySide6.QtCore import QFile, QTextStream, QIODevice
from PySide6.QtQml import QJSValue

from EasyApp.Logic.Logging import console
from Logic.Helpers import IO
from Logic.Calculators import CryspyParser
from Logic.Data import Data

try:
    import cryspy
    from cryspy.H_functions_global.function_1_cryspy_objects import \
        str_to_globaln
    from cryspy.procedure_rhochi.rhochi_by_dictionary import \
        rhochi_calc_chi_sq_by_dictionary
    #console.debug('CrysPy module imported')
except ImportError:
    console.error('No CrysPy module found')


_DEFAULT_DATA_BLOCK_NO_MEAS_SC_CWL = """data_scd

_diffrn_radiation.probe neutron

_diffrn_radiation_wavelength.wavelength 1.0

_extinction.model gauss
_extinction.mosaicity 1000.0
_extinction.radius 30.0

loop_
_exptl_crystal.id
_exptl_crystal.scale
ph 1.0

loop_
_refln.index_h
_refln.index_k
_refln.index_l
_refln.intensity_meas
_refln.intensity_meas_su
"""

_DEFAULT_DATA_BLOCK_NO_MEAS_PD_TOF = """data_pnd

_diffrn_radiation.probe neutron

_pd_instr.2theta_bank 144.845
_pd_instr.dtt1 7476.91
_pd_instr.dtt2 -1.54
_pd_instr.zero -9.24
_pd_instr.alpha0 0.0
_pd_instr.alpha1 0.5971
_pd_instr.beta0 0.04221
_pd_instr.beta1 0.00946
_pd_instr.sigma0 0.30
_pd_instr.sigma1 7.01
_pd_instr.sigma2 0.0

loop_
_pd_phase_block.id
_pd_phase_block.scale
ph 1.0

loop_
_pd_background.line_segment_X
_pd_background.line_segment_intensity
0 100
150000 100

loop_
_pd_meas.time_of_flight
_pd_meas.intensity_total
_pd_meas.intensity_total_su
"""

_DEFAULT_DATA_BLOCK_NO_MEAS_PD_CWL = """data_pnd

_diffrn_radiation.probe neutron
_diffrn_radiation_wavelength.wavelength 1.9

_pd_calib.2theta_offset 0.0

_pd_instr.resolution_u 0.04
_pd_instr.resolution_v -0.05
_pd_instr.resolution_w 0.06
_pd_instr.resolution_x 0
_pd_instr.resolution_y 0

_pd_instr.reflex_asymmetry_p1 0
_pd_instr.reflex_asymmetry_p2 0
_pd_instr.reflex_asymmetry_p3 0
_pd_instr.reflex_asymmetry_p4 0

loop_
_pd_phase_block.id
_pd_phase_block.scale
ph 1.0

loop_
_pd_background.line_segment_X
_pd_background.line_segment_intensity
0 100
180 100

loop_
_pd_meas.2theta_scan
_pd_meas.intensity_total
_pd_meas.intensity_total_su
"""

_DEFAULT_DATA_BLOCK_PD_CWL = _DEFAULT_DATA_BLOCK_NO_MEAS_PD_CWL + """36.5 1    1
37.0 10   3
37.5 700  25
38.0 1100 30
38.5 50   7
39.0 1    1
"""


class Experiment(QObject):
    definedChanged = Signal()
    currentIndexChanged = Signal()
    dataBlocksChanged = Signal()
    dataBlocksNoMeasChanged = Signal()
    dataBlocksMeasOnlyChanged = Signal()
    dataBlocksCifChanged = Signal()
    dataBlocksCifNoMeasChanged = Signal()
    dataBlocksCifMeasOnlyChanged = Signal()
    yMeasArraysChanged = Signal()
    yBkgArraysChanged = Signal()
    yCalcTotalArraysChanged = Signal()
    yResidArraysChanged = Signal()
    xBraggDictsChanged = Signal()
    chartRangesChanged = Signal()

    def __init__(self, parent):
        super().__init__(parent)
        self._proxy = parent

        self._defined = False
        self._currentIndex = -1

        self._dataBlocksNoMeas = []
        self._dataBlocksMeasOnly = []

        self._dataBlocksCif = []
        self._dataBlocksCifNoMeas = []
        self._dataBlocksCifMeasOnly = []

        self._xArrays = []
        self._yMeasArrays = []
        self._syMeasArrays = []
        self._yBkgArrays = []
        self._yCalcTotalArrays = []
        self._yResidArrays = []
        self._xBraggDicts = []

        self._chartRanges = []

    # QML accessible properties

    @Property('QVariant', notify=chartRangesChanged)
    def chartRanges(self):
        return self._chartRanges

    @Property(bool, notify=definedChanged)
    def defined(self):
        return self._defined

    @defined.setter
    def defined(self, newValue):
        if self._defined == newValue:
            return
        self._defined = newValue
        console.debug(IO.formatMsg('main', f'Experiment defined: {newValue}'))
        self.definedChanged.emit()

    @Property(int, notify=currentIndexChanged)
    def currentIndex(self):
        return self._currentIndex

    @currentIndex.setter
    def currentIndex(self, newValue):
        if self._currentIndex == newValue:
            return
        self._currentIndex = newValue
        console.debug(f"Current experiment index: {newValue}")
        self.currentIndexChanged.emit()

    @Property('QVariant', notify=dataBlocksMeasOnlyChanged)
    def dataBlocksMeasOnly(self):
        #console.error('EXPERIMENT DATABLOCK (MEAS ONLY) GETTER')
        return self._dataBlocksMeasOnly

    @Property('QVariant', notify=dataBlocksNoMeasChanged)
    def dataBlocksNoMeas(self):
        #console.error('EXPERIMENT DATABLOCK (NO MEAS) GETTER')
        return self._dataBlocksNoMeas

    @Property('QVariant', notify=dataBlocksCifChanged)
    def dataBlocksCif(self):
        return self._dataBlocksCif

    @Property('QVariant', notify=dataBlocksCifNoMeasChanged)
    def dataBlocksCifNoMeas(self):
        return self._dataBlocksCifNoMeas

    @Property('QVariant', notify=dataBlocksCifMeasOnlyChanged)
    def dataBlocksCifMeasOnly(self):
        return self._dataBlocksCifMeasOnly

    # QML accessible methods

    @Slot()
    def addDefaultExperiment(self):
        console.debug('Adding default experiment')
        self.loadExperimentsFromEdCif(_DEFAULT_DATA_BLOCK_PD_CWL)

    @Slot('QVariant')
    def loadExperimentsFromResources(self, fpaths):
        if type(fpaths) == QJSValue:
            fpaths = fpaths.toVariant()
        for fpath in fpaths:
            console.debug(f"Loading experiment(s) from: {fpath}")
            file = QFile(fpath)
            if not file.open(QIODevice.ReadOnly | QIODevice.Text):
                console.error('Not found in resources')
                return
            stream = QTextStream(file)
            edCif = stream.readAll()
            self.loadExperimentsFromEdCif(edCif)

    @Slot('QVariant')
    def loadExperimentsFromFiles(self, fpaths):
        if type(fpaths) == QJSValue:
            fpaths = fpaths.toVariant()

        for fpath in fpaths:
            fpath = fpath.toLocalFile()
            fpath = IO.generalizePath(fpath)
            _, fext = os.path.splitext(fpath)
            console.debug(f"Loading experiment(s) from: {fpath}")

            # If loading CIF
            if fext == '.cif':
                with open(fpath, 'r') as file:
                    procData = file.read()

            # If loading non-CIF data files (pd-cwl and pd-tof)
            elif fext == '.xye' or fext == '.xys' or fext == '.xy' or fext == '.dat':

                # Try loading data file
                try:
                    data = np.loadtxt(fpath, unpack=True)
                except Exception as exception:
                    console.error(f"Failed to load data from file {fpath} with exception {exception}")
                    return

                # Extract measured data and calculate standard uncertainty if needed
                if data.shape[0] == 3:
                    x, intensity, intensity_su = data
                elif data.shape[0] == 2:
                    x, intensity = data
                    intensity_su = np.sqrt(intensity)
                else:
                    console.error(f"Failed to load data from file {fpath}. Supported number of columns: 2 or 3")
                    return

                # Convert data from numpy arrays to string
                sio = StringIO()
                np.savetxt(sio, np.c_[x, intensity, intensity_su], fmt='%10.6f')
                procData = sio.getvalue()

                # Add default CIF instrumental block and measured data header
                if x.max() < 180:
                    procData = _DEFAULT_DATA_BLOCK_NO_MEAS_PD_CWL + procData
                else:
                    procData = _DEFAULT_DATA_BLOCK_NO_MEAS_PD_TOF + procData

            # If loading non-CIF data files (sg-cwl)
            elif fext == '.int':

                # Try loading data file
                try:
                    data = np.loadtxt(fpath, unpack=True)
                except Exception as exception:
                    console.error(f"Failed to load data from file {fpath} with exception {exception}")
                    return

                # Extract measured data and calculate standard uncertainty if needed
                if data.shape[0] == 5:
                    h, k, l, intensity, intensity_su = data
                else:
                    console.error(f"Failed to load data from file {fpath}. Supported number of columns: 5")
                    return

                # Convert data from numpy arrays to string
                sio = StringIO()
                np.savetxt(sio, np.c_[h, k, l, intensity, intensity_su], fmt='%4i' '%4i' '%4i' '%12.3f' '%12.3f')
                procData = sio.getvalue()

                # Add default CIF instrumental block and measured data header
                procData = _DEFAULT_DATA_BLOCK_NO_MEAS_SC_CWL + procData

            # Other formats not supported
            else:
                console.error(f"Unsupported file extension {fext} of {fpath}")
                return

            # Lowercase all data block names
            procData = re.sub(r'data_(.*)', lambda m: m.group(0).lower(), procData)

            self.loadExperimentsFromEdCif(procData)

    @Slot(str)
    def loadExperimentsFromEdCif(self, edCif):
        cryspyObj = self._proxy.data._cryspyObj

        # Add the tof cryspy specific parameters
        # We set them to be 0 and calculate the background ourselves
        if '2theta_scan' in edCif:
            cryspyCif = CryspyParser.edCifToCryspyCif(edCif, 'pd-cwl')
        elif 'time_of_flight' in edCif:
            edCif += '\n_pd_instr.peak_shape Gauss'  # 'pseudo-Voigt' is default
            #edCif += '\n_pd_instr.peak_shape pseudo-Voigt'
            ###edCif += '\n_tof_background_time_max 1000.0'
            cryspyCif = CryspyParser.edCifToCryspyCif(edCif, 'pd-tof')
        elif 'index_h' in edCif:
            edCif += '\n_setup_field 0.0'
            edCif += '\n_diffrn_orient_matrix_ub_11 -0.088033'
            edCif += '\n_diffrn_orient_matrix_ub_12 -0.088004'
            edCif += '\n_diffrn_orient_matrix_ub_13  0.069970'
            edCif += '\n_diffrn_orient_matrix_ub_21  0.034058'
            edCif += '\n_diffrn_orient_matrix_ub_22 -0.188170'
            edCif += '\n_diffrn_orient_matrix_ub_23 -0.013039'
            edCif += '\n_diffrn_orient_matrix_ub_31  0.223600'
            edCif += '\n_diffrn_orient_matrix_ub_32  0.125751'
            edCif += '\n_diffrn_orient_matrix_ub_33  0.029490'
            edCif += '\n_diffrn_orient_matrix_type   CCSL'
            cryspyCif = CryspyParser.edCifToCryspyCif(edCif, 'sg-cwl')
        cryspyExperimentsObj = str_to_globaln(cryspyCif)

        # Add/modify CryspyObj with ranges based on the measured data points in _pd_meas loop
        for dataBlock in cryspyExperimentsObj.items:
            cryspyExperimentType = type(dataBlock)
            cryspyRangeObj = None
            if cryspyExperimentType == cryspy.E_data_classes.cl_2_pd.Pd:
                console.debug(IO.formatMsg('sub', f"'pd-cwl' type experiment based on {cryspyExperimentType}"))
                range_min = 0  # default value to be updated later
                range_max = 180  # default value to be updated later
                defaultEdRangeCif = f'_pd_meas.2theta_range_min {range_min}\n_pd_meas.2theta_range_max {range_max}'
                cryspyRangeCif = CryspyParser.edCifToCryspyCif(defaultEdRangeCif, 'pd-cwl')
                cryspyRangeObj = str_to_globaln(cryspyRangeCif).items
                for item in dataBlock.items:
                    if type(item) == cryspy.C_item_loop_classes.cl_1_pd_meas.PdMeasL:
                        range_min = item.items[0].ttheta
                        range_max = item.items[-1].ttheta
                        cryspyRangeObj[0].ttheta_min = range_min
                        cryspyRangeObj[0].ttheta_max = range_max
            elif cryspyExperimentType == cryspy.E_data_classes.cl_2_tof.TOF:
                console.debug(IO.formatMsg('sub', f"'pd-tof' type experiment based on {cryspyExperimentType}"))
                range_min = 2000  # default value to be updated later
                range_max = 20000  # default value to be updated later
                cryspyRangeCif = f'_range_time_min {range_min}\n_range_time_max {range_max}'
                cryspyRangeObj = str_to_globaln(cryspyRangeCif).items
                for item in dataBlock.items:
                    if type(item) == cryspy.C_item_loop_classes.cl_1_tof_meas.TOFMeasL:
                        range_min = item.items[0].time
                        range_max = item.items[-1].time
                        cryspyRangeObj[0].time_min = range_min
                        cryspyRangeObj[0].time_max = range_max
                for idx, item in enumerate(dataBlock.items):
                    if type(item) == cryspy.C_item_loop_classes.cl_1_tof_background.TOFBackground:
                        dataBlock.items[idx].time_max = range_max
            elif cryspyExperimentType == cryspy.E_data_classes.cl_2_diffrn.Diffrn:
                console.debug(IO.formatMsg('sub', f"'sg-cwl' type experiment based on {cryspyExperimentType}"))
            if cryspyRangeObj is not None:
                dataBlock.add_items(cryspyRangeObj)

        # Add/modify CryspyObj with phases based on the already loaded phases
        loadedModelNames = [block['name']['value'] for block in self._proxy.model.dataBlocks]
        for dataBlock in cryspyExperimentsObj.items:
            cryspyExperimentType = type(dataBlock)
            # pd-cwl and pd-tof experiments
            if cryspyExperimentType == cryspy.E_data_classes.cl_2_pd.Pd or cryspyExperimentType == cryspy.E_data_classes.cl_2_tof.TOF:
                # Delete phases not present in the loaded models
                for itemIdx, item in enumerate(dataBlock.items):
                    if type(item) == cryspy.C_item_loop_classes.cl_1_phase.PhaseL:
                        cryspyModelNames = [phase.label for phase in item.items]
                        for modelIdx, modelName in enumerate(cryspyModelNames):
                            if modelName not in loadedModelNames:
                                del item.items[modelIdx]
                        if not len(item.items):
                            del dataBlock.items[itemIdx]
                itemTypes = [type(item) for item in dataBlock.items]
                # Add default phases if no phases are present
                if cryspy.C_item_loop_classes.cl_1_phase.PhaseL not in itemTypes and cryspyExperimentType != cryspy.E_data_classes.cl_2_diffrn.Diffrn:
                    defaultEdModelsCif = 'loop_\n_pd_phase_block.id\n_pd_phase_block.scale'
                    for modelName in loadedModelNames:
                        defaultEdModelsCif += f'\n{modelName} 1.0'
                    cryspyPhasesCif = CryspyParser.edCifToCryspyCif(defaultEdModelsCif)
                    cryspyPhasesObj = str_to_globaln(cryspyPhasesCif).items
                    dataBlock.add_items(cryspyPhasesObj)
            # sg-cwl
            elif cryspyExperimentType == cryspy.E_data_classes.cl_2_diffrn.Diffrn:
                firstModelName = loadedModelNames[0]
                firstModelScale = 1.0
                for item in cryspyExperimentsObj.items[0].items:
                    if hasattr(item, 'items') and item.items[0].PREFIX == 'exptl_crystal':
                        firstModelScale = item.items[0].scale
                        break
                cryspyPhasesCif = f'_phase_label {firstModelName}\n_phase_scale {firstModelScale}'
                cryspyPhasesObj = str_to_globaln(cryspyPhasesCif).items
                dataBlock.add_items(cryspyPhasesObj)

        experimentsCountBefore = len(self.cryspyObjExperiments())
        cryspyObj.add_items(cryspyExperimentsObj.items)
        experimentsCountAfter = len(self.cryspyObjExperiments())
        success = experimentsCountAfter - experimentsCountBefore

        if success:
            cryspyExperimentsDict = cryspyExperimentsObj.get_dictionary()
            edExperimentsMeasOnly, edExperimentsNoMeas = CryspyParser.cryspyObjAndDictToEdExperiments(cryspyExperimentsObj,
                                                                                                      cryspyExperimentsDict)

            self._proxy.data._cryspyDict.update(cryspyExperimentsDict)
            self._dataBlocksMeasOnly += edExperimentsMeasOnly
            self._dataBlocksNoMeas += edExperimentsNoMeas

            self._currentIndex = len(self.dataBlocksNoMeas) - 1
            if not self.defined:
                self.defined = bool(len(self.dataBlocksNoMeas))

            console.debug(IO.formatMsg('sub', f'{len(edExperimentsMeasOnly)} experiment(s)', 'meas data only', 'to intern dataset', 'added'))
            console.debug(IO.formatMsg('sub', f'{len(edExperimentsNoMeas)} experiment(s)', 'without meas data', 'to intern dataset', 'added'))

            self.dataBlocksChanged.emit()
        else:
            console.debug(IO.formatMsg('sub', 'No experiment(s)', '', 'to intern dataset', 'added'))

    @Slot(str)
    def replaceExperiment(self, edCifNoMeas=''):  # NEED modifications for CWL/TOF
        console.debug("Cryspy obj and dict need to be replaced")

        # Compose EasyDiffraction CIF
        currentDataBlock = self.dataBlocksNoMeas[self.currentIndex]
        currentExperimentName = currentDataBlock['name']['value']

        cryspyObjBlockNames = [item.data_name for item in self._proxy.data._cryspyObj.items]
        cryspyObjBlockIdx = cryspyObjBlockNames.index(currentExperimentName)

        if not edCifNoMeas:
            edCifNoMeas = CryspyParser.dataBlockToCif(currentDataBlock)

        edCifMeasOnly = CryspyParser.dataBlockToCif(self.dataBlocksMeasOnly[self.currentIndex],
                                                    includeBlockName=False)

        edCif = edCifNoMeas + '\n\n' + edCifMeasOnly

        # Add parameters, which are optional for EasyDiffraction CIF, but required for CrysPy CIF
        diffrn_radiation_type = currentDataBlock['params']['_diffrn_radiation']['type']['value']
        sample_type = currentDataBlock['params']['_sample']['type']['value']

        if diffrn_radiation_type == 'cwl' and sample_type == 'pd':
            experiment_prefix = 'pd'
            experiment_type = 'pd-cwl'
        elif diffrn_radiation_type == 'tof' and sample_type == 'pd':
            experiment_prefix = 'tof'
            experiment_type = 'pd-tof'
        elif diffrn_radiation_type == 'cwl' and sample_type == 'sg':
            experiment_prefix = 'diffrn'
            experiment_type = 'sg-cwl'

        #if '2theta_scan' in edCif:  # pd-cwl
        if experiment_type == 'pd-cwl':
            diffrn_radiation_type = 'cwl'
            experiment_prefix = 'pd'
            range_min = currentDataBlock['params']['_pd_meas']['2theta_range_min']['value']
            range_max = currentDataBlock['params']['_pd_meas']['2theta_range_max']['value']
            edRangeCif = f'_pd_meas.2theta_range_min {range_min}\n_pd_meas.2theta_range_max {range_max}'
            edCif += '\n\n' + edRangeCif
        #elif 'time_of_flight' in edCif:  # pd-tof
        elif experiment_type == 'pd-tof':
            edCif += '\n\n_pd_instr.peak_shape Gauss'
            #edCif += '\n_pd_instr.peak_shape pseudo-Voigt'
            diffrn_radiation_type = 'tof'
            experiment_prefix = 'tof'
            ###time_max = currentDataBlock['params']['_tof_background']['time_max']['value']
            ###edCif += f'\n_tof_background.time_max {time_max}'
            range_min = currentDataBlock['params']['_pd_meas']['tof_range_min']['value']
            range_max = currentDataBlock['params']['_pd_meas']['tof_range_max']['value']
            edRangeCif = f'_pd_meas.tof_range_min {range_min}\n_pd_meas.tof_range_max {range_max}'
            edCif += '\n\n' + edRangeCif
        #elif 'index_h' in edCif:  # sg-cwl
        elif experiment_type == 'sg-cwl':
            edCif += '\n_setup_field 0.0'
            edCif += '\n_diffrn_orient_matrix_ub_11 -0.088033'
            edCif += '\n_diffrn_orient_matrix_ub_12 -0.088004'
            edCif += '\n_diffrn_orient_matrix_ub_13  0.069970'
            edCif += '\n_diffrn_orient_matrix_ub_21  0.034058'
            edCif += '\n_diffrn_orient_matrix_ub_22 -0.188170'
            edCif += '\n_diffrn_orient_matrix_ub_23 -0.013039'
            edCif += '\n_diffrn_orient_matrix_ub_31  0.223600'
            edCif += '\n_diffrn_orient_matrix_ub_32  0.125751'
            edCif += '\n_diffrn_orient_matrix_ub_33  0.029490'
            edCif += '\n_diffrn_orient_matrix_type   CCSL'

        # Create CrysPy CIF and objects
        cryspyCif = CryspyParser.edCifToCryspyCif(edCif, experiment_type)
        cryspyExperimentsObj = str_to_globaln(cryspyCif)

        # add phase block
        if experiment_type == 'sg-cwl':
            for dataBlock in cryspyExperimentsObj.items:
                firstModelName = ''
                firstModelScale = 1.0
                for item in cryspyExperimentsObj.items[0].items:
                    if hasattr(item, 'items') and item.items[0].PREFIX == 'exptl_crystal':
                        firstModelName = item.items[0].id
                        firstModelScale = item.items[0].scale
                        break
                cryspyPhasesCif = f'_phase_label {firstModelName}\n_phase_scale {firstModelScale}'
                cryspyPhasesObj = str_to_globaln(cryspyPhasesCif).items
                dataBlock.add_items(cryspyPhasesObj)

        # Create cryspy dictionary
        cryspyExperimentsDict = cryspyExperimentsObj.get_dictionary()

        # Powder diffraction experiment should have 'pd_' or 'tof_' prefix to be recognized by CrysPy
        # Had to add edCifMeasOnly loop to the input CIF in order to allow CrysPy to do this
        cryspyDictBlockName = f'{experiment_prefix}_{currentExperimentName}'

        _, edExperimentsNoMeas = CryspyParser.cryspyObjAndDictToEdExperiments(cryspyExperimentsObj,
                                                                              cryspyExperimentsDict)

        self._proxy.data._cryspyObj.items[cryspyObjBlockIdx] = cryspyExperimentsObj.items[0]
        self._proxy.data._cryspyDict[cryspyDictBlockName] = cryspyExperimentsDict[cryspyDictBlockName]
        self._dataBlocksNoMeas[self.currentIndex] = edExperimentsNoMeas[0]

        console.debug(f"Experiment data block '{currentExperimentName}' (no. {self.currentIndex + 1}) (without measured data) has been replaced")
        self.dataBlocksNoMeasChanged.emit()  # self.dataBlocksNoMeasChanged.emit(blockIdx)

#        # remove experiment from self._proxy.data._cryspyDict
#        currentExperimentName = self.dataBlocks[self.currentIndex]['name']
#        del self._proxy.data._cryspyDict[f'pd_{currentExperimentName}']
#
#        # add experiment to self._proxy.data._cryspyDict
#        cifNoMeas = CryspyParser.dataBlocksToCif(self._dataBlocks)
#        cifMeasOnly = self.dataBlocksCifMeasOnly
#        edCif = cifNoMeas + '\n' + cifMeasOnly
#        self.loadExperimentsFromEdCif(edCif)

    @Slot(int)
    def removeExperiment(self, index):
        console.debug(f"Removing experiment no. {index + 1}")
        self.currentIndex = index - 1
        del self._dataBlocksNoMeas[index]
        del self._dataBlocksMeasOnly[index]
        del self._xArrays[index]
        del self._yMeasArrays[index]
        del self._yBkgArrays[index]

        self.defined = bool(len(self.dataBlocksNoMeas))

        self.dataBlocksNoMeasChanged.emit()
        self.dataBlocksMeasOnlyChanged.emit()
        self.yMeasArraysChanged.emit()
        self.yBkgArraysChanged.emit()
        console.debug(f"Experiment no. {index + 1} has been removed")

    @Slot()
    def resetAll(self):
        self.defined = False
        self._currentIndex = -1
        self._dataBlocksNoMeas = []
        self._dataBlocksMeasOnly = []
        self._dataBlocksCif = []
        self._dataBlocksCifNoMeas = ""
        self._dataBlocksCifMeasOnly = ""
        self._xArrays = []
        self._yMeasArrays = []
        self._syMeasArrays = []
        self._yBkgArrays = []
        self._yCalcTotalArrays = []
        self._yResidArrays = []
        self._xBraggDicts = []
        self._chartRanges = []
        #self.dataBlocksChanged.emit()
        console.debug("All experiments removed")

    @Slot(int, str, str, str, 'QVariant')
    def setMainParamWithFullUpdate(self, blockIdx, category, name, field, value):
        changedIntern = self.editDataBlockMainParam(blockIdx, category, name, field, value)
        if not changedIntern:
            return
        self.replaceExperiment()

    @Slot(int, str, str, str, 'QVariant')
    def setMainParam(self, blockIdx, category, name, field, value):
        changedIntern = self.editDataBlockMainParam(blockIdx, category, name, field, value)
        changedCryspy = self.editCryspyDictByMainParam(blockIdx, category, name, field, value)
        if changedIntern and changedCryspy:
            self.dataBlocksNoMeasChanged.emit()

    @Slot(int, str, str, int, str, 'QVariant')
    def setLoopParamWithFullUpdate(self, blockIdx, category, name, rowIndex, field, value):
        changedIntern = self.editDataBlockLoopParam(blockIdx, category, name, rowIndex, field, value)
        if not changedIntern:
            return
        self.replaceExperiment()

    @Slot(int, str, str, int, str, 'QVariant')
    def setLoopParam(self, blockIdx, category, name, rowIndex, field, value):
        changedIntern = self.editDataBlockLoopParam(blockIdx, category, name, rowIndex, field, value)
        changedCryspy = self.editCryspyDictByLoopParam(blockIdx, category, name, rowIndex, field, value)
        if changedIntern and changedCryspy:
            self.dataBlocksNoMeasChanged.emit()

    @Slot(str, int)
    def removeLoopRow(self, category, rowIndex):
        self.removeDataBlockLoopRow(category, rowIndex)
        self.replaceExperiment()

    @Slot(str)
    def appendLoopRow(self, category):
        self.appendDataBlockLoopRow(category)
        self.replaceExperiment()

    @Slot()
    def resetBkgToDefault(self):
        self.resetDataBlockBkgToDefault()
        self.replaceExperiment()

    # Private methods

    def cryspyObjExperiments(self):
        cryspyObj = self._proxy.data._cryspyObj
        supportedExperimentTypes = [cryspy.E_data_classes.cl_2_pd.Pd,  # 'pd-cwl
                                    cryspy.E_data_classes.cl_2_tof.TOF,  # 'pd-tof'
                                    cryspy.E_data_classes.cl_2_diffrn.Diffrn]  # 'sg-cwl'
        experiments = [block for block in cryspyObj.items if type(block) in supportedExperimentTypes]
        return experiments

    def removeDataBlockLoopRow(self, category, rowIndex):
        block = 'experiment'
        blockIdx = self._currentIndex
        del self._dataBlocksNoMeas[blockIdx]['loops'][category][rowIndex]

        console.debug(f"Intern dict ▌ {block}[{blockIdx}].{category}[{rowIndex}] has been removed")

    def appendDataBlockLoopRow(self, category):
        block = 'experiment'
        blockIdx = self._currentIndex

        lastBkgPoint = self._dataBlocksNoMeas[blockIdx]['loops'][category][-1]

        newBkgPoint = copy.deepcopy(lastBkgPoint)
        newBkgPoint['line_segment_X']['value'] += 10

        self._dataBlocksNoMeas[blockIdx]['loops'][category].append(newBkgPoint)
        atomsCount = len(self._dataBlocksNoMeas[blockIdx]['loops'][category])

        console.debug(f"Intern dict ▌ {block}[{blockIdx}].{category}[{atomsCount}] has been added")

    def resetDataBlockBkgToDefault(self):
        block = 'experiment'
        blockIdx = self._currentIndex
        category = '_pd_background'

        firstBkgPoint = copy.deepcopy(self._dataBlocksNoMeas[blockIdx]['loops'][category][0])  # copy of the 1st point
        firstBkgPoint['line_segment_X']['value'] = 0
        firstBkgPoint['line_segment_intensity']['value'] = 0

        lastBkgPoint = copy.deepcopy(firstBkgPoint)
        lastBkgPoint['line_segment_X']['value'] = 180

        self._dataBlocksNoMeas[blockIdx]['loops'][category] = [firstBkgPoint, lastBkgPoint]

        console.debug(f"Intern dict ▌ {block}[{blockIdx}].{category} has been reset to default values")

    def editDataBlockMainParam(self, blockIdx, category, name, field, value):
        block = 'experiment'
        oldValue = self._dataBlocksNoMeas[blockIdx]['params'][category][name][field]
        if oldValue == value:
            return False
        self._dataBlocksNoMeas[blockIdx]['params'][category][name][field] = value
        if type(value) == float:
            console.debug(IO.formatMsg('sub', 'Intern dict', f'{oldValue} → {value:.6f}', f'{block}[{blockIdx}].{category}.{name}.{field}'))
        else:
            console.debug(IO.formatMsg('sub', 'Intern dict', f'{oldValue} → {value}', f'{block}[{blockIdx}].{category}.{name}.{field}'))
        return True

    def editDataBlockLoopParam(self, blockIdx, category, name, rowIndex, field, value):
        block = 'experiment'
        oldValue = self._dataBlocksNoMeas[blockIdx]['loops'][category][rowIndex][name][field]
        if oldValue == value:
            return False
        self._dataBlocksNoMeas[blockIdx]['loops'][category][rowIndex][name][field] = value
        if type(value) == float:
            console.debug(IO.formatMsg('sub', 'Intern dict', f'{oldValue} → {value:.6f}', f'{block}[{blockIdx}].{category}[{rowIndex}].{name}.{field}'))
        else:
            console.debug(IO.formatMsg('sub', 'Intern dict', f'{oldValue} → {value}', f'{block}[{blockIdx}].{category}[{rowIndex}].{name}.{field}'))
        return True

    def editCryspyDictByMainParam(self, blockIdx, category, name, field, value):
        if field != 'value' and field != 'fit':
            return True

        path, value = self.cryspyDictPathByMainParam(blockIdx, category, name, value)
        if field == 'fit':
            path[1] = f'flags_{path[1]}'

        oldValue = self._proxy.data._cryspyDict[path[0]][path[1]][path[2]]
        if oldValue == value:
            return False
        self._proxy.data._cryspyDict[path[0]][path[1]][path[2]] = value

        console.debug(IO.formatMsg('sub', 'Cryspy dict', f'{oldValue} → {value}', f'{path}'))
        return True

    def editCryspyDictByLoopParam(self, blockIdx, category, name, rowIndex, field, value):
        if field != 'value' and field != 'fit':
            return True

        path, value = self.cryspyDictPathByLoopParam(blockIdx, category, name, rowIndex, value)
        if path[1] == '':  # Temporary solution! If param is handled by ED directly, not CrysPy, as e.g. TOF background
            return True
        if field == 'fit':
            path[1] = f'flags_{path[1]}'

        oldValue = self._proxy.data._cryspyDict[path[0]][path[1]][path[2]]
        if oldValue == value:
            return False
        self._proxy.data._cryspyDict[path[0]][path[1]][path[2]] = value

        console.debug(IO.formatMsg('sub', 'Cryspy dict', f'{oldValue} → {value}', f'{path}'))
        return True

    def cryspyDictPathByMainParam(self, blockIdx, category, name, value):
        diffrn_radiation_type = self._dataBlocksNoMeas[blockIdx]['params']['_diffrn_radiation']['type']['value']
        sample_type = self._proxy.experiment.dataBlocksNoMeas[blockIdx]['params']['_sample']['type']['value']

        if diffrn_radiation_type == 'cwl' and sample_type == 'pd':
            experiment_prefix = 'pd'
        elif diffrn_radiation_type == 'tof' and sample_type == 'pd':
            experiment_prefix = 'tof'
        elif diffrn_radiation_type == 'cwl' and sample_type == 'sg':
            experiment_prefix = 'diffrn'

        blockName = self._dataBlocksNoMeas[blockIdx]['name']['value']
        path = ['','','']
        path[0] = f'{experiment_prefix}_{blockName}'

        # _diffrn_radiation_wavelength
        if category == '_diffrn_radiation_wavelength':
            if name == 'wavelength':
                path[1] = 'wavelength'
                path[2] = 0

        # _pd_meas_2theta_offset
        elif category == '_pd_calib':
            if name == '2theta_offset':
                path[1] = 'offset_ttheta'
                path[2] = 0
                if diffrn_radiation_type == 'cwl':
                    value = np.deg2rad(value)

        # _pd_instr
        elif category == '_pd_instr':
            if name == 'resolution_u':
                path[1] = 'resolution_parameters'
                path[2] = 0
            elif name == 'resolution_v':
                path[1] = 'resolution_parameters'
                path[2] = 1
            elif name == 'resolution_w':
                path[1] = 'resolution_parameters'
                path[2] = 2
            elif name == 'resolution_x':
                path[1] = 'resolution_parameters'
                path[2] = 3
            elif name == 'resolution_y':
                path[1] = 'resolution_parameters'
                path[2] = 4
            elif name == 'resolution_z':
                path[1] = 'resolution_parameters'
                path[2] = 5

            elif name == 'reflex_asymmetry_p1':
                path[1] = 'asymmetry_parameters'
                path[2] = 0
            elif name == 'reflex_asymmetry_p2':
                path[1] = 'asymmetry_parameters'
                path[2] = 1
            elif name == 'reflex_asymmetry_p3':
                path[1] = 'asymmetry_parameters'
                path[2] = 2
            elif name == 'reflex_asymmetry_p4':
                path[1] = 'asymmetry_parameters'
                path[2] = 3

            elif name == 'dtt1':
                path[1] = 'dtt1'
                path[2] = 0
            elif name == 'dtt2':
                path[1] = 'dtt2'
                path[2] = 0
            elif name == 'zero':
                path[1] = 'zero'
                path[2] = 0

            elif name in ['alpha0', 'alpha1']:
                path[1] = 'profile_alphas'
                path[2] = int(name[-1])
            elif name in ['beta0', 'beta1']:
                path[1] = 'profile_betas'
                path[2] = int(name[-1])
            elif name in ['sigma0', 'sigma1', 'sigma2']:  # sigma2: if profile_peak_shape == 'pseudo-Voigt'
                path[1] = 'profile_sigmas'
                path[2] = int(name[-1])
            elif name in ['gamma0', 'gamma1', 'gamma2']:  # gamma0, gamma1, gamma2: if profile_peak_shape == 'pseudo-Voigt'
                path[1] = 'profile_gammas'
                path[2] = int(name[-1])

        # _tof_background
        elif category == '_tof_background':
             if name.startswith('coeff'):
                 coeff_index = int(name[5:])
                 path[1] = 'background_coefficients'
                 path[2] = coeff_index - 1

        # _extinction
        elif category == '_extinction':
            if name == 'mosaicity':
                path[1] = 'extinction_mosaicity'
                path[2] = 0
            if name == 'radius':
                path[1] = 'extinction_radius'
                path[2] = 0

        # undefined
        else:
            console.error(f"Undefined parameter name '{category}_{name}'")

        #console.debug(f"Editing CrysPy parameter '{path[0]}.{path[1]}{[path[2]]}'")

        return path, value

    def cryspyDictPathByLoopParam(self, blockIdx, category, name, rowIndex, value):
        diffrn_radiation_type = self._dataBlocksNoMeas[blockIdx]['params']['_diffrn_radiation']['type']['value']
        sample_type = self._proxy.experiment.dataBlocksNoMeas[blockIdx]['params']['_sample']['type']['value']

        if diffrn_radiation_type == 'cwl' and sample_type == 'pd':
            experiment_prefix = 'pd'
        elif diffrn_radiation_type == 'tof' and sample_type == 'pd':
            experiment_prefix = 'tof'
        elif diffrn_radiation_type == 'cwl' and sample_type == 'sg':
            experiment_prefix = 'diffrn'

        blockName = self._dataBlocksNoMeas[blockIdx]['name']['value']
        path = ['','','']
        path[0] = f"{experiment_prefix}_{blockName}"

        # _pd_background
        if category == '_pd_background':
            if diffrn_radiation_type == 'cwl':
                console.debug('Background is handeled by CrysPy')
                if name == 'line_segment_X':
                    path[1] = 'background_ttheta'
                    path[2] = rowIndex
                    value = np.deg2rad(value)
                if name == 'line_segment_intensity':
                    path[1] = 'background_intensity'
                    path[2] = rowIndex
            elif diffrn_radiation_type == 'tof':
                console.debug('Background is handeled by CrysPy')
                if name == 'line_segment_X':
                    path[1] = 'background_time'
                    path[2] = rowIndex
                    value = np.deg2rad(value)
                if name == 'line_segment_intensity':
                    path[1] = 'background_intensity'
                    path[2] = rowIndex

        # _pd_phase_block
        if category == '_pd_phase_block':
            if name == 'scale':
                path[1] = 'phase_scale'
                path[2] = rowIndex

        # _exptl_crystal
        if category == '_exptl_crystal':
            if name == 'scale':
                path[1] = 'phase_scale'
                path[2] = 0

        return path, value

    def paramValueByFieldAndCrypyParamPath(self, field, path):  # NEED FIX: code duplicate of editDataBlockByLmfitParams
        block, group, idx = path

        # Experiment, pd (powder diffraction), block
        if block.startswith('pd_'):
            blockName = block[3:]
            category = None
            name = None
            rowIndex = -1

            # wavelength
            if group == 'wavelength':
                category = '_diffrn_radiation_wavelength'
                name = 'wavelength'

            # offset_ttheta
            elif group == 'offset_ttheta':
                category = '_pd_calib'
                name = '2theta_offset'

            # resolution_parameters
            elif group == 'resolution_parameters':
                category = '_pd_instr'
                if idx[0] == 0:
                    name = 'resolution_u'
                elif idx[0] == 1:
                    name = 'resolution_v'
                elif idx[0] == 2:
                    name = 'resolution_w'
                elif idx[0] == 3:
                    name = 'resolution_x'
                elif idx[0] == 4:
                    name = 'resolution_y'
                elif idx[0] == 5:
                    name = 'resolution_z'

            # asymmetry_parameters
            elif group == 'asymmetry_parameters':
                category = '_pd_instr'
                if idx[0] == 0:
                    name = 'reflex_asymmetry_p1'
                elif idx[0] == 1:
                    name = 'reflex_asymmetry_p2'
                elif idx[0] == 2:
                    name = 'reflex_asymmetry_p3'
                elif idx[0] == 3:
                    name = 'reflex_asymmetry_p4'

            # background_ttheta
            elif group == 'background_ttheta':
                category = '_pd_background'
                name = 'line_segment_X'
                rowIndex = idx[0]

            # background_intensity
            elif group == 'background_intensity':
                category = '_pd_background'
                name = 'line_segment_intensity'
                rowIndex = idx[0]

            # phase_scale
            elif group == 'phase_scale':
                category = '_pd_phase_block'
                name = 'scale'
                rowIndex = idx[0]

            blockIdx = [block['name']['value'] for block in self._dataBlocksNoMeas].index(blockName)

            if rowIndex == -1:
                return self.dataBlocksNoMeas[blockIdx]['params'][category][name][field]
            else:
                return self.dataBlocksNoMeas[blockIdx]['loops'][category][rowIndex][name][field]

        return None

    def editDataBlockByLmfitParams(self, params):
        for param in params.values():
            block, group, idx = Data.strToCryspyDictParamPath(param.name)

            # pd (powder diffraction) block
            if block.startswith('pd_') or block.startswith('tof_') or block.startswith('diffrn_'):
                if block.startswith('pd_'):  # pd-cwl
                    blockName = block[3:]
                elif block.startswith('tof_'):  # pd-tof
                    blockName = block[4:]
                elif block.startswith('diffrn_'):  # sg-cwl
                    blockName = block[7:]

                category = None
                name = None
                rowIndex = -1
                value = param.value

                # wavelength
                if group == 'wavelength':
                    category = '_diffrn_radiation_wavelength'
                    name = 'wavelength'

                # offset_ttheta
                elif group == 'offset_ttheta':
                    category = '_pd_calib'
                    name = '2theta_offset'
                    value = np.rad2deg(value)

                # resolution_parameters
                elif group == 'resolution_parameters':
                    category = '_pd_instr'
                    if idx[0] == 0:
                        name = 'resolution_u'
                    elif idx[0] == 1:
                        name = 'resolution_v'
                    elif idx[0] == 2:
                        name = 'resolution_w'
                    elif idx[0] == 3:
                        name = 'resolution_x'
                    elif idx[0] == 4:
                        name = 'resolution_y'
                    elif idx[0] == 5:
                        name = 'resolution_z'

                # asymmetry_parameters
                elif group == 'asymmetry_parameters':
                    category = '_pd_instr'
                    if idx[0] == 0:
                        name = 'reflex_asymmetry_p1'
                    elif idx[0] == 1:
                        name = 'reflex_asymmetry_p2'
                    elif idx[0] == 2:
                        name = 'reflex_asymmetry_p3'
                    elif idx[0] == 3:
                        name = 'reflex_asymmetry_p4'

                # background_ttheta
                elif group == 'background_ttheta':
                    category = '_pd_background'
                    name = 'line_segment_X'
                    rowIndex = idx[0]
                    value = np.rad2deg(value)

                # background_intensity
                elif group == 'background_intensity':
                    category = '_pd_background'
                    name = 'line_segment_intensity'
                    rowIndex = idx[0]

                # phase_scale
                elif group == 'phase_scale':
                    if block.startswith('diffrn_'):  # sg-cwl
                        category = '_exptl_crystal'
                        name = 'scale'
                        rowIndex = 0
                    elif block.startswith('pd_') or block.startswith('tof_'):  # pd-cwl, pd-tof
                        category = '_pd_phase_block'
                        name = 'scale'
                        rowIndex = idx[0]

                # phase_scale
                elif group == 'phase_scale':
                    category = '_pd_phase_block'
                    name = 'scale'
                    rowIndex = idx[0]

                # zero
                elif group == 'zero':
                    category = '_pd_instr'
                    name = 'zero'

                # dtt1 (TOF)
                elif group == 'dtt1':
                    category = '_pd_instr'
                    name = 'dtt1'

                # dtt2 (TOF)
                elif group == 'dtt2':
                    category = '_pd_instr'
                    name = 'dtt2'

                # profile_alphas (TOF)
                elif group == 'profile_alphas':
                    category = '_pd_instr'
                    if idx[0] == 0:
                        name = 'alpha0'
                    elif idx[0] == 1:
                        name = 'alpha1'

                # profile_betas (TOF)
                elif group == 'profile_betas':
                    category = '_pd_instr'
                    if idx[0] == 0:
                        name = 'beta0'
                    elif idx[0] == 1:
                        name = 'beta1'

                # profile_sigmas (TOF)
                elif group == 'profile_sigmas':
                    category = '_pd_instr'
                    if idx[0] == 0:
                        name = 'sigma0'
                    elif idx[0] == 1:
                        name = 'sigma1'
                    elif idx[0] == 2:
                        name = 'sigma2'

                # background_coefficients (TOF)
                elif group == 'background_coefficients':
                    category = '_tof_background'
                    name = f'coeff{idx[0]+1}'

                # extinction_mosaicity (sg-cwl)
                elif group == 'extinction_mosaicity':
                    category = '_extinction'
                    name = 'mosaicity'

                # extinction_radius (sg-cwl)
                elif group == 'extinction_radius':
                    category = '_extinction'
                    name = 'radius'

                # Unrecognized group
                else:
                    console.error(f'Unrecognized group {group} in parameter {param.name}')
                    return

                error = 0
                if param.stderr is not None:
                    if param.stderr < 1e-6:
                        error = 1e-6  # Temporary solution to compensate for too small uncertanties after lmfit
                    else:
                        error = param.stderr

                value = float(value)  # convert float64 to float (needed for QML access)
                error = float(error)  # convert float64 to float (needed for QML access)
                blockIdx = [block['name']['value'] for block in self._dataBlocksNoMeas].index(blockName)

                if rowIndex == -1:
                    self.editDataBlockMainParam(blockIdx, category, name, 'value', value)
                    self.editDataBlockMainParam(blockIdx, category, name, 'error', error)
                else:
                    self.editDataBlockLoopParam(blockIdx, category, name, rowIndex, 'value', value)
                    self.editDataBlockLoopParam(blockIdx, category, name, rowIndex, 'error', error)

            # Model (crystal phase) block
            elif block.startswith('crystal_'):
                pass

            # Unknown block
            else:
                console.error(f'Unrecognized parameter {param.name}')


    def runCryspyCalculations(self):
        result = rhochi_calc_chi_sq_by_dictionary(
            self._proxy.data._cryspyDict,
            dict_in_out=self._proxy.data._cryspyInOutDict,
            flag_use_precalculated_data=False,
            flag_calc_analytical_derivatives=False)

        console.debug(IO.formatMsg('sub', 'Cryspy calculations', 'finished'))

        chiSq = result[0]
        self._proxy.fitting._pointsCount = result[1]
        self._proxy.fitting._freeParamsCount = len(result[4])
        self._proxy.fitting.chiSq = chiSq / (self._proxy.fitting._pointsCount - self._proxy.fitting._freeParamsCount)

        gofLastIter = self._proxy.fitting.chiSq  # NEED FIX
        if self._proxy.fitting.chiSqStart is None:
            self._proxy.status.goodnessOfFit = f'{gofLastIter:0.2f}'                           # NEED move to connection
        else:
            gofStart = self._proxy.fitting.chiSqStart # NEED FIX
            self._proxy.status.goodnessOfFit = f'{gofStart:0.2f} → {gofLastIter:0.2f}'  # NEED move to connection
        if not self._proxy.fitting._freezeChiSqStart:
            self._proxy.fitting.chiSqStart = self._proxy.fitting.chiSq

    def setMeasuredArraysForSingleExperiment(self, idx):
        cryspyDict = self._proxy.data._cryspyDict
        cryspyInOutDict = self._proxy.data._cryspyInOutDict

        diffrn_radiation_type = self._proxy.experiment.dataBlocksNoMeas[idx]['params']['_diffrn_radiation']['type']['value']
        sample_type = self._proxy.experiment.dataBlocksNoMeas[idx]['params']['_sample']['type']['value']

        ed_name = self._proxy.experiment.dataBlocksNoMeas[idx]['name']['value']
        if diffrn_radiation_type == 'cwl' and sample_type == 'pd':
            cryspy_block_name = f'pd_{ed_name}'
        elif diffrn_radiation_type == 'tof' and sample_type == 'pd':
            cryspy_block_name = f'tof_{ed_name}'
        elif diffrn_radiation_type == 'cwl' and sample_type == 'sg':
            cryspy_block_name = f'diffrn_{ed_name}'

        # X data
        if sample_type == 'pd' and diffrn_radiation_type == 'cwl':
            x_array = cryspyInOutDict[cryspy_block_name]['ttheta']
            x_array = np.rad2deg(x_array)
        if sample_type == 'pd' and diffrn_radiation_type == 'tof':
            x_array = cryspyInOutDict[cryspy_block_name]['time']
        elif sample_type == 'sg':
            x_array = cryspyInOutDict[cryspy_block_name]['sthovl']
        self.setXArray(x_array, idx)

        # Measured Y data
        if sample_type == 'pd':
            y_meas_array = cryspyInOutDict[cryspy_block_name]['signal_exp'][0]
        elif sample_type == 'sg':
            y_meas_array = cryspyDict[cryspy_block_name]['intensity_es'][0]
        self.setYMeasArray(y_meas_array, idx)

        # Standard deviation of the measured Y data
        if sample_type == 'pd':
            sy_meas_array = cryspyInOutDict[cryspy_block_name]['signal_exp'][1]
        elif sample_type == 'sg':
            sy_meas_array = cryspyDict[cryspy_block_name]['intensity_es'][1]
        self.setSYMeasArray(sy_meas_array, idx)

    def calculatedYBkgArray_OLD(self, cryspy_block_idx, cryspy_block_name, x_array_name):
        dataBlockNoMeas = self._dataBlocksNoMeas[cryspy_block_idx]
        pd_background = dataBlockNoMeas['loops']['_pd_background']
        x_bkg_points = np.array([item['line_segment_X']['value'] for item in pd_background])
        y_bkg_points = np.array([item['line_segment_intensity']['value'] for item in pd_background])
        cryspyInOutDict = self._proxy.data._cryspyInOutDict
        desired_x_bkg_array = cryspyInOutDict[cryspy_block_name][x_array_name]
        desired_y_bkg_array = np.interp(desired_x_bkg_array, x_bkg_points, y_bkg_points)
        return desired_y_bkg_array

    def calculatedYBkgArray(self, cryspy_block_idx, cryspy_block_name, x_array_name):
        cryspyInOutDict = self._proxy.data._cryspyInOutDict
        y_array_name = 'signal_background'
        y_bkg_array = cryspyInOutDict[cryspy_block_name][y_array_name]
        return y_bkg_array

    def setCalculatedArraysForSingleExperiment(self, idx):
        cryspyDict = self._proxy.data._cryspyDict
        cryspyInOutDict = self._proxy.data._cryspyInOutDict

        diffrn_radiation_type = self._proxy.experiment.dataBlocksNoMeas[idx]['params']['_diffrn_radiation']['type']['value']
        sample_type = self._proxy.experiment.dataBlocksNoMeas[idx]['params']['_sample']['type']['value']

        ed_name = self._proxy.experiment.dataBlocksNoMeas[idx]['name']['value']
        if diffrn_radiation_type == 'cwl' and sample_type == 'pd':
            cryspy_block_name = f'pd_{ed_name}'
            x_array_name = 'ttheta'
        elif diffrn_radiation_type == 'tof' and sample_type == 'pd':
            cryspy_block_name = f'tof_{ed_name}'
            x_array_name = 'time'
        elif diffrn_radiation_type == 'cwl' and sample_type == 'sg':
            cryspy_block_name = f'diffrn_{ed_name}'

        if sample_type == 'pd' and 'signal_plus' not in list(cryspyInOutDict[cryspy_block_name].keys()):
            return
        if sample_type == 'sg' and 'intensity_calc' not in list(cryspyInOutDict[cryspy_block_name].keys()):
            return

        if sample_type == 'sg':
            # Calculated Y data (Ycalc)
            y_calc_total_array = cryspyInOutDict[cryspy_block_name]['intensity_calc']
            self.setYCalcTotalArray(y_calc_total_array, idx)

            # Residual (Ymeas - Ycalc)
            y_meas_array = self._yMeasArrays[idx]
            y_resid_array = y_meas_array - y_calc_total_array
            self.setYResidArray(y_resid_array, idx)

            # Bragg peaks data
            modelName = self._proxy.model.dataBlocks[0]['name']['value']
            x_bragg_array = cryspyInOutDict[cryspy_block_name]['sthovl']
            xBraggDict = { modelName: x_bragg_array }
            self.setXBraggDict(xBraggDict, idx)

        elif sample_type == 'pd':
            # Background Y data # NEED FIX: use calculatedYBkgArray()
            #y_bkg_array = cryspyInOutDict[cryspy_block_name]['signal_background']
            y_bkg_array = self.calculatedYBkgArray(idx, cryspy_block_name, x_array_name)
            self.setYBkgArray(y_bkg_array, idx)

            # Total calculated Y data (sum of all phases up and down polarisation plus background)
            y_calc_total_array = cryspyInOutDict[cryspy_block_name]['signal_plus'] + \
                                 cryspyInOutDict[cryspy_block_name]['signal_minus'] + \
                                 y_bkg_array
            self.setYCalcTotalArray(y_calc_total_array, idx)

            # Residual (Ymeas -Ycalc)
            y_meas_array = self._yMeasArrays[idx]
            y_resid_array = y_meas_array - y_calc_total_array
            self.setYResidArray(y_resid_array, idx)

            # Bragg peaks data
            #cryspyInOutDict[cryspy_name]['dict_in_out_co2sio4']['index_hkl'] # [0] - h array, [1] - k array, [2] - l array
            #cryspyInOutDict[cryspy_name]['dict_in_out_co2sio4']['ttheta_hkl'] # need rad2deg
            dict_name_prefix = 'dict_in_out'
            modelNames = [key[len(dict_name_prefix)+1:] for key in cryspyInOutDict[cryspy_block_name].keys() if dict_name_prefix in key]
            xBraggDict = {}
            for modelName in modelNames:
                x_bragg_array = cryspyInOutDict[cryspy_block_name][f'{dict_name_prefix}_{modelName}'][f'{x_array_name}_hkl']
                if diffrn_radiation_type == 'cwl':
                    x_bragg_array = np.rad2deg(x_bragg_array)
                xBraggDict[modelName] = x_bragg_array
            self.setXBraggDict(xBraggDict, idx)

    def setChartRangesForSingleExperiment(self, idx):
        x_array = self._xArrays[idx]
        y_meas_array = self._yMeasArrays[idx]
        y_calc_total_array = self._yCalcTotalArrays[idx]
        # pd
        x_min = x_array.min()
        x_max = x_array.max()
        y_min = y_meas_array.min()
        y_max = y_meas_array.max()
        y_range = y_max - y_min
        y_extra = y_range * 0.1
        y_min -= y_extra
        y_max += y_extra
        # sc
        #x2_min = np.minimum(y_meas_array.min(), y_calc_total_array.min())
        #x2_max = np.maximum(y_meas_array.max(), y_calc_total_array.max())
        x2_min = y_meas_array.min()
        x2_max = y_meas_array.max()
        x2_range = x2_max - x2_min
        x2_extra = x2_range * 0.1
        x2_min -= x2_extra
        x2_max += x2_extra
        y2_min = x2_min
        y2_max = x2_max
        #
        ranges = {'xMin': float(x_min),
                  'xMax': float(x_max),
                  'yMin': float(y_min),
                  'yMax': float(y_max),
                  'x2Min': float(x2_min),
                  'x2Max': float(x2_max),
                  'y2Min': float(y2_min),
                  'y2Max': float(y2_max)}
        self.setChartRanges(ranges, idx)

    def replaceArrays(self):
        for idx in range(len(self._dataBlocksMeasOnly)):
            self.setCalculatedArraysForSingleExperiment(idx)

    def addArraysAndChartRanges(self):
        for idx in range(len(self._xArrays), len(self._dataBlocksMeasOnly)):
            self.setMeasuredArraysForSingleExperiment(idx)
            self.setCalculatedArraysForSingleExperiment(idx)
            self.setChartRangesForSingleExperiment(idx)

    def setXArray(self, xArray, idx):
        try:
            self._xArrays[idx] = xArray
            console.debug(IO.formatMsg('sub', 'X', f'experiment no. {idx + 1}', 'in intern dataset', 'replaced'))
        except IndexError:
            self._xArrays.append(xArray)
            console.debug(IO.formatMsg('sub', 'X', f'experiment no. {len(self._xArrays)}', 'to intern dataset', 'added'))

    def setYMeasArray(self, yMeasArray, idx):
        try:
            self._yMeasArrays[idx] = yMeasArray
            console.debug(IO.formatMsg('sub', 'Y-meas', f'experiment no. {idx + 1}', 'in intern dataset', 'replaced'))
        except IndexError:
            self._yMeasArrays.append(yMeasArray)
            console.debug(IO.formatMsg('sub', 'Y-meas', f'experiment no. {len(self._yMeasArrays)}', 'to intern dataset', 'added'))
        self.yMeasArraysChanged.emit()

    def setSYMeasArray(self, syMeasArray, idx):
        try:
            self._syMeasArrays[idx] = syMeasArray
            console.debug(IO.formatMsg('sub', 'sY-meas', f'experiment no. {idx + 1}', 'in intern dataset', 'replaced'))
        except IndexError:
            self._syMeasArrays.append(syMeasArray)
            console.debug(IO.formatMsg('sub', 'sY-meas', f'experiment no. {len(self._syMeasArrays)}', 'to intern dataset', 'added'))

    def setYBkgArray(self, yBkgArray, idx):
        try:
            self._yBkgArrays[idx] = yBkgArray
            console.debug(IO.formatMsg('sub', 'Y-bkg (inter)', f'experiment no. {idx + 1}', 'in intern dataset', 'replaced'))
        except IndexError:
            self._yBkgArrays.append(yBkgArray)
            console.debug(IO.formatMsg('sub', 'Y-bkg (inter)', f'experiment no. {len(self._yBkgArrays)}', 'to intern dataset', 'added'))
        self.yBkgArraysChanged.emit()

    def setYCalcTotalArray(self, yCalcTotalArray, idx):
        try:
            self._yCalcTotalArrays[idx] = yCalcTotalArray
            console.debug(IO.formatMsg('sub', 'Y-calc (total)', f'experiment no. {idx + 1}', 'in intern dataset', 'replaced'))
        except IndexError:
            self._yCalcTotalArrays.append(yCalcTotalArray)
            console.debug(IO.formatMsg('sub', 'Y-calc (total)', f'experiment no. {len(self._yCalcTotalArrays)}', 'to intern dataset', 'added'))
        self.yCalcTotalArraysChanged.emit()

    def setYResidArray(self, yResidArray, idx):
        try:
            self._yResidArrays[idx] = yResidArray
            console.debug(IO.formatMsg('sub', 'Y-resid (meas-calc)', f'experiment no. {idx + 1}', 'in intern dataset', 'replaced'))
        except IndexError:
            self._yResidArrays.append(yResidArray)
            console.debug(IO.formatMsg('sub', 'Y-resid (meas-calc)', f'experiment no. {len(self._yResidArrays)}', 'to intern dataset', 'added'))
        self.yResidArraysChanged.emit()

    def setXBraggDict(self, xBraggDict, idx):
        try:
            self._xBraggDicts[idx] = xBraggDict
            console.debug(IO.formatMsg('sub', 'X-Bragg (peaks)', f'experiment no. {idx + 1}', 'in intern dataset', 'replaced'))
        except IndexError:
            self._xBraggDicts.append(xBraggDict)
            console.debug(IO.formatMsg('sub', 'X-Bragg (peaks)', f'experiment no. {len(self._xBraggDicts)}', 'to intern dataset', 'added'))
        self.xBraggDictsChanged.emit()

    def setChartRanges(self, ranges, idx):
        try:
            self._chartRanges[idx] = ranges
            console.debug(IO.formatMsg('sub', 'Chart ranges', f'experiment no. {idx + 1}', 'in intern dataset', 'replaced'))
        except IndexError:
            self._chartRanges.append(ranges)
            console.debug(IO.formatMsg('sub', 'Chart ranges', f'experiment no. {len(self._chartRanges)}', 'to intern dataset', 'added'))
        self.chartRangesChanged.emit()

    def setDataBlocksCifNoMeas(self):
        self._dataBlocksCifNoMeas = [CryspyParser.dataBlockToCif(block) for block in self._dataBlocksNoMeas]
        console.debug(IO.formatMsg('sub', f'{len(self._dataBlocksCifNoMeas)} experiment(s)', 'without meas data', 'to CIF string', 'converted'))
        self.dataBlocksCifNoMeasChanged.emit()

    def setDataBlocksCifMeasOnly(self):
        self._dataBlocksCifMeasOnly = [CryspyParser.dataBlockToCif(block, includeBlockName=False) for block in self._dataBlocksMeasOnly]
        console.debug(IO.formatMsg('sub', f'{len(self._dataBlocksCifMeasOnly)} experiment(s)', 'meas data only', 'to CIF string', 'converted'))
        self.dataBlocksCifMeasOnlyChanged.emit()

    def setDataBlocksCif(self):
        self.setDataBlocksCifNoMeas()
        self.setDataBlocksCifMeasOnly()
        cifMeasOnlyReduced =  [block.split('\n')[:10] + ['...'] + block.split('\n')[-6:] for block in self._dataBlocksCifMeasOnly]
        cifMeasOnlyReduced = ['\n'.join(block) for block in cifMeasOnlyReduced]
        cifMeasOnlyReduced = [f'\n{block}' for block in cifMeasOnlyReduced]
        cifMeasOnlyReduced = [block.rstrip() for block in cifMeasOnlyReduced]
        self._dataBlocksCif = [[noMeas, measOnlyReduced] for (noMeas, measOnlyReduced) in zip(self._dataBlocksCifNoMeas, cifMeasOnlyReduced)]
        console.debug(IO.formatMsg('sub', f'{len(self._dataBlocksCif)} experiment(s)', 'simplified meas data', 'to CIF string', 'converted'))
        self.dataBlocksCifChanged.emit()
