# SPDX-FileCopyrightText: 2023 EasyDiffraction contributors
# SPDX-License-Identifier: BSD-3-Clause
# © © 2023 Contributors to the EasyDiffraction project <https://github.com/easyscience/EasyDiffractionApp>

import copy
import re
import random
import numpy as np
from PySide6.QtCore import QObject, Signal, Slot, Property, QThreadPool
from PySide6.QtCore import QFile, QTextStream, QIODevice
from PySide6.QtQml import QJSValue

from easyDiffractionLib import Phases, Phase, Lattice, Site, SpaceGroup
from easyCrystallography.Components.AtomicDisplacement import AtomicDisplacement
from easyDiffractionLib.io.cryspy_parser import CryspyParser
from easyDiffractionLib.io.Helpers import formatMsg, generalizePath
from EasyApp.Logic.Logging import console

from Logic.Tables import PERIODIC_TABLE # TODO CHANGE THIS TO PERIODICTABLE
import periodictable as pt
from Logic.Data import Data
from easyCrystallography.Symmetry.tools import SpacegroupInfo

try:
    import cryspy
    from cryspy.H_functions_global.function_1_cryspy_objects import \
        str_to_globaln
    console.debug('CrysPy module imported')
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

        self.phases = Phases()

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
        console.debug(formatMsg('main', f'Model defined: {newValue}'))

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

    def addDefaultPhase(self):
        default_phase = self._defaultPhase()
        r = re.compile('(.+[^0-9])\d*$')
        known_phases = [r.findall(s)[0] for s in self.phases.phase_names]  # Strip out any 1, 2, 3 etc we may have added
        if default_phase.name in known_phases:
            idx = known_phases.count(default_phase.name)
            default_phase.name = default_phase.name + str(idx)
        # print('Disabling scale')
        default_phase.scale.fixed = True
        self.phases.append(default_phase)

    # @staticmethod
    def _defaultPhase(self):
        space_group = SpaceGroup('F d -3:2')
        cell = Lattice(5.0, 3.0, 4.0, 90, 90, 90)
        adp = AtomicDisplacement("Uiso")
        atom = Site(label='O', specie='O', fract_x=0.0, fract_y=0.0, fract_z=0.0, adp=adp)#, interface=self._interface)
        phase = Phase('Test', spacegroup=space_group, cell=cell)#, interface=self._interface)
        phase.add_atom(atom)
        return phase
    
    # QML accessible methods
    @Slot(str, str, result=str)
    def atomData(self, typeSymbol, key):
        if typeSymbol == '':
            return ''
        typeSymbol = re.sub(r'[0-9]', '', typeSymbol)  # '162Dy' -> 'Dy'
        try:
            callable = getattr(pt, typeSymbol)
            r = getattr(callable, key)
            return r
        except AttributeError:
            pass
            # passing the color check to the internal database
        return PERIODIC_TABLE[typeSymbol][key]

    @Slot()
    def addDefaultModel(self):
        console.debug("Adding default model(s)")
        self.loadModelsFromEdCif(_DEFAULT_CIF_BLOCK)
        self.addDefaultPhase()

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
            fpath = generalizePath(fpath)
            console.debug(f"Loading model(s) from: {fpath}")
            phase = Phases.from_cif_file(fpath)
            self.phases.append(phase[0])
            with open(fpath, 'r') as file:
                edCif = file.read()
            self.loadModelsFromEdCif(edCif)

    # @Slot(str)
    def loadModelsFromEdCif(self, edCif):
        cryspyObj = self._proxy.data._cryspyObj
        cryspyCif = CryspyParser.edCifToCryspyCif(edCif)
        cryspyModelsObj = str_to_globaln(cryspyCif)

        modelsCountBefore = len(self.cryspyObjCrystals())
        cryspyObj.add_items(cryspyModelsObj.items)
        modelsCountAfter = len(self.cryspyObjCrystals())
        success = modelsCountAfter - modelsCountBefore

        # convert phase into dataBlocks
        dataBlocks = self.phaseToBlocks(self.phases)
        self._dataBlocks = dataBlocks
        self.defined = bool(len(self._dataBlocks))
        self._currentIndex = len(self._dataBlocks) - 1
        self.dataBlocksChanged.emit()

        # if success:
        #     cryspyModelsDict = cryspyModelsObj.get_dictionary()
        #     edModels = CryspyParser.cryspyObjAndDictToEdModels(cryspyModelsObj, cryspyModelsDict)

        #     self._proxy.data._cryspyDict.update(cryspyModelsDict)
        #     self._dataBlocks += edModels

        #     self._currentIndex = len(self.dataBlocks) - 1
        #     if not self.defined:
        #         self.defined = bool(len(self.dataBlocks))

        #     console.debug(formatMsg('sub', f'{len(edModels)} model(s)', '', 'to intern dataset', 'added'))

        #     self.dataBlocksChanged.emit()

        # else:
        #     console.debug(formatMsg('sub', 'No model(s)', '', 'to intern dataset', 'added'))

    def phaseToBlocks(self, phases):
        phase = phases[0]
        blocks = {'name': '', 'params': {}, 'loops': {}}
        blocks['name'] = phase.name
        blocks['params']['_cell'] = {}
        blocks['params']['_cell']['length_a'] = phase.cell.length_a
        blocks['params']['_cell']['length_b'] = phase.cell.length_b
        blocks['params']['_cell']['length_c'] = phase.cell.length_c
        blocks['params']['_cell']['angle_alpha'] = phase.cell.angle_alpha
        blocks['params']['_cell']['angle_beta'] = phase.cell.angle_beta
        blocks['params']['_cell']['angle_gamma'] = phase.cell.angle_gamma
        blocks['params']['_space_group'] = {}
        blocks['params']['_space_group']['name_H-M_alt'] = phase.spacegroup.space_group_HM_name
        blocks['params']['_space_group']['crystal_system'] = phase.spacegroup.crystal_system
        blocks['params']['_space_group']['IT_number'] = phase.spacegroup.int_number

        blocks['loops']['_atom_site'] = []
        for atom in phase.atoms:
            atomDict = {}
            atomDict['label'] = atom.label
            atomDict['type_symbol'] = atom.specie.symbol
            atomDict['fract_x'] = atom.fract_x
            atomDict['fract_y'] = atom.fract_y
            atomDict['fract_z'] = atom.fract_z
            atomDict['occupancy'] = atom.occupancy
            if hasattr(atom, 'adp') and isinstance(atom.adp, AtomicDisplacement) and (atom.adp.type == 'Uiso'):
                atomDict['B_iso_or_equiv'] = atom.adp.Uiso
            blocks['loops']['_atom_site'].append(atomDict)

        pass # debug breakpoint
        return [blocks]
        
    @Slot(str)
    def replaceModel(self, edCif=''):
        console.debug("Cryspy obj and dict need to be replaced")

        currentDataBlock = self.dataBlocks[self.currentIndex]
        currentModelName = currentDataBlock['name']

        cryspyObjBlockNames = [item.data_name for item in self._proxy.data._cryspyObj.items]
        cryspyObjBlockIdx = cryspyObjBlockNames.index(currentModelName)

        cryspyDictBlockName = f'crystal_{currentModelName}'

        if not edCif:
            edCif = CryspyParser.dataBlockToCif(currentDataBlock)
        cryspyCif = CryspyParser.edCifToCryspyCif(edCif)
        cryspyModelsObj = str_to_globaln(cryspyCif)
        cryspyModelsDict = cryspyModelsObj.get_dictionary()
        edModels = CryspyParser.cryspyObjAndDictToEdModels(cryspyModelsObj, cryspyModelsDict)

        self._proxy.data._cryspyObj.items[cryspyObjBlockIdx] = cryspyModelsObj.items[0]
        self._proxy.data._cryspyDict[cryspyDictBlockName] = cryspyModelsDict[cryspyDictBlockName]
        self._dataBlocks[self.currentIndex] = edModels[0]

        console.debug(f"Model data block '{currentModelName}' (no. {self.currentIndex + 1}) has been replaced")
        self.dataBlocksChanged.emit()

    @Slot(int)
    def removeModel(self, index):
        console.debug(f"Removing model no. {index + 1}")

        currentDataBlock = self.dataBlocks[index]
        currentModelName = currentDataBlock['name']

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
        print("\ncryspyObjCrystals\n")
        cryspyObj = self._proxy.data._cryspyObj
        cryspyModelType = cryspy.E_data_classes.cl_1_crystal.Crystal
        models = [block for block in cryspyObj.items if type(block) == cryspyModelType]
        return models

    def createSpaceGroupNames(self):
        all_system_names = SpacegroupInfo.get_all_systems()
        names = []
        for system in all_system_names:
            numbers = SpacegroupInfo.get_ints_from_system(system)
            names.extend([SpacegroupInfo.get_symbol_from_int_number(n) for n in numbers])
        return names

    def createIsotopesNames(self):
        elements = pt.elements
        isotopes = [element.symbol for element in elements][1:] # skip 'n'
        isotopes.extend([str(iso) + element.symbol for element in elements for iso in element.isotopes][1:]) # skip '1n'
        return isotopes

    def removeDataBlockLoopRow(self, category, rowIndex):
        block = 'model'
        blockIdx = self._currentIndex
        del self._dataBlocks[blockIdx]['loops'][category][rowIndex]

        console.debug(formatMsg('sub', 'Intern dict', 'removed', f'{block}[{blockIdx}].{category}[{rowIndex}]'))

    def appendDataBlockLoopRow(self, category):
        print("\nappendDataBlockLoopRow\n")
        block = 'model'
        blockIdx = self._currentIndex

        lastAtom = self._dataBlocks[blockIdx]['loops'][category][-1]

        newAtom = copy.deepcopy(lastAtom)
        newAtom['label'] = random.choice(self.isotopesNames)
        newAtom['type_symbol'] = newAtom['label'].raw_value
        newAtom['fract_x'] = random.uniform(0, 1)
        newAtom['fract_y'] = random.uniform(0, 1)
        newAtom['fract_z'] = random.uniform(0, 1)
        newAtom['occupancy'] = 1
        newAtom['B_iso_or_equiv'] = 0

        self._dataBlocks[blockIdx]['loops'][category].append(newAtom)
        atomsCount = len(self._dataBlocks[blockIdx]['loops'][category])

        console.debug(formatMsg('sub', 'Intern dict', 'added', f'{block}[{blockIdx}].{category}[{atomsCount}]'))

    def duplicateDataBlockLoopRow(self, category, idx):
        block = 'model'
        blockIdx = self._currentIndex

        lastAtom = self._dataBlocks[blockIdx]['loops'][category][idx]

        self._dataBlocks[blockIdx]['loops'][category].append(lastAtom)
        atomsCount = len(self._dataBlocks[blockIdx]['loops'][category])

        console.debug(formatMsg('sub', 'Intern dict', 'added', f'{block}[{blockIdx}].{category}[{atomsCount}]'))

    def editDataBlockMainParam(self, blockIdx, category, name, field, value):
        blockType = 'model'
        oldValue = self._dataBlocks[blockIdx]['params'][category][name][field]
        if oldValue == value:
            return False
        self._dataBlocks[blockIdx]['params'][category][name][field] = value
        if type(value) == float:
            console.debug(formatMsg('sub', 'Intern dict', f'{oldValue} → {value:.6f}', f'{blockType}[{blockIdx}].{category}.{name}.{field}'))
        else:
            console.debug(formatMsg('sub', 'Intern dict', f'{oldValue} → {value}', f'{blockType}[{blockIdx}].{category}.{name}.{field}'))
        return True

    def editDataBlockLoopParam(self, blockIdx, category, name, rowIndex, field, value):
        block = 'model'
        oldValue = self._dataBlocks[blockIdx]['loops'][category][rowIndex][name][field]
        if oldValue == value:
            return False
        self._dataBlocks[blockIdx]['loops'][category][rowIndex][name][field] = value
        if type(value) == float:
            console.debug(formatMsg('sub', 'Intern dict', f'{oldValue} → {value:.6f}', f'{block}[{blockIdx}].{category}[{rowIndex}].{name}.{field}'))
        else:
            console.debug(formatMsg('sub', 'Intern dict', f'{oldValue} → {value}', f'{block}[{blockIdx}].{category}[{rowIndex}].{name}.{field}'))
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

        console.debug(formatMsg('sub', 'Cryspy dict', f'{oldValue} → {value}', f'{path}'))
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

        console.debug(formatMsg('sub', 'Cryspy dict', f'{oldValue} → {value}', f'{path}'))
        return True

    def cryspyDictPathByMainParam(self, blockIdx, category, name, value):
        blockName = self._dataBlocks[blockIdx]['name']
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
        blockName = self._dataBlocks[blockIdx]['name']
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

            blockIdx = [block['name'] for block in self._dataBlocks].index(blockName)

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
                blockIdx = [block['name'] for block in self._dataBlocks].index(blockName)

                if rowIndex == -1:
                    self.editDataBlockMainParam(blockIdx, category, name, 'value', value)
                    self.editDataBlockMainParam(blockIdx, category, name, 'error', error)
                else:
                    self.editDataBlockLoopParam(blockIdx, category, name, rowIndex, 'value', value)
                    self.editDataBlockLoopParam(blockIdx, category, name, rowIndex, 'error', error)

    def setDataBlocksCif(self):
        self._dataBlocksCif = [[CryspyParser.dataBlockToCif(block)] for block in self._dataBlocks]
        console.debug(formatMsg('sub', f'{len(self._dataBlocksCif)} model(s)', '', 'to CIF string', 'converted'))
        self.dataBlocksCifChanged.emit()

    def updateCurrentModelStructView(self):
        self.setCurrentModelStructViewAtomsModel()
        #self.setCurrentModelStructViewCellModel()
        #self.setCurrentModelStructViewAxesModel()

    def setCurrentModelStructViewCellModel(self):
        params = self._dataBlocks[self._currentIndex]['params']
        a = params['_cell']['length_a'].raw_value
        b = params['_cell']['length_b'].raw_value
        c = params['_cell']['length_c'].raw_value
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
        a = params['_cell']['length_a'].raw_value
        b = params['_cell']['length_b'].raw_value
        c = params['_cell']['length_c'].raw_value
        self._structViewAxesModel = [
            {"x": 0.5, "y": 0,   "z": 0,   "rotx": 0, "roty":  0, "rotz": -90, "len": a},
            {"x": 0,   "y": 0.5, "z": 0,   "rotx": 0, "roty":  0, "rotz":   0, "len": b},
            {"x": 0,   "y": 0,   "z": 0.5, "rotx": 0, "roty": 90, "rotz":  90, "len": c}
        ]
        console.debug(f"Structure view axes  for model no. {self._currentIndex + 1} has been set. Cell lengths: ({a}, {b}, {c})")
        self.structViewAxesModelChanged.emit()

    def setCurrentModelStructViewAtomsModel(self):
        print("\nsetCurrentModelStructViewAtomsModel\n")
        structViewModel = set()
        currentModelIndex = self._proxy.model.currentIndex
        models = self.cryspyObjCrystals()
        spaceGroup = [sg for sg in models[currentModelIndex].items if type(sg) == cryspy.C_item_loop_classes.cl_2_space_group.SpaceGroup][0]
        atoms = self._dataBlocks[self._currentIndex]['loops']['_atom_site']

        
        # Add all atoms in the cell, including those in equivalent positions
        for atom in atoms:
            symbol = atom['type_symbol']
            xUnique = atom['fract_x'].raw_value
            yUnique = atom['fract_y'].raw_value
            zUnique = atom['fract_z'].raw_value
            xArray, yArray, zArray, _ = spaceGroup.calc_xyz_mult(xUnique, yUnique, zUnique)
            for x, y, z in zip(xArray, yArray, zArray):
                structViewModel.add((
                    float(x),
                    float(y),
                    float(z),
                    self.atomData(symbol, 'covalent_radius'),
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
        console.debug(formatMsg('sub', f'{len(atoms)} atom(s)', f'model no. {self._currentIndex + 1}', 'for structure view', 'defined'))
        self.structViewAtomsModelChanged.emit()

    def phaseToModel(self, phase):
        '''
        Convert the current phase to ED model representation
        '''
        pass

    def jobToModel(self, job):
        '''
        Convert the current job to ED model representation
        '''
        pass

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
        console.debug(formatMsg('main', '---------------'))
