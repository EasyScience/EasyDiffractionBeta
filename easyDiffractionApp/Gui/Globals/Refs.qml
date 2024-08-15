// SPDX-FileCopyrightText: 2023 EasyDiffraction contributors <support@easydiffraction.org>
// SPDX-License-Identifier: BSD-3-Clause
// © 2023 Contributors to the EasyDiffraction project <https://github.com/easyscience/EasyDiffraction>

pragma Singleton

import QtQuick


QtObject { // If "Unknown component. (M300) in QtCreator", try: "Tools > QML/JS > Reset Code Model"

    // Main
    readonly property var app: {
        'appbar': {
            'resetStateButton': null,
            'homeButton': null,
            'projectButton': null,
            'modelButton': null,
            'experimentButton': null,
            'analysisButton': null,
            'summaryButton': null,
            'preferencesButton': null
        },
        'homePage': {
            'startButton': null
        },
        'projectPage': {
            'examplesGroup': null,
            'examples': [],
            'continueButton': null
        },
        'modelPage': {
            'continueButton': null,
            'loadNewModelFromFileButton': null,
            'addNewModelManuallyButton': null,
            'plotView': null,
            'shiftParameter': null,
            'widthParameter': null,
            'scaleParameter': null,
            'spaceGroupGroup': null,
            'cellGroup': null,
            'atomSiteGroup': null,
            'atomicDisplacementGroup': null
        },
        'experimentPage': {
            'continueButton': null,
            'importDataFromLocalDriveButton': null,
            'addDefaultExperimentDataButton': null,
            'plotView': null
        },
        'analysisPage': {
            'continueButton': null,
            'startFittingButton': null,
            'plotView': null,
            'fitStatusDialogOkButton': null,
        },
        'summaryPage': {
        },
        'preferences': {
            'promptsTab': null,
            'updatesTab': null,
            'appearanceTab': null,
            'experimentalTab': null,
            'developTab': null
        }
    }

    // Misc
    property var summaryReportWebEngine
    property var remoteController

}
