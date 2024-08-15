// SPDX-FileCopyrightText: 2023 EasyDiffraction contributors <support@easydiffraction.org>
// SPDX-License-Identifier: BSD-3-Clause
// © 2023 Contributors to the EasyDiffraction project <https://github.com/easyscience/EasyDiffraction>

import QtQuick
import QtQuick.Controls
//import QtQuick.XmlListModel 2.15

import EasyApp.Gui.Style as EaStyle
import EasyApp.Gui.Globals as EaGlobals
import EasyApp.Gui.Elements as EaElements
import EasyApp.Gui.Components as EaComponents

import Gui.Globals as Globals
import Gui.Components as Components


EaComponents.ContentPage {
    defaultInfo: Globals.Proxies.main.summary.isCreated ?
                     "" :
                     qsTr("No Summary Generated")

    mainView: EaComponents.MainContent {
        tabs: [
            EaElements.TabButton { text: qsTr("Summary") }
        ]

        items: [
            Loader {
                source: 'MainContent/TextView.qml'  // 'MainContent/Report.qml'
                onStatusChanged: if (status === Loader.Ready) console.debug(`${source} loaded`)
            }
        ]
    }

    sideBar: EaComponents.SideBar {
        tabs: [
            EaElements.TabButton { text: qsTr("Basic controls") },
            EaElements.TabButton { text: qsTr("Advanced controls"); enabled: false },
            EaElements.TabButton { text: qsTr("Text mode") }
        ]

        items: [
            Loader { source: 'SideBarBasic.qml' },
            Loader { source: 'SideBarAdvanced.qml' },
            Loader { source: 'SideBarText.qml' }
        ]

        continueButton.visible: false
    }

    Component.onCompleted: console.debug(`Summary page loaded: ${this}`)
    Component.onDestruction: console.debug(`Summary page destroyed: ${this}`)
}
