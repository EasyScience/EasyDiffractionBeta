# SPDX-FileCopyrightText: 2023 EasyDiffraction contributors
# SPDX-License-Identifier: BSD-3-Clause
# © © 2023 Contributors to the EasyDiffraction project <https://github.com/easyscience/EasyDiffractionApp>

import os

from EasyApp.Logic.Logging import console
from easydiffraction.io.helpers import formatMsg
from easydiffraction.io.helpers import generalizePath
from PySide6.QtCore import Property
from PySide6.QtCore import QFile
from PySide6.QtCore import QIODevice
from PySide6.QtCore import QObject
from PySide6.QtCore import QTextStream
from PySide6.QtCore import Signal
from PySide6.QtCore import Slot

try:
    import cryspy
    console.debug('CrysPy module imported')
except ImportError:
    console.error('No CrysPy module found')


class Summary(QObject):
    isCreatedChanged = Signal()
    dataBlocksCifChanged = Signal()

    def __init__(self, parent, interface=None):
        super().__init__(parent)
        self._proxy = parent
        self._interface = interface
        self._isCreated = False
        self._dataBlocksCif = ''

    @Slot()
    def resetAll(self):
        self.isCreated = False
        self._dataBlocksCif = ''
        console.debug("All summary removed")

    @Property(bool, notify=isCreatedChanged)
    def isCreated(self):
        return self._isCreated

    @isCreated.setter
    def isCreated(self, newValue):
        if self._isCreated == newValue:
            return
        self._isCreated = newValue
        self.isCreatedChanged.emit()

    @Property(str, notify=dataBlocksCifChanged)
    def dataBlocksCif(self):
        return self._dataBlocksCif

    def setDataBlocksCif(self):
        dataBlocksCifList = []
        cryspyDict = self._interface.data()._cryspyDict
        # cryspyInOutDict = self._proxy.data._calcInOutDict
        cryspyInOutDict = self._interface.data()._inOutDict
        cryspyObj = self._interface.data()._cryspyObj
        cryspyObj.take_parameters_from_dictionary(cryspyDict, l_parameter_name=None, l_sigma=None)
        cryspyObj.take_parameters_from_dictionary(cryspyInOutDict, l_parameter_name=None, l_sigma=None)

        # Models
        for blockCif in self._proxy.model._dataBlocksCif:
            dataBlocksCifList.append(blockCif[0])

        # Experiments without raw measured data, but with processed data and hkl lists
        for idx, block in enumerate(self._proxy.experiment._dataBlocksNoMeas):
            blockCifNoMeas = self._proxy.experiment._dataBlocksCifNoMeas[idx]
            dataBlocksCifList.append(blockCifNoMeas)
            for dataBlock in cryspyObj.items:
                if type(dataBlock) is cryspy.E_data_classes.cl_2_pd.Pd and dataBlock.data_name == block['name']['value']:
                    for subBlock in dataBlock.items:
                        if type(subBlock) is cryspy.C_item_loop_classes.cl_1_pd_proc.PdProcL:
                            dataBlockProcCif = subBlock.to_cif()
                            dataBlocksCifList.append(dataBlockProcCif)
                        elif type(subBlock) is cryspy.C_item_loop_classes.cl_1_pd_peak.PdPeakL:
                            dataBlockPeakCif = subBlock.to_cif()
                            dataBlocksCifList.append(dataBlockPeakCif)

        console.debug(formatMsg('sub', f'{len(dataBlocksCifList)} item(s)', '', 'to CIF string', 'converted'))
        self._dataBlocksCif = '\n\n'.join(dataBlocksCifList)
        self.dataBlocksCifChanged.emit()

    def loadReportFromResources(self, fpath):
        console.debug(f"Loading model(s) from: {fpath}")
        file = QFile(fpath)
        if not file.open(QIODevice.ReadOnly | QIODevice.Text):
            console.error('Not found in resources')
            return
        stream = QTextStream(file)
        edCif = stream.readAll()
        self._dataBlocksCif = edCif
        self.isCreated = True
        self.dataBlocksCifChanged.emit()

    def loadReportFromFile(self, fpath):
        fpath = fpath.toLocalFile()
        fpath = generalizePath(fpath)
        console.debug(f"Loading report from: {fpath}")
        if not os.path.isfile(fpath):
            console.error(f"File not found: {fpath}")
            return
        with open(fpath, 'r') as file:
            edCif = file.read()
        self._dataBlocksCif = edCif
        self.isCreated = True
        self.dataBlocksCifChanged.emit()
