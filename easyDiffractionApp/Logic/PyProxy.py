# SPDX-FileCopyrightText: 2023 EasyDiffraction contributors
# SPDX-License-Identifier: BSD-3-Clause
# © © 2023 Contributors to the EasyDiffraction project <https://github.com/easyscience/EasyDiffractionApp>

from PySide6.QtCore import QObject, Property

from EasyApp.Logic.Logging import LoggerLevelHandler
from Logic.Connections import Connections
from Logic.Project import Project
from Logic.Experiment import Experiment
from Logic.Model import Model
from Logic.Data import Data
from Logic.Analysis import Analysis
from Logic.Fitting2 import Fitting
from Logic.Fittables import Fittables
from Logic.Summary import Summary
from Logic.Status import Status
from Logic.Plotting import Plotting
from Logic.Helpers import BackendHelpers
from easydiffraction.interface import InterfaceFactory
from easydiffraction import Job


class PyProxy(QObject):
    def __init__(self, parent=None):
        super().__init__(parent)
        # self.interface = InterfaceFactory()
        # instantiate the Job object.
        # This is done only once, since in the App world there is only one Job
        self._job = Job()
        self.interface = self._job.interface
        self._logger = LoggerLevelHandler(self)
        self._project = Project(self)
        self._experiment = Experiment(self, interface=self.interface)
        self._model = Model(self, interface=self.interface)
        self._data = Data(self, interface=self.interface)
        self._analysis = Analysis(self)
        self._fittables = Fittables(self)
        self._fitting = Fitting(self, interface=self.interface)
        self._summary = Summary(self, interface=self.interface)
        self._status = Status(self)
        self._plotting = Plotting(self)
        self._connections = Connections(self)
        self._backendHelpers = BackendHelpers(self)


    @Property('QVariant', constant=True)
    def logger(self):
        return self._logger

    @Property('QVariant', constant=True)
    def connections(self):
        return self._connections

    @Property('QVariant', constant=True)
    def project(self):
        return self._project

    @Property('QVariant', constant=True)
    def experiment(self):
        return self._experiment

    @Property('QVariant', constant=True)
    def model(self):
        return self._model

    @Property('QVariant', constant=True)
    def data(self):
        return self._data

    @Property('QVariant', constant=True)
    def analysis(self):
        return self._analysis

    @Property('QVariant', constant=True)
    def fitting(self):
        return self._fitting

    @Property('QVariant', constant=True)
    def fittables(self):
        return self._fittables

    @Property('QVariant', constant=True)
    def summary(self):
        return self._summary

    @Property('QVariant', constant=True)
    def status(self):
        return self._status

    @Property('QVariant', constant=True)
    def plotting(self):
        return self._plotting

    @Property('QVariant', constant=True)
    def backendHelpers(self):
        return self._backendHelpers

    @Property('QVariant', constant=True)
    def job(self):
        # make the job available for all the proxies
        return self._job