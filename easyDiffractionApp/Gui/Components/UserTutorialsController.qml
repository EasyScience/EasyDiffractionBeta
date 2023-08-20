// SPDX-FileCopyrightText: 2023 EasyDiffraction contributors
// SPDX-License-Identifier: BSD-3-Clause
// © © 2023 Contributors to the EasyDiffraction project <https://github.com/easyscience/EasyDiffractionApp>

import QtQuick
import QtQuick.Controls

import EasyApp.Gui.Style as EaStyle
import EasyApp.Gui.Globals as EaGlobals
import EasyApp.Gui.Elements as EaElements
import EasyApp.Gui.Components as EaComponents

import Gui.Globals as Globals


EaElements.RemoteController {
    id: rc

    visible: false

    // Tutorials

    function setupRunTutorial() {
        rc.visible = true
        rc.posToCenter()
        rc.wait(1000)
        rc.showPointer()
    }

    function completeRunTutorial() {
        rc.hidePointer()
        rc.wait(1000)
        rc.visible = false
    }

    function runAppInterfaceTutorial() {
        setupRunTutorial()

        rc.mouseClick(Globals.Refs.app.appbar.preferencesButton)

        rc.mouseClick(Globals.Refs.app.preferences.updatesTab)
        rc.mouseClick(Globals.Refs.app.preferences.appearanceTab)
        rc.mouseClick(Globals.Refs.app.preferences.experimentalTab)
        rc.mouseClick(Globals.Refs.app.preferences.developTab)
        rc.mouseClick(Globals.Refs.app.preferences.promptsTab)

        completeRunTutorial()
    }

    function runBasicUsageTutorial() {
        setupRunTutorial()

        // Home Page
        rc.mouseClick(Globals.Refs.app.homePage.startButton)

        // Project Page
        rc.mouseClick(Globals.Refs.app.projectPage.continueButton)

        // Model Page
        rc.mouseClick(Globals.Refs.app.modelPage.addNewModelManuallyButton)
        rc.mouseClick(Globals.Refs.app.projectPage.spaceGroupGroup)
        rc.mouseClick(Globals.Refs.app.projectPage.cellGroup)
        rc.mouseClick(Globals.Refs.app.projectPage.atomSiteGroup)
        rc.mouseClick(Globals.Refs.app.projectPage.atomicDisplacementGroup)
        rc.mouseClick(Globals.Refs.app.modelPage.continueButton)

        completeRunTutorial()
    }

    function runAdvancedUsageTutorial() {
        setupRunTutorial()

        // Home Page
        rc.mouseClick(Globals.Refs.app.homePage.startButton)

        // Project Page
        rc.mouseClick(Globals.Refs.app.projectPage.examplesGroup)
        rc.mouseClick(Globals.Refs.app.projectPage.examples[0])
        rc.mouseClick(Globals.Refs.app.projectPage.continueButton)

        // Model Page
        rc.wait(2000)
        rc.mouseClick(Globals.Refs.app.modelPage.continueButton)

        // Experiment page
        rc.wait(2000)
        rc.mouseClick(Globals.Refs.app.experimentPage.continueButton)

        // Analysis page
        rc.mouseClick(Globals.Refs.app.analysisPage.startFittingButton)
        rc.wait(5000)
        rc.mouseClick(Globals.Refs.app.analysisPage.fitStatusDialogOkButton)
        rc.mouseClick(Globals.Refs.app.analysisPage.continueButton)

        // Summary page
        rc.wait(2000)
        rc.mouseClick(Globals.Refs.app.appbar.resetStateButton)

        completeRunTutorial()
    }

}
