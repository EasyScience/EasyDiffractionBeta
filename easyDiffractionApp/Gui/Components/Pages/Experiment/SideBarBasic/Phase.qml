// SPDX-FileCopyrightText: 2023 EasyDiffraction contributors <support@easydiffraction.org>
// SPDX-License-Identifier: BSD-3-Clause
// © 2023 Contributors to the EasyDiffraction project <https://github.com/easyscience/EasyDiffraction>

import QtQuick
import QtQuick.Controls

import EasyApp.Gui.Style as EaStyle
import EasyApp.Gui.Elements as EaElements
import EasyApp.Gui.Components as EaComponents

import Gui.Globals as Globals


EaElements.GroupColumn {
    property string phaseKey: {
        if (Globals.Proxies.experimentMainParam('_sample', 'type').value === 'pd') {
            return '_pd_phase_block'
        } else if (Globals.Proxies.experimentMainParam('_sample', 'type').value === 'sg') {
            return '_exptl_crystal'
        } else {
            return ''
        }
    }

    // Table
    EaComponents.TableView {
        id: tableView

        defaultInfoText: qsTr("No phases defined")

        // Table model
        // We only use the length of the model object defined in backend logic and
        // directly access that model in every row using the TableView index property.
        model: {
            if (typeof Globals.Proxies.main.experiment.dataBlocksNoMeas[
                        Globals.Proxies.main.experiment.currentIndex] === 'undefined') {
                return []
            }
            if (typeof Globals.Proxies.main.experiment.dataBlocksNoMeas[
                        Globals.Proxies.main.experiment.currentIndex].loops._pd_phase_block !== 'undefined') {
                return Globals.Proxies.main.experiment.dataBlocksNoMeas[
                    Globals.Proxies.main.experiment.currentIndex].loops._pd_phase_block
            } else if (typeof Globals.Proxies.main.experiment.dataBlocksNoMeas[
                           Globals.Proxies.main.experiment.currentIndex].loops._exptl_crystal !== 'undefined') {
                return Globals.Proxies.main.experiment.dataBlocksNoMeas[
                            Globals.Proxies.main.experiment.currentIndex].loops._exptl_crystal
            } else {
                console.error('No phase names found')
                return []
            }
        }
            //typeof Globals.Proxies.main.experiment.dataBlocksNoMeas[Globals.Proxies.main.experiment.currentIndex] === 'undefined' ?
            //[] :
            //Globals.Proxies.main.experiment.dataBlocksNoMeas[Globals.Proxies.main.experiment.currentIndex].loops._pd_phase_block
        // Table model

        // Header row
        header: EaComponents.TableViewHeader {

            EaComponents.TableViewLabel {
                width: EaStyle.Sizes.fontPixelSize * 3.0
                //text: qsTr("no.")
            }

            EaComponents.TableViewLabel {
                width: EaStyle.Sizes.tableRowHeight
                //text: qsTr("color")
            }

            EaComponents.TableViewLabel {
                width: EaStyle.Sizes.fontPixelSize * 6.0
                horizontalAlignment: Text.AlignLeft
                color: EaStyle.Colors.themeForegroundMinor
                text: Globals.Proxies.experimentLoopParam(phaseKey, 'id', 0).shortPrettyName ?? ''  // 0 = 1st element index
            }

            EaComponents.TableViewLabel {
                width: EaStyle.Sizes.fontPixelSize * 4.0
                horizontalAlignment: Text.AlignHCenter
                color: EaStyle.Colors.themeForegroundMinor
                text: Globals.Proxies.experimentLoopParam(phaseKey, 'scale', 0).shortPrettyName ?? ''  // 0 = 1st element index
            }

            EaComponents.TableViewLabel {
                flexibleWidth: true
            }

            EaComponents.TableViewLabel {
                width: EaStyle.Sizes.tableRowHeight
                //text: qsTr("del.")
            }

        }
        // Header row

        // Table rows
        delegate: EaComponents.TableViewDelegate {

            EaComponents.TableViewLabel {
                text: index + 1
                color: EaStyle.Colors.themeForegroundMinor
            }

            EaComponents.TableViewButton {
                fontIcon: "layer-group"
                ToolTip.text: qsTr("Calculated pattern color")
                backgroundColor: "transparent"
                borderColor: "transparent"
                iconColor: EaStyle.Colors.models[index]
            }

            EaComponents.TableViewParameter {
                readOnly: true
                parameter: Globals.Proxies.experimentLoopParam(phaseKey, 'id', index)
                onEditingFinished: Globals.Proxies.setExperimentLoopParamWithFullUpdate(parameter, 'value', text)
            }

            EaComponents.TableViewParameter {
                parameter: Globals.Proxies.experimentLoopParam(phaseKey, 'scale', index)
                onEditingFinished: Globals.Proxies.setExperimentLoopParam(parameter, 'value', Number(text))
                fitCheckBox.onToggled: Globals.Proxies.setExperimentLoopParam(parameter, 'fit', fitCheckBox.checked)
            }

            EaComponents.TableViewLabel {}

            EaComponents.TableViewButton {
                enabled: tableView.model.length > 1
                fontIcon: "minus-circle"
                ToolTip.text: qsTr("Remove this phase")
                onClicked: Globals.Proxies.main.model.removeModel(index)
            }

        }
        // Table rows

    }
    // Table

}
