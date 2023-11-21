# SPDX-FileCopyrightText: 2023 EasyDiffraction contributors
# SPDX-License-Identifier: BSD-3-Clause
# © © 2023 Contributors to the EasyDiffraction project <https://github.com/easyscience/EasyDiffractionApp>

import os
import copy
import numpy as np
import pathlib

from PySide6.QtCore import QObject, Signal, Slot, Property
from PySide6.QtCore import QFile, QTextStream, QIODevice
from PySide6.QtQml import QJSValue

# Parameter is App-centric, should be moved to the App
from easyDiffractionLib.io.cryspy_parser import CryspyParser, Parameter
from easyDiffractionLib.io.cif import dataBlockToCif, cifV2ToV1
from easyDiffractionLib.io.Helpers import formatMsg, generalizePath
from easyDiffractionLib.Jobs import get_job_from_file

from EasyApp.Logic.Logging import console
from Logic.Data import Data

try:
    import cryspy
    from cryspy.H_functions_global.function_1_cryspy_objects import \
        str_to_globaln
    console.debug('CrysPy module imported')
except ImportError:
    console.debug('No CrysPy module found')


_DEFAULT_DATA_BLOCK_NO_MEAS = """data_pnd

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

_DEFAULT_DATA_BLOCK = _DEFAULT_DATA_BLOCK_NO_MEAS + """36.5 1    1
37.0 10   3
37.5 700  25
38.0 1100 30
38.5 50   7
39.0 1    1
"""

BLOCK2JOB = {
    'wavelength': 'wavelength',
    '_diffrn_radiation_wavelength': 'parameters',
    'resolution_u': 'resolution_u',
    '_pd_instr': 'parameters',
    'resolution_v': 'resolution_v',
    'resolution_w': 'resolution_w',
    'resolution_x': 'resolution_x',
    'resolution_y': 'resolution_y',
    'reflex_asymmetry_p1': 'reflex_asymmetry_p1',
    'reflex_asymmetry_p2': 'reflex_asymmetry_p2',
    'reflex_asymmetry_p3': 'reflex_asymmetry_p3',
    'reflex_asymmetry_p4': 'reflex_asymmetry_p4',
    '_pd_calib': 'pattern',
    '2theta_offset': 'zero_shift',

    '_pd_background': 'backgrounds',
    'line_segment_X': 'x',
    'line_segment_intensity': 'y',
    'scale': 'scale',
    '_pd_phase_block': 'phases',
}

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

    def __init__(self, parent, interface=None):
        super().__init__(parent)
        self._proxy = parent

        self._defined = False
        self._currentIndex = -1

        self._interface = interface
        self._job = None
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
        console.debug(formatMsg('main', f'Experiment defined: {newValue}'))
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
        self.loadExperimentsFromEdCif(_DEFAULT_DATA_BLOCK)

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
        for idx, fpath in enumerate(fpaths):
            fpath = fpath.toLocalFile()
            fpath = generalizePath(fpath)
            _, fext = os.path.splitext(fpath)
            console.debug(f"Loading experiment(s) from: {fpath}")
            with open(fpath, 'r') as file:
                fileContent = file.read()
            if fext == '.xye':
                fileContent = _DEFAULT_DATA_BLOCK_NO_MEAS + fileContent
            self.loadExperimentsFromEdCif(fileContent)

            job_name = pathlib.Path(fpath).stem
            phases = self._proxy._model.phases
            _, self._job = get_job_from_file(fpath, job_name, phases=phases, interface=self._interface)

            blocks = self.jobToBlock(job=self._job)
            self._dataBlocksNoMeas.append(blocks)

            blocks = self.jobToData(job=self._job)
            self._dataBlocksMeasOnly.append(blocks)

            self._currentIndex = len(self.dataBlocksNoMeas) - 1
            if not self.defined:
                self.defined = bool(len(self.dataBlocksNoMeas))
            self.dataBlocksChanged.emit()

    def jobToBlock(self, job=None):
        '''
        Convert a Job object to a list of data blocks, without the measured data
        '''
        if job is None:
            return
        # current experiment
        cifDict = 'core'
        dataBlock = {'name': '', 'params': {}, 'loops': {}}
        dataBlock['name'] = dict(Parameter(
            value = job.name,
            icon = 'microscope'))
        param = 'params'
        category = '_diffrn_radiation'
        url = 'https://docs.easydiffraction.org/app/project/dictionaries/'
        dataBlock[param][category] = {}
        name = 'probe'
        dataBlock[param][category][name] = dict(Parameter(
                        value = 'neutron',  # This needs proper parsing in the library
                        permittedValues = ['neutron', 'x-ray'],
                        category = category,
                        name = name,
                        shortPrettyName = name,
                        url = url + category,
                        cifDict = cifDict
                    ))
        name = 'wavelength'
        category = '_diffrn_radiation_wavelength'
        prettyCategory = 'radiation'
        dataBlock[param][category] = {}
        dataBlock[param][category][name] = dict(Parameter(
                        value = job.parameters.wavelength.raw_value,
                        error = job.parameters.wavelength.error,
                        category = category,
                        prettyCategory = prettyCategory,
                        name = name,
                        prettyName = name,
                        shortPrettyName = name,
                        icon = prettyCategory,
                        url = url + category,
                        cifDict = cifDict,
                        absDelta = 0.01,
                        units = 'Å',
                        fittable = True,
                        fit = not job.parameters.wavelength.fixed
                    ))
        category = '_pd_instr'
        prettyCategory = 'inst'
        icon = 'grip-lines-vertical'
        name = 'resolution_u'
        dataBlock[param][category] = {}
        dataBlock[param][category][name] = dict(Parameter(
                        value = job.parameters.resolution_u.raw_value,
                        error = job.parameters.resolution_u.error,
                        category = category,
                        prettyCategory = prettyCategory,
                        name = name,
                        prettyName = name,
                        shortPrettyName = 'u',
                        icon = icon,
                        url = url + category,
                        absDelta = 0.1,
                        fittable = True,
                        fit = not job.parameters.resolution_u.fixed
                    ))
        name = 'resolution_v'
        dataBlock[param][category][name] = dict(Parameter(
                        value = job.parameters.resolution_v.raw_value,
                        error = job.parameters.resolution_v.error,
                        category = category,
                        prettyCategory = prettyCategory,
                        name = name,
                        prettyName = name,
                        shortPrettyName = 'v',
                        icon = icon,
                        url = url + category,
                        absDelta = 0.1,
                        fittable = True,
                        fit = not job.parameters.resolution_v.fixed
                    ))
        name = 'resolution_w'
        dataBlock[param][category][name] = dict(Parameter(
                        value = job.parameters.resolution_w.raw_value,
                        error = job.parameters.resolution_w.error,
                        category = category,
                        prettyCategory = prettyCategory,
                        name = name,
                        prettyName = name,
                        shortPrettyName = 'w',
                        icon = icon,
                        url = url + category,
                        absDelta = 0.1,
                        fittable = True,
                        fit = not job.parameters.resolution_w.fixed
                    ))
        name = 'resolution_x'
        dataBlock[param][category][name] = dict(Parameter(
                        value = job.parameters.resolution_x.raw_value,
                        error = job.parameters.resolution_x.error,
                        category = category,
                        prettyCategory = prettyCategory,
                        name = name,
                        prettyName = name,
                        shortPrettyName = 'x',
                        icon = icon,
                        url = url + category,
                        absDelta = 0.1,
                        fittable = True,
                        fit = not job.parameters.resolution_x.fixed
                    ))
        name = 'resolution_y'
        dataBlock[param][category][name] = dict(Parameter(
                        job.parameters.resolution_y.raw_value,
                        error = job.parameters.resolution_y.error,
                        category = category,
                        prettyCategory = prettyCategory,
                        name = name,
                        prettyName = name,
                        shortPrettyName = 'y',
                        icon = icon,
                        url = url + category,
                        absDelta = 0.1,
                        fittable = True,
                        fit = not job.parameters.resolution_y.fixed
                    ))
        icon = 'balance-scale-left'
        name = 'reflex_asymmetry_p1'
        dataBlock[param][category][name] = dict(Parameter(
                            job.parameters.reflex_asymmetry_p1.raw_value,
                            error = job.parameters.reflex_asymmetry_p1.error,
                            category = category,
                            prettyCategory = prettyCategory,
                            name = name,
                            prettyName = "asymmetry p1",
                            shortPrettyName = "p1",
                            icon = icon,
                            url = url + category,
                            absDelta = 0.5,
                            fittable = True,
                            fit = not job.parameters.reflex_asymmetry_p1.fixed
                        ))
        name = 'reflex_asymmetry_p2'
        dataBlock[param][category][name] = dict(Parameter(
                            job.parameters.reflex_asymmetry_p2.raw_value,
                            error = job.parameters.reflex_asymmetry_p2.error,
                            category = category,
                            prettyCategory = prettyCategory,
                            name = name,
                            prettyName = "asymmetry p2",
                            shortPrettyName = "p2",
                            icon = icon,
                            url = url + category,
                            absDelta = 0.5,
                            fittable = True,
                            fit = not job.parameters.reflex_asymmetry_p2.fixed
                        ))
        name = 'reflex_asymmetry_p3'
        dataBlock[param][category][name] = dict(Parameter(
                            job.parameters.reflex_asymmetry_p3.raw_value,
                            error = job.parameters.reflex_asymmetry_p3.error,
                            category = category,
                            prettyCategory = prettyCategory,
                            name = name,
                            prettyName = "asymmetry p3",
                            shortPrettyName = "p3",
                            icon = icon,
                            url = url + category,
                            absDelta = 0.5,
                            fittable = True,
                            fit = not job.parameters.reflex_asymmetry_p3.fixed
                        ))
        name = 'reflex_asymmetry_p4'
        dataBlock[param][category][name] = dict(Parameter(
                            job.parameters.reflex_asymmetry_p4.raw_value,
                            error = job.parameters.reflex_asymmetry_p4.error,
                            category = category,
                            prettyCategory = prettyCategory,
                            name = name,
                            prettyName = "asymmetry p4",
                            shortPrettyName = "p4",
                            icon = icon,
                            url = url + category,
                            absDelta = 0.5,
                            fittable = True,
                            fit = not job.parameters.reflex_asymmetry_p4.fixed
                        ))

        # _pd_calib
        category = '_pd_calib'
        prettyCategory = 'calib'
        icon = 'arrows-alt-h'
        name = '2theta_offset'
        dataBlock[param][category] = {}
        dataBlock[param][category][name] = dict(Parameter(
                            job.pattern.zero_shift.raw_value,
                            error = job.pattern.zero_shift.error,
                            category = category,
                            prettyCategory = prettyCategory,
                            name = name,
                            prettyName = '2θ offset',
                            shortPrettyName = "offset",
                            icon = icon,
                            url = url + category,
                            cifDict = 'pd',
                            absDelta = 0.2,
                            units = '°',
                            fittable = True,
                            fit = not job.pattern.zero_shift.fixed
                        ))


        # _pd_meas
        category = '_pd_meas'
        name = '2theta_range_min'
        dataBlock[param][category] = {}
        x_name = job.name + '_' + job.name + '_tth'
        xmin = job.datastore.store[x_name].data[0]
        dataBlock[param][category][name] = dict(Parameter(
                            str(xmin),
                            optional = True,
                            category = category,
                            name = name,
                            prettyName = "range min",
                            shortPrettyName = "min",
                            url = url,
                            cifDict = 'pd'
                        ))
        name = '2theta_range_max'
        xmax = job.datastore.store[x_name].data[-1]
        dataBlock[param][category][name] = dict(Parameter(
                            str(xmax),
                            optional = True,
                            category = category,
                            name = name,
                            prettyName = "range max",
                            shortPrettyName = "max",
                            url = url,
                            cifDict = 'pd',
                        ))
        name = '2theta_range_inc'
        # inc = (xmax-xmin)/len(job.datastore.store[x_name].data)
        # 2nd point - 1st point (to change later)
        inc = job.datastore.store[x_name].data[1] - xmin
        inc = round(inc, 4)
        dataBlock[param][category][name] = dict(Parameter(
                            str(inc),
                            optional = True,
                            category = category,
                            name = name,
                            prettyName = "range inc",
                            shortPrettyName = "inc",
                            url = url,
                            cifDict = 'pd',
                        ))

        # loops
        #
        param = 'loops'

        # background
        category = '_pd_background'
        ed_bkg_points = []
        job_bg_points = job.backgrounds[0]
        for idx, bkg_point in enumerate(job_bg_points):
            ed_bkg_point = {}
            name = 'line_segment_X'
            ed_bkg_point[name] = dict(Parameter(
                str(bkg_point.x.raw_value),
                idx = idx,
                category = category,
                name = name,
                prettyName = '2θ',
                shortPrettyName = '2θ',
                url = url + category,
                cifDict = 'pd'
            ))
            name = 'line_segment_intensity'
            ed_bkg_point[name] = dict(Parameter(
                bkg_point.y.raw_value,
                error = bkg_point.y.error,
                idx = idx,
                category = category,
                prettyCategory = 'bkg',
                rowName = f'{bkg_point.x.raw_value:g}°',  # formatting float to str without trailing zeros
                name = name,
                prettyName = 'intensity',
                shortPrettyName = 'Ibkg',
                icon = 'mountain',
                categoryIcon = 'wave-square',
                url = url + category,
                cifDict = 'pd',
                pctDelta = 25,
                fittable = True,
                fit = not bkg_point.y.fixed
            ))
            name = 'X_coordinate'
            ed_bkg_point[name] = dict(Parameter(
                '2theta',
                idx = idx,
                category = category,
                name = name,
                prettyName = 'X coord',
                shortPrettyName = 'X coord',
                url = url + category,
                cifDict = 'pd'
            ))

            ed_bkg_points.append(ed_bkg_point)
        dataBlock[param] = {}
        dataBlock[param][category] = ed_bkg_points

        category = '_pd_phase_block'
        category_url = '_phase'
        ed_phase_blocks = []
        for idx, phase in enumerate(job.phases):
            ed_phase_block = {}
            scale_param = phase.scale
            id_param = phase.name
            name = 'id'
            ed_phase_block[name] = dict(Parameter(
                id_param,
                idx = idx,
                category = category,
                name = name,
                shortPrettyName = 'label',
                url = url + category_url,
                cifDict = 'pd'
            ))
            name = 'scale'
            ed_phase_block[name] = dict(Parameter(
                scale_param.raw_value,
                error = scale_param.error,
                rowName = id_param,
                idx = idx,
                category = category,
                name = name,
                prettyName = name,
                shortPrettyName = name,
                categoryIcon='layer-group',
                icon = 'weight',
                url = url + category_url,
                cifDict = 'pd',
                pctDelta = 25,
                fittable = True,
                fit = not scale_param.fixed
            ))
            ed_phase_blocks.append(ed_phase_block)
        dataBlock[param][category] = ed_phase_blocks
        return dataBlock

    def jobToData(self, job=None):
        '''
        Convert a Job object to a data blocks containing the measured data
        '''
        if job is None:
            return
         # current experiment
        cifDict = 'pd'
        url = 'https://docs.easydiffraction.org/app/project/dictionaries/'
        dataBlock = {'name': {}, 'loops': {}}
        dataBlock['name'] = dict(Parameter(
            value = job.name,
            icon = 'microscope'))
        dataBlock['name'] = job.name
        # loops
        #
        param = 'loops'

        # background
        category = '_pd_meas'
        dataBlock[param][category] = {}
        ed_points = {}
        x_name = job.name + '_' + job.name + '_tth'
        y_name = job.name + '_' + job.name + '_I0'
        err_name = job.name + '_' + job.name + '_I1'
        x_points = job.datastore.store[x_name].data
        y_points = np.ones_like(x_points) #job.datastore.store[y_name].data
        err_points = job.datastore.store[err_name].data

        name = '2theta_scan'

        ed_points[name] = dict(Parameter(
            x_points,
            category = category,
            name = name,
            prettyName = '2θ',
            shortPrettyName = '2θ',
            url = url + category,
            cifDict = cifDict
        ))
        name = 'intensity_total'
        ed_points[name] = dict(Parameter(
            y_points,
            category = category,
            name = name,
            prettyName = 'intensity',
            shortPrettyName = 'I',
            url = url + category,
            cifDict = cifDict,
        ))
        name = 'intensity_total_su'
        ed_points[name] = dict(Parameter(
            err_points,
            category = category,
            name = name,
            shortPrettyName = 'sI',
            url = url + category,
            cifDict = cifDict,
        ))
        ed_points = [ed_points]
        dataBlock[param][category] = ed_points
        return dataBlock

    @Slot(str)
    def loadExperimentsFromEdCif(self, edCif):
        modelNames = [block['name']['value'] for block in self._proxy.model.dataBlocks]
        self._interface.updateExpCif(edCif, modelNames)

    @Slot(str)
    def replaceExperiment(self, edCifNoMeas=''):
        console.debug("Calculator obj and dict need to be replaced")

        currentDataBlock = self.dataBlocksNoMeas[self.currentIndex]
        currentExperimentName = currentDataBlock['name']['value']

        calcObjBlockNames = [item.data_name for item in self._proxy.data._calcObj.items]
        calcObjBlockIdx = calcObjBlockNames.index(currentExperimentName)

        if not edCifNoMeas:
            edCifNoMeas = dataBlockToCif(currentDataBlock)

        range_min = currentDataBlock['params']['_pd_meas']['2theta_range_min']['value']
        range_max = currentDataBlock['params']['_pd_meas']['2theta_range_max']['value']
        edRangeCif = f'_pd_meas.2theta_range_min {range_min}\n_pd_meas.2theta_range_max {range_max}'
        edCifNoMeas += '\n\n' + edRangeCif

        edCifMeasOnly = dataBlockToCif(self.dataBlocksMeasOnly[self.currentIndex],
                                                    includeBlockName=False)

        edCif = edCifNoMeas + '\n\n' + edCifMeasOnly

        blocks = self._interface.replaceExpCif(edCif, currentExperimentName)
        self._dataBlocksNoMeas[self.currentIndex] = blocks

        # calcCif = cifV2ToV1(edCif)
        # calcExperimentsObj = str_to_globaln(calcCif)
        # calcExperimentsDict = calcExperimentsObj.get_dictionary()

        # calcDictBlockName = f'pd_{currentExperimentName}'

        # _, edExperimentsNoMeas = CryspyParser.calcObjAndDictToEdExperiments(calcExperimentsObj,
        #                                                                     calcExperimentsDict)

        # self._proxy.data._calcObj.items[calcObjBlockIdx] = calcExperimentsObj.items[0]
        # self._proxy.data._calcDict[calcDictBlockName] = calcExperimentsDict[calcDictBlockName]
        # self._dataBlocksNoMeas[self.currentIndex] = edExperimentsNoMeas[0]

        console.debug(f"Experiment data block '{currentExperimentName}' (no. {self.currentIndex + 1}) (without measured data) has been replaced")
        self.dataBlocksNoMeasChanged.emit()  # self.dataBlocksNoMeasChanged.emit(blockIdx)

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
        changedCalc = self.editCalcDictByMainParam(blockIdx, category, name, field, value)
        if changedIntern and changedCalc:
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
        changedCalc = self.editCalcDictByLoopParam(blockIdx, category, name, rowIndex, field, value)
        if changedIntern and changedCalc:
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
        # Update the job object
        self.blocksToJob(blockIdx, category, name, field, value)

        if type(value) == float:
            console.debug(formatMsg('sub', 'Intern dict', f'{oldValue} → {value:.6f}', f'{block}[{blockIdx}].{category}.{name}.{field}'))
        else:
            console.debug(formatMsg('sub', 'Intern dict', f'{oldValue} → {value}', f'{block}[{blockIdx}].{category}.{name}.{field}'))
        return True

    def editDataBlockLoopParam(self, blockIdx, category, name, rowIndex, field, value):
        block = 'experiment'
        oldValue = self._dataBlocksNoMeas[blockIdx]['loops'][category][rowIndex][name][field]
        if oldValue == value:
            return False
        # cheaper to do it directly than convert the phase object after its update.
        self._dataBlocksNoMeas[blockIdx]['loops'][category][rowIndex][name][field] = value
        # Update the job object
        self.blocksToLoopJob(blockIdx, category, name, rowIndex, field, value)

        if type(value) == float:
            console.debug(formatMsg('sub', 'Intern dict', f'{oldValue} → {value:.6f}', f'{block}[{blockIdx}].{category}[{rowIndex}].{name}.{field}'))
        else:
            console.debug(formatMsg('sub', 'Intern dict', f'{oldValue} → {value}', f'{block}[{blockIdx}].{category}[{rowIndex}].{name}.{field}'))
        return True

    def blocksToJob(self, blockIdx, category, name, field, value):
        """
        Update the job object with new values defined
        by the data block key names.
        """
        # find the correct parameter in the phase object
        p_name = BLOCK2JOB[name]
        p_category = BLOCK2JOB[category]
        # get category
        job_with_category = getattr(self._job, p_category)
        if field == 'value':
            setattr(job_with_category, p_name, value)
        elif field == 'error':
            getattr(job_with_category, p_name).error = value
        elif field == 'fit':
            getattr(job_with_category, p_name).fixed = not value
        pass

    def blocksToLoopJob(self, blockIdx, category, name, rowIndex, field, value):
        """
        Update the job object based on the parameters passed
        """
        p_name = BLOCK2JOB[name]
        p_category = BLOCK2JOB[category]
        # get category
        # assumption of the first loop, since there is only one background currently
        job_with_category = getattr(self._job, p_category)[0]
        # should we get the loop item?
        # this works for the background, but not for scale etc.
        try:
            job_with_category = job_with_category[rowIndex]
        except TypeError:
            pass
        if isinstance(job_with_category, list):
            job_with_category = job_with_category[rowIndex]
        # get loop item
        job_with_item = getattr(job_with_category, p_name)
        if field == 'value':
            job_with_item.value = value
        elif field == 'error':
            job_with_item.error = value
        elif field == 'fit':
            job_with_item.fixed = not value
        pass

    def editCalcDictByMainParam(self, blockIdx, category, name, field, value):
        if field != 'value' and field != 'fit':
            return True

        path, value = self.calcDictPathByMainParam(blockIdx, category, name, value)
        if field == 'fit':
            path[1] = f'flags_{path[1]}'

        oldValue = self._proxy.data._calcDict[path[0]][path[1]][path[2]]
        if oldValue == value:
            return False
        self._proxy.data._calcDict[path[0]][path[1]][path[2]] = value

        console.debug(formatMsg('sub', 'Calc dict', f'{oldValue} → {value}', f'{path}'))
        return True

    def editCalcDictByLoopParam(self, blockIdx, category, name, rowIndex, field, value):
        if field != 'value' and field != 'fit':
            return True

        path, value = self.calcDictPathByLoopParam(blockIdx, category, name, rowIndex, value)
        if field == 'fit':
            path[1] = f'flags_{path[1]}'

        oldValue = self._proxy.data._calcDict[path[0]][path[1]][path[2]]
        if oldValue == value:
            return False
        self._proxy.data._calcDict[path[0]][path[1]][path[2]] = value

        console.debug(formatMsg('sub', 'Cryspy dict', f'{oldValue} → {value}', f'{path}'))
        return True

    def calcDictPathByMainParam(self, blockIdx, category, name, value):
        blockName = self._dataBlocksNoMeas[blockIdx]['name']['value']
        path = ['','','']
        path[0] = f"pd_{blockName}"

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

        # undefined
        else:
            console.error(f"Undefined parameter name '{category}{name}'")

        return path, value

    def calcDictPathByLoopParam(self, blockIdx, category, name, rowIndex, value):
        blockName = self._dataBlocksNoMeas[blockIdx]['name']['value']
        path = ['','','']
        path[0] = f"pd_{blockName}"

        # _pd_background
        if category == '_pd_background':
            if name == 'line_segment_X':
                path[1] = 'background_ttheta'
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

        return path, value

    def paramValueByFieldAndCrypyParamPath(self, field, path):  # NEED FIX: code duplicate of editDataBlockByLmfitParams
        block, group, idx = path

        # pd (powder diffraction) block
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
            block, group, idx = Data.strToCalcDictParamPath(param.name)

            # pd (powder diffraction) block
            if block.startswith('pd_'):
                blockName = block[3:]
                category = None
                name = None
                rowIndex = -1
                value = param.value
                error = 0
                if param.stderr is not None:
                    error = param.stderr

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
                    category = '_pd_phase_block'
                    name = 'scale'
                    rowIndex = idx[0]

                value = float(value)  # convert float64 to float (needed for QML access)
                error = float(error)  # convert float64 to float (needed for QML access)
                blockIdx = [block['name']['value'] for block in self._dataBlocksNoMeas].index(blockName)

                if rowIndex == -1:
                    self.editDataBlockMainParam(blockIdx, category, name, 'value', value)
                    self.editDataBlockMainParam(blockIdx, category, name, 'error', error)
                else:
                    self.editDataBlockLoopParam(blockIdx, category, name, rowIndex, 'value', value)
                    self.editDataBlockLoopParam(blockIdx, category, name, rowIndex, 'error', error)

    def runProfileCalculations(self):

        # shove it all into the calculator.

        result = self._interface.calculate_profile()

        console.debug(formatMsg('sub', 'Profle calculations', 'finished'))

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
        ed_name = self._proxy.experiment.dataBlocksNoMeas[idx]['name']['value']
        calc_block_name = f'pd_{ed_name}'
        calcInOutDict = self._proxy.data._calcInOutDict

        # X data
        x_array = calcInOutDict[calc_block_name]['ttheta']
        x_array = np.rad2deg(x_array)
        self.setXArray(x_array, idx)

        # Measured Y data
        y_meas_array = calcInOutDict[calc_block_name]['signal_exp'][0]
        self.setYMeasArray(y_meas_array, idx)

        # Standard deviation of the measured Y data
        sy_meas_array = calcInOutDict[calc_block_name]['signal_exp'][1]
        self.setSYMeasArray(sy_meas_array, idx)

    def setCalculatedArraysForSingleExperiment(self, idx):
        ed_name = self._proxy.experiment.dataBlocksNoMeas[idx]['name']['value']
        calc_block_name = f'pd_{ed_name}'
        calcInOutDict = self._proxy.data._calcInOutDict

        # Background Y data # NED FIX: use calculatedYBkgArray()
        y_bkg_array = calcInOutDict[calc_block_name]['signal_background']
        self.setYBkgArray(y_bkg_array, idx)

        # Total calculated Y data (sum of all phases up and down polarisation plus background)
        y_calc_total_array = calcInOutDict[calc_block_name]['signal_plus'] + \
                             calcInOutDict[calc_block_name]['signal_minus'] + \
                             y_bkg_array
        self.setYCalcTotalArray(y_calc_total_array, idx)

        # Residual (Ymeas -Ycalc)
        y_meas_array = self._yMeasArrays[idx]
        y_resid_array = y_meas_array - y_calc_total_array
        self.setYResidArray(y_resid_array, idx)

        # Bragg peaks data
        #cryspyInOutDict[cryspy_name]['dict_in_out_co2sio4']['index_hkl'] # [0] - h array, [1] - k array, [2] - l array
        #cryspyInOutDict[cryspy_name]['dict_in_out_co2sio4']['ttheta_hkl'] # need rad2deg
        modelNames = [key[12:] for key in calcInOutDict[calc_block_name].keys() if 'dict_in_out' in key]
        xBraggDict = {}
        for modelName in modelNames:
            x_bragg_array = calcInOutDict[calc_block_name][f'dict_in_out_{modelName}']['ttheta_hkl']
            x_bragg_array = np.rad2deg(x_bragg_array)
            xBraggDict[modelName] = x_bragg_array
        self.setXBraggDict(xBraggDict, idx)

    def setChartRangesForSingleExperiment(self, idx):
        x_array = self._xArrays[idx]
        y_meas_array = self._yMeasArrays[idx]
        x_min = float(x_array.min())
        x_max = float(x_array.max())
        y_min = float(y_meas_array.min())
        y_max = float(y_meas_array.max())
        y_range = y_max - y_min
        y_extra = y_range * 0.1
        y_min -= y_extra
        y_max += y_extra
        ranges = {'xMin':x_min, 'xMax':x_max, 'yMin':y_min, 'yMax':y_max}
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
            console.debug(formatMsg('sub', 'X', f'experiment no. {idx + 1}', 'in intern dataset', 'replaced'))
        except IndexError:
            self._xArrays.append(xArray)
            console.debug(formatMsg('sub', 'X', f'experiment no. {len(self._xArrays)}', 'to intern dataset', 'added'))

    def setYMeasArray(self, yMeasArray, idx):
        try:
            self._yMeasArrays[idx] = yMeasArray
            console.debug(formatMsg('sub', 'Y-meas', f'experiment no. {idx + 1}', 'in intern dataset', 'replaced'))
        except IndexError:
            self._yMeasArrays.append(yMeasArray)
            console.debug(formatMsg('sub', 'Y-meas', f'experiment no. {len(self._yMeasArrays)}', 'to intern dataset', 'added'))
        self.yMeasArraysChanged.emit()

    def setSYMeasArray(self, syMeasArray, idx):
        try:
            self._syMeasArrays[idx] = syMeasArray
            console.debug(formatMsg('sub', 'sY-meas', f'experiment no. {idx + 1}', 'in intern dataset', 'replaced'))
        except IndexError:
            self._syMeasArrays.append(syMeasArray)
            console.debug(formatMsg('sub', 'sY-meas', f'experiment no. {len(self._syMeasArrays)}', 'to intern dataset', 'added'))

    def setYBkgArray(self, yBkgArray, idx):
        try:
            self._yBkgArrays[idx] = yBkgArray
            console.debug(formatMsg('sub', 'Y-bkg (inter)', f'experiment no. {idx + 1}', 'in intern dataset', 'replaced'))
        except IndexError:
            self._yBkgArrays.append(yBkgArray)
            console.debug(formatMsg('sub', 'Y-bkg (inter)', f'experiment no. {len(self._yBkgArrays)}', 'to intern dataset', 'added'))
        self.yBkgArraysChanged.emit()

    def setYCalcTotalArray(self, yCalcTotalArray, idx):
        try:
            self._yCalcTotalArrays[idx] = yCalcTotalArray
            console.debug(formatMsg('sub', 'Y-calc (total)', f'experiment no. {idx + 1}', 'in intern dataset', 'replaced'))
        except IndexError:
            self._yCalcTotalArrays.append(yCalcTotalArray)
            console.debug(formatMsg('sub', 'Y-calc (total)', f'experiment no. {len(self._yCalcTotalArrays)}', 'to intern dataset', 'added'))
        self.yCalcTotalArraysChanged.emit()

    def setYResidArray(self, yResidArray, idx):
        try:
            self._yResidArrays[idx] = yResidArray
            console.debug(formatMsg('sub', 'Y-resid (meas-calc)', f'experiment no. {idx + 1}', 'in intern dataset', 'replaced'))
        except IndexError:
            self._yResidArrays.append(yResidArray)
            console.debug(formatMsg('sub', 'Y-resid (meas-calc)', f'experiment no. {len(self._yResidArrays)}', 'to intern dataset', 'added'))
        self.yResidArraysChanged.emit()

    def setXBraggDict(self, xBraggDict, idx):
        try:
            self._xBraggDicts[idx] = xBraggDict
            console.debug(formatMsg('sub', 'X-Bragg (peaks)', f'experiment no. {idx + 1}', 'in intern dataset', 'replaced'))
        except IndexError:
            self._xBraggDicts.append(xBraggDict)
            console.debug(formatMsg('sub', 'X-Bragg (peaks)', f'experiment no. {len(self._xBraggDicts)}', 'to intern dataset', 'added'))
        self.xBraggDictsChanged.emit()

    def setChartRanges(self, ranges, idx):
        try:
            self._chartRanges[idx] = ranges
            console.debug(formatMsg('sub', 'Chart ranges', f'experiment no. {idx + 1}', 'in intern dataset', 'replaced'))
        except IndexError:
            self._chartRanges.append(ranges)
            console.debug(formatMsg('sub', 'Chart ranges', f'experiment no. {len(self._chartRanges)}', 'to intern dataset', 'added'))
        self.chartRangesChanged.emit()

    def setDataBlocksCifNoMeas(self):
        self._dataBlocksCifNoMeas = [dataBlockToCif(block) for block in self._dataBlocksNoMeas]
        console.debug(formatMsg('sub', f'{len(self._dataBlocksCifNoMeas)} experiment(s)', 'without meas data', 'to CIF string', 'converted'))
        self.dataBlocksCifNoMeasChanged.emit()

    def setDataBlocksCifMeasOnly(self):
        self._dataBlocksCifMeasOnly = [dataBlockToCif(block, includeBlockName=False) for block in self._dataBlocksMeasOnly]
        console.debug(formatMsg('sub', f'{len(self._dataBlocksCifMeasOnly)} experiment(s)', 'meas data only', 'to CIF string', 'converted'))
        self.dataBlocksCifMeasOnlyChanged.emit()

    def setDataBlocksCif(self):
        self.setDataBlocksCifNoMeas()
        self.setDataBlocksCifMeasOnly()
        cifMeasOnlyReduced =  [block.split('\n')[:10] + ['...'] + block.split('\n')[-6:] for block in self._dataBlocksCifMeasOnly]
        cifMeasOnlyReduced = ['\n'.join(block) for block in cifMeasOnlyReduced]
        cifMeasOnlyReduced = [f'\n{block}' for block in cifMeasOnlyReduced]
        cifMeasOnlyReduced = [block.rstrip() for block in cifMeasOnlyReduced]
        self._dataBlocksCif = [[noMeas, measOnlyReduced] for (noMeas, measOnlyReduced) in zip(self._dataBlocksCifNoMeas, cifMeasOnlyReduced)]
        console.debug(formatMsg('sub', f'{len(self._dataBlocksCif)} experiment(s)', 'simplified meas data', 'to CIF string', 'converted'))
        self.dataBlocksCifChanged.emit()
