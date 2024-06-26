# SPDX-FileCopyrightText: 2023 EasyDiffraction contributors
# SPDX-License-Identifier: BSD-3-Clause
# © 2023 Contributors to the EasyDiffraction project <https://github.com/easyscience/EasyDiffraction>

import copy
import re
import random
import numpy as np
from PySide6.QtCore import QObject, Signal, Slot, Property, QThreadPool
from PySide6.QtCore import QFile, QTextStream, QIODevice
from PySide6.QtQml import QJSValue

from EasyApp.Logic.Logging import console
from Logic.Helpers import IO
from Logic.Calculators import CryspyParser
from Logic.Tables import PERIODIC_TABLE
from Logic.Data import Data

try:
    import cryspy
    from cryspy.A_functions_base.database import DATABASE
    from cryspy.A_functions_base.function_2_space_group import \
        REFERENCE_TABLE_IT_COORDINATE_SYSTEM_CODE_NAME_HM_EXTENDED, \
        REFERENCE_TABLE_IT_NUMBER_NAME_HM_FULL, \
        ACCESIBLE_NAME_HM_SHORT
    from cryspy.procedure_rhochi.rhochi_by_dictionary import \
        rhochi_calc_chi_sq_by_dictionary
    #console.debug('CrysPy module imported')
except ImportError:
    console.error('No CrysPy module found')


_DEFAULT_CIF_BLOCK = """data_default

_space_group_name_H-M_alt "P b n m"

_cell_length_a 10
_cell_length_b 6
_cell_length_c 5
_cell_angle_alpha 90
_cell_angle_beta 90
_cell_angle_gamma 90

loop_
_atom_site_label
_atom_site_type_symbol
_atom_site_fract_x
_atom_site_fract_y
_atom_site_fract_z
_atom_site_occupancy
_atom_site_adp_type
_atom_site_B_iso_or_equiv
O O 0 0 0 1 Biso 0
"""


class Model(QObject):
    definedChanged = Signal()
    currentIndexChanged = Signal()
    dataBlocksChanged = Signal()
    dataBlocksCifChanged = Signal()

    structViewAtomsModelChanged = Signal()
    structViewCellModelChanged = Signal()
    structViewAxesModelChanged = Signal()

    def __init__(self, parent):
        super().__init__(parent)
        self._proxy = parent
        self._defined = False
        self._currentIndex = -1
        self._dataBlocks = []
        self._dataBlocksCif = []

        self._structureViewUpdater = StructureViewUpdater(self._proxy)

        self._structViewAtomsModel = []
        self._structViewCellModel = []
        self._structViewAxesModel = []

        self._spaceGroupDict = {}
        self._spaceGroupNames = self.createSpaceGroupNames()
        self._isotopesNames = self.createIsotopesNames()

    # QML accessible properties

    @Property('QVariant', constant=True)
    def spaceGroupNames(self):
        return self._spaceGroupNames

    @Property('QVariant', constant=True)
    def isotopesNames(self):
        return self._isotopesNames

    @Property(bool, notify=definedChanged)
    def defined(self):
        return self._defined
    
    @defined.setter
    def defined(self, newValue):
        if self._defined == newValue:
            return
        self._defined = newValue
        console.debug(IO.formatMsg('main', f'Model defined: {newValue}'))

        self.definedChanged.emit()

    @Property(int, notify=currentIndexChanged)
    def currentIndex(self):
        return self._currentIndex

    @currentIndex.setter
    def currentIndex(self, newValue):
        if self._currentIndex == newValue:
            return
        self._currentIndex = newValue
        console.debug(f"Current model index: {newValue}")
        self.currentIndexChanged.emit()

    @Property('QVariant', notify=dataBlocksChanged)
    def dataBlocks(self):
        return self._dataBlocks

    @Property('QVariant', notify=dataBlocksCifChanged)
    def dataBlocksCif(self):
        return self._dataBlocksCif

    @Property('QVariant', notify=structViewAtomsModelChanged)
    def structViewAtomsModel(self):
        return self._structViewAtomsModel

    @Property('QVariant', notify=structViewCellModelChanged)
    def structViewCellModel(self):
        return self._structViewCellModel

    @Property('QVariant', notify=structViewAxesModelChanged)
    def structViewAxesModel(self):
        return self._structViewAxesModel

    # QML accessible methods

    @Slot(str, str, result=str)
    def atomData(self, typeSymbol, key):
        if typeSymbol == '':
            return ''
        typeSymbol = re.sub(r'[0-9\+\-]', '', typeSymbol)  # '162Dy' -> 'Dy', 'Co2+' -> 'Co'
        return PERIODIC_TABLE[typeSymbol][key]

    @Slot()
    def addDefaultModel(self):
        console.debug("Adding default model(s)")
        self.loadModelsFromEdCif(_DEFAULT_CIF_BLOCK)

    @Slot('QVariant')
    def loadModelsFromResources(self, fpaths):
        if type(fpaths) == QJSValue:
            fpaths = fpaths.toVariant()
        for fpath in fpaths:
            console.debug(f"Loading model(s) from: {fpath}")
            file = QFile(fpath)
            if not file.open(QIODevice.ReadOnly | QIODevice.Text):
                console.error('Not found in resources')
                return
            stream = QTextStream(file)
            edCif = stream.readAll()
            self.loadModelsFromEdCif(edCif)

    @Slot('QVariant')
    def loadModelsFromFiles(self, fpaths):
        if type(fpaths) == QJSValue:
            fpaths = fpaths.toVariant()
        for fpath in fpaths:
            fpath = fpath.toLocalFile()
            fpath = IO.generalizePath(fpath)
            console.debug(f"Loading model(s) from: {fpath}")
            with open(fpath, 'r') as file:
                edCif = file.read()
            edCif = re.sub(r'data_(.*)', lambda m: m.group(0).lower(), edCif)  # Lowercase all data block names
            self.loadModelsFromEdCif(edCif)

    @Slot(str)
    def loadModelsFromEdCif(self, edCif):
        cryspyObj = self._proxy.data._cryspyObj
        cryspyCif = CryspyParser.edCifToCryspyCif(edCif)
        cryspyModelsObj = CryspyParser.cryspyCifToModelsObj(cryspyCif)

        modelsCountBefore = len(self.cryspyObjCrystals())
        cryspyObj.add_items(cryspyModelsObj.items)
        modelsCountAfter = len(self.cryspyObjCrystals())
        success = modelsCountAfter - modelsCountBefore

        if success:
            edModels = CryspyParser.cryspyObjToEdModels(cryspyModelsObj)

            cryspyModelsDict = cryspyModelsObj.get_dictionary()
            self._proxy.data._cryspyDict.update(cryspyModelsDict)
            self._dataBlocks += edModels

            self._currentIndex = len(self.dataBlocks) - 1
            if not self.defined:
                self.defined = bool(len(self.dataBlocks))

            console.debug(IO.formatMsg('sub', f'{len(edModels)} model(s)', '', 'to intern dataset', 'added'))

            self.dataBlocksChanged.emit()

        else:
            console.debug(IO.formatMsg('sub', 'No model(s)', '', 'to intern dataset', 'added'))

    @Slot(str)
    def replaceModel(self, edCif='', idx=None):
        console.debug("Cryspy obj and dict need to be replaced")

        if idx is None:
            idx = self.currentIndex

        currentDataBlock = self.dataBlocks[idx]
        currentModelName = currentDataBlock['name']['value']

        cryspyObjBlockNames = [item.data_name for item in self._proxy.data._cryspyObj.items]
        cryspyObjBlockIdx = cryspyObjBlockNames.index(currentModelName)

        cryspyDictBlockName = f'crystal_{currentModelName}'

        if not edCif:
            edCif = CryspyParser.dataBlockToCif(currentDataBlock)
        cryspyCif = CryspyParser.edCifToCryspyCif(edCif)
        cryspyModelsObj = CryspyParser.cryspyCifToModelsObj(cryspyCif)
        edModels = CryspyParser.cryspyObjToEdModels(cryspyModelsObj)

        cryspyModelsDict = cryspyModelsObj.get_dictionary()
        self._proxy.data._cryspyObj.items[cryspyObjBlockIdx] = cryspyModelsObj.items[0]
        self._proxy.data._cryspyDict[cryspyDictBlockName] = cryspyModelsDict[cryspyDictBlockName]
        self._dataBlocks[idx] = edModels[0]

        console.debug(f"Model data block '{currentModelName}' (no. {idx + 1}) has been replaced")
        self.dataBlocksChanged.emit()

    def replaceAllModels(self):
        for idx in range(len(self.dataBlocks)):
            self.replaceModel(idx=idx)

    @Slot(int)
    def removeModel(self, index):
        console.debug(f"Removing model no. {index + 1}")

        currentDataBlock = self.dataBlocks[index]
        currentModelName = currentDataBlock['name']['value']

        cryspyObjBlockNames = [item.data_name for item in self._proxy.data._cryspyObj.items]
        cryspyObjBlockIdx = cryspyObjBlockNames.index(currentModelName)

        cryspyDictBlockName = f'crystal_{currentModelName}'

        del self._proxy.data._cryspyObj.items[cryspyObjBlockIdx]
        del self._proxy.data._cryspyDict[cryspyDictBlockName]
        del self._dataBlocks[index]

        self.defined = bool(len(self.dataBlocks))

        self.dataBlocksChanged.emit()

        console.debug(f"Model no. {index + 1} has been removed")

    @Slot()
    def resetAll(self):
        self.defined = False
        self._currentIndex = -1
        self._dataBlocks = []
        self._dataBlocksCif = []
        #self.dataBlocksChanged.emit()
        console.debug("All models removed")

    @Slot(int, str, str, str, 'QVariant')
    def setMainParamWithFullUpdate(self, blockIdx, category, name, field, value):
        changedIntern = self.editDataBlockMainParam(blockIdx, category, name, field, value)
        if not changedIntern:
            return
        self.replaceModel()

    @Slot(int, str, str, str, 'QVariant')
    def setMainParam(self, blockIdx, category, name, field, value):
        changedIntern = self.editDataBlockMainParam(blockIdx, category, name, field, value)
        changedCryspy = self.editCryspyDictByMainParam(blockIdx, category, name, field, value)
        if changedIntern and changedCryspy:
            self.dataBlocksChanged.emit()

    @Slot(int, str, str, int, str, 'QVariant')
    def setLoopParamWithFullUpdate(self, blockIdx, category, name, rowIndex, field, value):
        changedIntern = self.editDataBlockLoopParam(blockIdx, category, name, rowIndex, field, value)
        if not changedIntern:
            return
        self.replaceModel()

    @Slot(int, str, str, int, str, 'QVariant')
    def setLoopParam(self, blockIdx, category, name, rowIndex, field, value):
        changedIntern = self.editDataBlockLoopParam(blockIdx, category, name, rowIndex, field, value)
        changedCryspy = self.editCryspyDictByLoopParam(blockIdx, category, name, rowIndex, field, value)
        if changedIntern and changedCryspy:
            self.dataBlocksChanged.emit()

    @Slot(str, int)
    def removeLoopRow(self, category, rowIndex):
        self.removeDataBlockLoopRow(category, rowIndex)
        self.replaceModel()

    @Slot(str)
    def appendLoopRow(self, category):
        self.appendDataBlockLoopRow(category)
        self.replaceModel()

    @Slot(str, int)
    def duplicateLoopRow(self, category, idx):
        self.duplicateDataBlockLoopRow(category, idx)
        self.replaceModel()

    # Private methods

    def cryspyObjCrystals(self):
        cryspyObj = self._proxy.data._cryspyObj
        cryspyModelType = cryspy.E_data_classes.cl_1_crystal.Crystal
        models = [block for block in cryspyObj.items if type(block) == cryspyModelType]
        return models

    def createSpaceGroupNames(self):
        namesShort = ACCESIBLE_NAME_HM_SHORT
        namesFull = tuple((name[1] for name in REFERENCE_TABLE_IT_NUMBER_NAME_HM_FULL))
        namesExtended = tuple((name[2] for name in REFERENCE_TABLE_IT_COORDINATE_SYSTEM_CODE_NAME_HM_EXTENDED))
        return list(set(namesShort + namesFull + namesExtended))

    def createIsotopesNames(self):
        return [isotope[1] for isotope in list(DATABASE['Isotopes'].keys())]

    def removeDataBlockLoopRow(self, category, rowIndex):
        block = 'model'
        blockIdx = self._currentIndex
        del self._dataBlocks[blockIdx]['loops'][category][rowIndex]

        console.debug(IO.formatMsg('sub', 'Intern dict', 'removed', f'{block}[{blockIdx}].{category}[{rowIndex}]'))

    def appendDataBlockLoopRow(self, category):
        block = 'model'
        blockIdx = self._currentIndex

        lastAtom = self._dataBlocks[blockIdx]['loops'][category][-1]

        newAtom = copy.deepcopy(lastAtom)
        newAtom['label']['value'] = random.choice(self.isotopesNames)
        newAtom['type_symbol']['value'] = newAtom['label']['value']
        newAtom['fract_x']['value'] = random.uniform(0, 1)
        newAtom['fract_y']['value'] = random.uniform(0, 1)
        newAtom['fract_z']['value'] = random.uniform(0, 1)
        newAtom['occupancy']['value'] = 1
        newAtom['B_iso_or_equiv']['value'] = 0

        self._dataBlocks[blockIdx]['loops'][category].append(newAtom)
        atomsCount = len(self._dataBlocks[blockIdx]['loops'][category])

        console.debug(IO.formatMsg('sub', 'Intern dict', 'added', f'{block}[{blockIdx}].{category}[{atomsCount}]'))

    def duplicateDataBlockLoopRow(self, category, idx):
        block = 'model'
        blockIdx = self._currentIndex

        lastAtom = self._dataBlocks[blockIdx]['loops'][category][idx]

        self._dataBlocks[blockIdx]['loops'][category].append(lastAtom)
        atomsCount = len(self._dataBlocks[blockIdx]['loops'][category])

        console.debug(IO.formatMsg('sub', 'Intern dict', 'added', f'{block}[{blockIdx}].{category}[{atomsCount}]'))

    def editDataBlockMainParam(self, blockIdx, category, name, field, value):
        blockType = 'model'
        oldValue = self._dataBlocks[blockIdx]['params'][category][name][field]
        if oldValue == value:
            return False
        self._dataBlocks[blockIdx]['params'][category][name][field] = value
        if type(value) == float:
            console.debug(IO.formatMsg('sub', 'Intern dict', f'{oldValue} → {value:.6f}', f'{blockType}[{blockIdx}].{category}.{name}.{field}'))
        else:
            console.debug(IO.formatMsg('sub', 'Intern dict', f'{oldValue} → {value}', f'{blockType}[{blockIdx}].{category}.{name}.{field}'))
        return True

    def editDataBlockLoopParam(self, blockIdx, category, name, rowIndex, field, value):
        block = 'model'
        oldValue = self._dataBlocks[blockIdx]['loops'][category][rowIndex][name][field]
        if oldValue == value:
            return False
        self._dataBlocks[blockIdx]['loops'][category][rowIndex][name][field] = value
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
        if field == 'fit':
            path[1] = f'flags_{path[1]}'

        oldValue = self._proxy.data._cryspyDict[path[0]][path[1]][path[2]]
        if oldValue == value:
            return False
        self._proxy.data._cryspyDict[path[0]][path[1]][path[2]] = value

        console.debug(IO.formatMsg('sub', 'Cryspy dict', f'{oldValue} → {value}', f'{path}'))
        return True

    def cryspyDictPathByMainParam(self, blockIdx, category, name, value):
        blockName = self._dataBlocks[blockIdx]['name']['value']
        path = ['','','']
        path[0] = f"crystal_{blockName}"

        # _cell
        if category == '_cell':
            if name == 'length_a':
                path[1] = 'unit_cell_parameters'
                path[2] = 0
            elif name == 'length_b':
                path[1] = 'unit_cell_parameters'
                path[2] = 1
            elif name == 'length_c':
                path[1] = 'unit_cell_parameters'
                path[2] = 2
            elif name == 'angle_alpha':
                path[1] = 'unit_cell_parameters'
                path[2] = 3
                value = np.deg2rad(value)
            elif name == 'angle_beta':
                path[1] = 'unit_cell_parameters'
                path[2] = 4
                value = np.deg2rad(value)
            elif name == 'angle_gamma':
                path[1] = 'unit_cell_parameters'
                path[2] = 5
                value = np.deg2rad(value)

        # undefined
        else:
            console.error(f"Undefined name '{category}.{name}'")

        return path, value

    def cryspyDictPathByLoopParam(self, blockIdx, category, name, rowIndex, value):
        blockName = self._dataBlocks[blockIdx]['name']['value']
        path = ['','','']
        path[0] = f"crystal_{blockName}"

        # _atom_site
        if category == '_atom_site':
            if name == 'fract_x':
                path[1] = 'atom_fract_xyz'
                path[2] = (0, rowIndex)
            elif name == 'fract_y':
                path[1] = 'atom_fract_xyz'
                path[2] = (1, rowIndex)
            elif name == 'fract_z':
                path[1] = 'atom_fract_xyz'
                path[2] = (2, rowIndex)
            elif name == 'occupancy':
                path[1] = 'atom_occupancy'
                path[2] = rowIndex
            elif name == 'B_iso_or_equiv':
                path[1] = 'atom_b_iso'
                path[2] = rowIndex

        # undefined
        else:
            console.error(f"Undefined name '{category}.{name}'")

        return path, value

    def paramValueByFieldAndCrypyParamPath(self, field, path):  # NEED FIX: code duplicate of editDataBlockByLmfitParams
        block, group, idx = path

        # crystal block
        if block.startswith('crystal_'):
            blockName = block[8:]
            category = None
            name = None
            rowIndex = -1

            # unit_cell_parameters
            if group == 'unit_cell_parameters':
                category = '_cell'
                if idx[0] == 0:
                    name = 'length_a'
                elif idx[0] == 1:
                    name = 'length_b'
                elif idx[0] == 2:
                    name = 'length_c'
                elif idx[0] == 3:
                    name = 'angle_alpha'
                elif idx[0] == 4:
                    name = 'angle_beta'
                elif idx[0] == 5:
                    name = 'angle_gamma'

            # atom_fract_xyz
            elif group == 'atom_fract_xyz':
                category = '_atom_site'
                rowIndex = idx[1]
                if idx[0] == 0:
                    name = 'fract_x'
                elif idx[0] == 1:
                    name = 'fract_y'
                elif idx[0] == 2:
                    name = 'fract_z'

            # atom_occupancy
            elif group == 'atom_occupancy':
                category = '_atom_site'
                rowIndex = idx[0]
                name = 'occupancy'

            # b_iso_or_equiv
            elif group == 'atom_b_iso':
                category = '_atom_site'
                rowIndex = idx[0]
                name = 'B_iso_or_equiv'

            blockIdx = [block['name']['value'] for block in self._dataBlocks].index(blockName)

            if rowIndex == -1:
                return self.dataBlocks[blockIdx]['params'][category][name][field]
            else:
                return self.dataBlocks[blockIdx]['loops'][category][rowIndex][name][field]

        return None

    def editDataBlockByLmfitParams(self, params):
        for param in params.values():
            block, group, idx = Data.strToCryspyDictParamPath(param.name)

            # crystal block
            if block.startswith('crystal_'):
                blockName = block[8:]
                category = None
                name = None
                rowIndex = -1
                value = param.value
                error = 0
                if param.stderr is not None:
                    if param.stderr < 1e-6:
                        error = 1e-6  # Temporary solution to compensate for too small uncertanties after lmfit
                    else:
                        error = param.stderr

                # unit_cell_parameters
                if group == 'unit_cell_parameters':
                    category = '_cell'
                    if idx[0] == 0:
                        name = 'length_a'
                    elif idx[0] == 1:
                        name = 'length_b'
                    elif idx[0] == 2:
                        name = 'length_c'
                    elif idx[0] == 3:
                        name = 'angle_alpha'
                        value = np.rad2deg(value)
                    elif idx[0] == 4:
                        name = 'angle_beta'
                        value = np.rad2deg(value)
                    elif idx[0] == 5:
                        name = 'angle_gamma'
                        value = np.rad2deg(value)

                # atom_fract_xyz
                elif group == 'atom_fract_xyz':
                    category = '_atom_site'
                    rowIndex = idx[1]
                    if idx[0] == 0:
                        name = 'fract_x'
                    elif idx[0] == 1:
                        name = 'fract_y'
                    elif idx[0] == 2:
                        name = 'fract_z'

                # atom_occupancy
                elif group == 'atom_occupancy':
                    category = '_atom_site'
                    rowIndex = idx[0]
                    name = 'occupancy'

                # b_iso_or_equiv
                elif group == 'atom_b_iso':
                    category = '_atom_site'
                    rowIndex = idx[0]
                    name = 'B_iso_or_equiv'

                value = float(value)  # convert float64 to float (needed for QML access)
                error = float(error)  # convert float64 to float (needed for QML access)
                blockIdx = [block['name']['value'] for block in self._dataBlocks].index(blockName)

                if rowIndex == -1:
                    self.editDataBlockMainParam(blockIdx, category, name, 'value', value)
                    self.editDataBlockMainParam(blockIdx, category, name, 'error', error)
                else:
                    self.editDataBlockLoopParam(blockIdx, category, name, rowIndex, 'value', value)
                    self.editDataBlockLoopParam(blockIdx, category, name, rowIndex, 'error', error)

    def setDataBlocksCif(self):
        self._dataBlocksCif = [[CryspyParser.dataBlockToCif(block)] for block in self._dataBlocks]
        console.debug(IO.formatMsg('sub', f'{len(self._dataBlocksCif)} model(s)', '', 'to CIF string', 'converted'))
        self.dataBlocksCifChanged.emit()

    def updateCurrentModelStructView(self):
        self.setCurrentModelStructViewAtomsModel()
        #self.setCurrentModelStructViewCellModel()
        #self.setCurrentModelStructViewAxesModel()

    def setCurrentModelStructViewCellModel(self):
        params = self._dataBlocks[self._currentIndex]['params']
        a = params['_cell']['length_a']['value']
        b = params['_cell']['length_b']['value']
        c = params['_cell']['length_c']['value']
        self._structViewCellModel = [
            # x
            { "x": 0,     "y":-0.5*b, "z":-0.5*c, "rotx": 0, "roty": 0,  "rotz":-90, "len": a },
            { "x": 0,     "y": 0.5*b, "z":-0.5*c, "rotx": 0, "roty": 0,  "rotz":-90, "len": a },
            { "x": 0,     "y":-0.5*b, "z": 0.5*c, "rotx": 0, "roty": 0,  "rotz":-90, "len": a },
            { "x": 0,     "y": 0.5*b, "z": 0.5*c, "rotx": 0, "roty": 0,  "rotz":-90, "len": a },
            # y
            { "x":-0.5*a, "y": 0,     "z":-0.5*c, "rotx": 0, "roty": 0,  "rotz": 0,  "len": b },
            { "x": 0.5*a, "y": 0,     "z":-0.5*c, "rotx": 0, "roty": 0,  "rotz": 0,  "len": b },
            { "x":-0.5*a, "y": 0,     "z": 0.5*c, "rotx": 0, "roty": 0,  "rotz": 0,  "len": b },
            { "x": 0.5*a, "y": 0,     "z": 0.5*c, "rotx": 0, "roty": 0,  "rotz": 0,  "len": b },
            # z
            { "x":-0.5*a, "y":-0.5*b, "z": 0,     "rotx": 0, "roty": 90, "rotz": 90, "len": c },
            { "x": 0.5*a, "y":-0.5*b, "z": 0,     "rotx": 0, "roty": 90, "rotz": 90, "len": c },
            { "x":-0.5*a, "y": 0.5*b, "z": 0,     "rotx": 0, "roty": 90, "rotz": 90, "len": c },
            { "x": 0.5*a, "y": 0.5*b, "z": 0,     "rotx": 0, "roty": 90, "rotz": 90, "len": c },
        ]
        console.debug(f"Structure view cell  for model no. {self._currentIndex + 1} has been set. Cell lengths: ({a}, {b}, {c})")
        self.structViewCellModelChanged.emit()

    def setCurrentModelStructViewAxesModel(self):
        params = self._dataBlocks[self._currentIndex]['params']
        a = params['_cell']['length_a']['value']
        b = params['_cell']['length_b']['value']
        c = params['_cell']['length_c']['value']
        self._structViewAxesModel = [
            {"x": 0.5, "y": 0,   "z": 0,   "rotx": 0, "roty":  0, "rotz": -90, "len": a},
            {"x": 0,   "y": 0.5, "z": 0,   "rotx": 0, "roty":  0, "rotz":   0, "len": b},
            {"x": 0,   "y": 0,   "z": 0.5, "rotx": 0, "roty": 90, "rotz":  90, "len": c}
        ]
        console.debug(f"Structure view axes  for model no. {self._currentIndex + 1} has been set. Cell lengths: ({a}, {b}, {c})")
        self.structViewAxesModelChanged.emit()

    def setCurrentModelStructViewAtomsModel(self):
        structViewModel = set()
        currentModelIndex = self._proxy.model.currentIndex
        models = self.cryspyObjCrystals()
        spaceGroup = [sg for sg in models[currentModelIndex].items if type(sg) == cryspy.C_item_loop_classes.cl_2_space_group.SpaceGroup][0]
        atoms = self._dataBlocks[self._currentIndex]['loops']['_atom_site']
        # Add all atoms in the cell, including those in equivalent positions
        for atom in atoms:
            symbol = atom['type_symbol']['value']
            xUnique = atom['fract_x']['value']
            yUnique = atom['fract_y']['value']
            zUnique = atom['fract_z']['value']
            xArray, yArray, zArray, _ = spaceGroup.calc_xyz_mult(xUnique, yUnique, zUnique)
            for x, y, z in zip(xArray, yArray, zArray):
                structViewModel.add((
                    float(x),
                    float(y),
                    float(z),
                    self.atomData(symbol, 'covalentRadius'),
                    self.atomData(symbol, 'color')
                ))
        # Add those atoms, which have 0 in xyz to be translated into 1
        structViewModelCopy = copy.copy(structViewModel)
        for item in structViewModelCopy:
            if item[0] == 0 and item[1] == 0 and item[2] == 0:
                structViewModel.add((1, 0, 0, item[3], item[4]))
                structViewModel.add((0, 1, 0, item[3], item[4]))
                structViewModel.add((0, 0, 1, item[3], item[4]))
                structViewModel.add((1, 1, 0, item[3], item[4]))
                structViewModel.add((1, 0, 1, item[3], item[4]))
                structViewModel.add((0, 1, 1, item[3], item[4]))
                structViewModel.add((1, 1, 1, item[3], item[4]))
            elif item[0] == 0 and item[1] == 0:
                structViewModel.add((1, 0, item[2], item[3], item[4]))
                structViewModel.add((0, 1, item[2], item[3], item[4]))
                structViewModel.add((1, 1, item[2], item[3], item[4]))
            elif item[0] == 0 and item[2] == 0:
                structViewModel.add((1, item[1], 0, item[3], item[4]))
                structViewModel.add((0, item[1], 1, item[3], item[4]))
                structViewModel.add((1, item[1], 1, item[3], item[4]))
            elif item[1] == 0 and item[2] == 0:
                structViewModel.add((item[0], 1, 0, item[3], item[4]))
                structViewModel.add((item[0], 0, 1, item[3], item[4]))
                structViewModel.add((item[0], 1, 1, item[3], item[4]))
            elif item[0] == 0:
                structViewModel.add((1, item[1], item[2], item[3], item[4]))
            elif item[1] == 0:
                structViewModel.add((item[0], 1, item[2], item[3], item[4]))
            elif item[2] == 0:
                structViewModel.add((item[0], item[1], 1, item[3], item[4]))
        # Create dict from set for GUI
        self._structViewAtomsModel = [{'x':x, 'y':y, 'z':z, 'diameter':diameter, 'color':color}
                                      for x, y, z, diameter, color in structViewModel]
        console.debug(IO.formatMsg('sub', f'{len(atoms)} atom(s)', f'model no. {self._currentIndex + 1}', 'for structure view', 'defined'))
        self.structViewAtomsModelChanged.emit()


class StructureViewWorker(QObject):
    finished = Signal()

    def __init__(self, proxy):
        super().__init__()
        self._proxy = proxy

    def run(self):
        self._proxy.model.updateCurrentModelStructView()
        self.finished.emit()


class StructureViewUpdater(QObject):
    finished = Signal()

    def __init__(self, parent):
        super().__init__(parent)
        self._proxy = parent
        self._threadpool = QThreadPool.globalInstance()
        self._worker = StructureViewWorker(self._proxy)

        self._worker.finished.connect(self.finished)

    def update(self):
        self._threadpool.start(self._worker.run)
        console.debug(IO.formatMsg('main', '---------------'))
