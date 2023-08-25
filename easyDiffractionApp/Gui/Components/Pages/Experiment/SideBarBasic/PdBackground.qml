// SPDX-FileCopyrightText: 2022 easyDiffraction contributors <support@easydiffraction.org>
// SPDX-License-Identifier: BSD-3-Clause
// © 2023 Contributors to the EasyDiffraction project <https://github.com/easyscience/EasyDiffractionApp>

import QtQuick
import QtQuick.Controls

import EasyApp.Gui.Style as EaStyle
import EasyApp.Gui.Elements as EaElements
import EasyApp.Gui.Components as EaComponents

import Gui.Globals as Globals


EaElements.GroupColumn {

    // Table
    EaComponents.TableView {
        id: tableView

        defaultInfoText: qsTr("No background points defined")

        // Table model
        // We only use the length of the model object defined in backend logic and
        // directly access that model in every row using the TableView index property.
        model: typeof Globals.Proxies.main.experiment.dataBlocksNoMeas[Globals.Proxies.main.experiment.currentIndex] === 'undefined' ?
            [] :
            Globals.Proxies.main.experiment.dataBlocksNoMeas[Globals.Proxies.main.experiment.currentIndex].loops._pd_background
        // Table model

        // Header row
        header: EaComponents.TableViewHeader {

            EaComponents.TableViewLabel {
                width: EaStyle.Sizes.fontPixelSize * 3.0
                //text: qsTr("no.")
            }

            EaComponents.TableViewLabel {
                width: EaStyle.Sizes.fontPixelSize * 4.0
                horizontalAlignment: Text.AlignHCenter
                color: EaStyle.Colors.themeForegroundMinor
                text: Globals.Proxies.experimentLoopParam('_pd_background', 'line_segment_X', 0).shortPrettyName ?? ''  // NEED FIX
            }

            EaComponents.TableViewLabel {
                width: EaStyle.Sizes.fontPixelSize * 5.0
                horizontalAlignment: Text.AlignHCenter
                color: EaStyle.Colors.themeForegroundMinor
                text: Globals.Proxies.experimentLoopParam('_pd_background', 'line_segment_intensity', 0).shortPrettyName ?? ''  // NEED FIX
            }

            EaComponents.TableViewLabel {
                flexibleWidth: true
                horizontalAlignment: Text.AlignLeft
                color: EaStyle.Colors.themeForegroundMinor
                text: Globals.Proxies.experimentLoopParam('_pd_background', 'X_coordinate', 0).shortPrettyName ?? ''  // NEED FIX
            }

            EaComponents.TableViewLabel {
                width: EaStyle.Sizes.tableRowHeight
            }

        }
        // Header row

        // Table rows
        delegate: EaComponents.TableViewDelegate {

            EaComponents.TableViewLabel {
                text: index + 1
                color: EaStyle.Colors.themeForegroundMinor
            }

            EaComponents.TableViewParameter {
                parameter: Globals.Proxies.experimentLoopParam('_pd_background', 'line_segment_X', index)
                onEditingFinished: Globals.Proxies.setExperimentLoopParam(parameter, 'value', Number(text))
            }

            EaComponents.TableViewParameter {
                parameter: Globals.Proxies.experimentLoopParam('_pd_background', 'line_segment_intensity', index)
                onEditingFinished: Globals.Proxies.setExperimentLoopParam(parameter, 'value', Number(text))
                fitCheckBox.onToggled: Globals.Proxies.setExperimentLoopParam(parameter, 'fit', fitCheckBox.checked)
            }

            EaComponents.TableViewParameter {
                enabled: false
                parameter: Globals.Proxies.experimentLoopParam('_pd_background', 'X_coordinate', index)
            }

            EaComponents.TableViewButton {
                enabled: tableView.model.length > 2
                fontIcon: "minus-circle"
                ToolTip.text: qsTr("Remove this point")
                onClicked: Globals.Proxies.removeExperimentLoopRow('_pd_background', index)
            }

        }
        // Table rows

    }
    // Table

    // Control buttons below table
    Row {
        spacing: EaStyle.Sizes.fontPixelSize

        EaElements.SideBarButton {
            fontIcon: "plus-circle"
            text: qsTr("Append new point")
            onClicked: {
                console.debug(`Clicking '${text}' button: ${this}`)
                console.debug('*** Appending new background point ***')
                Globals.Proxies.appendExperimentLoopRow('_pd_background')
            }
        }

        EaElements.SideBarButton {
            fontIcon: "backspace"
            text: qsTr("Reset to default points")
            onClicked: {
                console.debug(`Clicking '${text}' button: ${this}`)
                console.debug('*** Resetting background points to default ones ***')
                Globals.Proxies.main.experiment.resetBkgToDefault()
            }
        }
    }
    // Control buttons below table

}
