// SPDX-FileCopyrightText: 2023 EasyDiffraction contributors <support@easydiffraction.org>
// SPDX-License-Identifier: BSD-3-Clause
// © 2023 Contributors to the EasyDiffraction project <https://github.com/easyscience/EasyDiffraction>

import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import QtCore

import EasyApp.Gui.Style as EaStyle
import EasyApp.Gui.Globals as EaGlobals
import EasyApp.Gui.Elements as EaElements
import EasyApp.Gui.Logic as EaLogic

import Gui.Globals as Globals


Column {
    property string projectLocation: Globals.Proxies.main.project.location +
                                     EaLogic.Utils.osPathSep() +
                                     'summary'

    spacing: EaStyle.Sizes.fontPixelSize

    // Name field + format selector
    Row {
        spacing: EaStyle.Sizes.fontPixelSize

        // Name field
        EaElements.TextField {
            id: nameField
            width: saveButton.width - formatField.width - parent.spacing
            topInset: nameLabel.height
            topPadding: topInset + padding
            horizontalAlignment: TextInput.AlignLeft
            placeholderText: qsTr("Enter summary file name here")
            Component.onCompleted: text = 'summary'
            EaElements.Label {
                id: nameLabel
                text: qsTr("Name")
            }
        }

        // Format selector
        EaElements.ComboBox {
            id: formatField
            topInset: formatLabel.height
            topPadding: topInset + padding
            //bottomInset: 0
            width: EaStyle.Sizes.fontPixelSize * 10
            textRole: "text"
            valueRole: "value"
            model: [
                { value: 'html', text: qsTr("HTML") }
            ]
            EaElements.Label {
                id: formatLabel
                text: qsTr("Format")
            }
        }
    }

    // Location field
    EaElements.TextField {
        id: reportLocationField
        width: saveButton.width
        topInset: locationLabel.height
        topPadding: topInset + padding
        rightPadding: chooseButton.width
        horizontalAlignment: TextInput.AlignLeft
        placeholderText: qsTr("Enter report location here")
        Component.onCompleted: text = projectLocation
        EaElements.Label {
            id: locationLabel
            text: qsTr("Location")
        }
        EaElements.ToolButton {
            id: chooseButton
            anchors.right: parent.right
            topPadding: parent.topPadding
            showBackground: false
            fontIcon: "folder-open"
            ToolTip.text: qsTr("Choose report parent directory")
            onClicked: reportParentDirDialog.open()
        }
    }

    // Save button
    EaElements.SideBarButton {
        id: saveButton
        wide: true
        fontIcon: 'download'
        text: qsTr('Save')
        onClicked: {
            console.debug(`Clicking '${text}' button: ${this}`)
            if (formatField.currentValue === 'html' || formatField.currentValue === 'pdf') {
                Globals.Proxies.main.summary.saveAsHtml(reportLocationField.text,
                                                        nameField.text)
            } else {
                console.error(`Unsupported file format '${formatField.currentValue}'`)
            }
        }
    }

    // Save directory dialog
    FolderDialog {
        id: reportParentDirDialog
        title: qsTr("Choose report parent directory")
    }

    onProjectLocationChanged: {
        reportParentDirDialog.currentFolder = Globals.Proxies.main.backendHelpers.localFileToUrl(projectLocation)
    }

}
