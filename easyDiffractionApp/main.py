# SPDX-FileCopyrightText: 2023 EasyDiffraction contributors
# SPDX-License-Identifier: BSD-3-Clause
# © 2023 Contributors to the EasyDiffraction project <https://github.com/easyscience/EasyDiffraction>

import sys


if __name__ == '__main__':

    from Logic.Helpers import EasyAppLoader
    EasyAppLoader.terminateIfNotFound()
    from EasyApp.Logic.Logging import console
    console.debug('Resource paths exposed to QML')

    from PySide6.QtCore import qInstallMessageHandler
    qInstallMessageHandler(console.qmlMessageHandler)
    console.debug('Custom Qt message handler defined')

    from Logic.Helpers import EnvironmentVariables
    EnvironmentVariables.set()
    console.debug('Environment variables defined')

    #from Logic.Helpers import WebEngine
    #WebEngine.initialize()
    #console.debug('QtWebEngine for the QML GUI components initialized')

    from Logic.Helpers import Application
    app = Application(sys.argv)
    console.debug(f'Qt Application created {app}')

    from PySide6.QtQml import QQmlApplicationEngine
    engine = QQmlApplicationEngine()
    console.debug(f'QML application engine created {engine}')

    from Logic.Helpers import ResourcePaths
    resourcePaths = ResourcePaths()
    for p in resourcePaths.imports:
        engine.addImportPath(p)
    console.debug('Resource paths exposed to QML')

    from PySide6.QtQml import qmlRegisterType
    from EasyApp.Logic.Maintenance import Updater
    qmlRegisterType(Updater, 'EasyApp.Logic.Maintenance', 1, 0, 'Updater')
    console.debug('Updater type registered instantiation in QML')

    from Logic.Helpers import TranslationsHandler
    translationsHandler = TranslationsHandler(engine)
    engine.rootContext().setContextProperty('pyTranslator', translationsHandler.translator)
    console.debug('Translator object exposed to QML')

    from Logic.Helpers import ColorSchemeHandler
    colorSchemeHandler = ColorSchemeHandler()
    engine.rootContext().setContextProperty('pySystemColorScheme', colorSchemeHandler.systemColorScheme)
    console.debug('System color scheme object exposed to QML')

    from Logic.Helpers import PersistentSettingsHandler
    settingsHandler = PersistentSettingsHandler()
    engine.rootContext().setContextProperty('pySettingsPath', settingsHandler.path)
    console.debug('Persistent settings file path exposed to QML')

    from Logic.Helpers import CommandLineArguments
    cliArgs = CommandLineArguments()
    engine.rootContext().setContextProperty('pyIsTestMode', cliArgs.testmode)
    console.debug('pyIsTestMode object exposed to QML')

    engine.load(resourcePaths.splashScreenQml)
    console.debug(f'Splash screen QML component loaded: {resourcePaths.splashScreenQml}')

    if not engine.rootObjects():
        sys.exit(-1)
    console.debug('QML engine has root component')

    from Logic.Helpers import PyProxyWorker
    from PySide6.QtCore import QThreadPool
    worker = PyProxyWorker()
    worker.createdAndMovedToMainThread.connect(lambda: (
            engine.rootContext().setContextProperty('pyProxy', worker.proxy),
            console.debug(f'PyProxy object id:{id(worker.proxy)} exposed to QML'),
            engine.load(resourcePaths.mainQml),
            console.debug(f'Main QML component loaded: {resourcePaths.mainQml}')
        ))
    threadpool = QThreadPool.globalInstance()
    console.debug('PyProxy object is creating and exposing to QML')
    threadpool.start(worker.createAndMoveToMainThread)

    console.debug('Application event loop is about to start')
    exitCode = app.exec()

    console.debug(f'Application is about to exit with code {exitCode}')
    sys.exit(exitCode)
