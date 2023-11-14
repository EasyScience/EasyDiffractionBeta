# SPDX-FileCopyrightText: 2023 EasyDiffraction contributors
# SPDX-License-Identifier: BSD-3-Clause
# © © 2023 Contributors to the EasyDiffraction project <https://github.com/easyscience/EasyDiffractionApp>

import numpy as np
from PySide6.QtCore import QObject, Slot

from EasyApp.Logic.Logging import console
from easyDiffractionLib.calculators.cryspy import Data as  CryspyData # TODO: make non-cryspy specific

class Data(QObject):
    def __init__(self, parent):
        super().__init__(parent)
        self._data = CryspyData(parent)
        self._cryspyDict = self._data._cryspyDict
        self._cryspyObj = self._data._cryspyObj
        self._cryspyInOutDict = self._data._cryspyInOutDict

    @Slot()
    def resetAll(self):
        self._data.reset()

    def cryspyDictParamPathToStr(p):
        return CryspyData.cryspyDictParamPathToStr(p)

    def strToCryspyDictParamPath(s):
        return CryspyData.strToCryspyDictParamPath(s)
