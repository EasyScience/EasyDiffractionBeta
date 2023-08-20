// SPDX-FileCopyrightText: 2023 EasyDiffraction contributors
// SPDX-License-Identifier: BSD-3-Clause
// © © 2023 Contributors to the EasyDiffraction project <https://github.com/easyscience/EasyDiffractionApp>

import QtQuick
import QtQuick.Controls

import EasyApp.Gui.Elements as EaElements
import EasyApp.Gui.Components as EaComponents

import Gui.Globals as Globals


EaComponents.SideBarColumn {

    EaElements.GroupBox {
        title: Globals.Proxies.modelGroupTitle(qsTr("Models"))
        icon: 'layer-group'
        collapsed: false
        last: !Globals.Proxies.main.model.defined

        Loader { source: 'SideBarBasic/Models.qml' }
    }

    EaElements.GroupBox {
        title: qsTr("Space group")
        icon: 'satellite'
        visible: Globals.Proxies.main.model.defined

        Loader { source: 'SideBarBasic/SpaceGroup.qml' }

        Component.onCompleted: Globals.Refs.app.projectPage.spaceGroupGroup = this.titleArea
    }

    EaElements.GroupBox {
        title: qsTr("Cell")
        icon: 'cube'
        visible: Globals.Proxies.main.model.defined

        Loader { source: 'SideBarBasic/Cell.qml' }

        Component.onCompleted: Globals.Refs.app.projectPage.cellGroup = this.titleArea
    }

    EaElements.GroupBox {
        title: Globals.Proxies.modelLoopTitle(qsTr('Atom site'), '_atom_site')
        icon: 'atom'
        visible: Globals.Proxies.main.model.defined

        Loader { source: 'SideBarBasic/AtomSite.qml' }

        Component.onCompleted: Globals.Refs.app.projectPage.atomSiteGroup = this.titleArea
    }

    EaElements.GroupBox {
        title: Globals.Proxies.modelLoopTitle(qsTr('Atomic displacement'), '_atom_site')
        icon: 'arrows-alt'
        visible: Globals.Proxies.main.model.defined

        Loader { source: 'SideBarBasic/AtomSiteAdp.qml' }

        Component.onCompleted: Globals.Refs.app.projectPage.atomicDisplacementGroup = this.titleArea
    }

}
