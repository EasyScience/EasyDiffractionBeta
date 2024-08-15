// SPDX-FileCopyrightText: 2023 EasyDiffraction contributors <support@easydiffraction.org>
// SPDX-License-Identifier: BSD-3-Clause
// © 2023 Contributors to the EasyDiffraction project <https://github.com/easyscience/EasyDiffraction>

import QtQuick

import EasyApp.Gui.Elements as EaElements
import EasyApp.Gui.Components as EaComponents

import Gui.Globals as Globals


EaComponents.SideBarColumn {

    EaElements.GroupBox {
        enabled: Globals.Proxies.main.project.created &&
                 !Globals.Proxies.main.project.location.includes(":/Examples")
        title: qsTr("Export summary")
        collapsible: false

        Loader { source: 'SideBarBasic/ExportReportGroup.qml' }
    }

}
