// SPDX-FileCopyrightText: 2023 EasyDiffraction contributors <support@easydiffraction.org>
// SPDX-License-Identifier: BSD-3-Clause
// © 2023 Contributors to the EasyDiffraction project <https://github.com/easyscience/EasyDiffraction>

import QtQuick
import QtQuick.Controls

import EasyApp.Gui.Style as EaStyle
import EasyApp.Gui.Elements as EaElements

import Gui.Globals as Globals

EaElements.GroupColumn {
    property real titleSpacing: 0.5

    EaElements.GroupRow {
        EaElements.ParamTextField {
            parameter: Globals.Proxies.experimentMainParam('_tof_background', 'coeff1')
            onEditingFinished: Globals.Proxies.setExperimentMainParam(parameter, 'value', Number(text))
            fitCheckBox.onToggled: Globals.Proxies.setExperimentMainParam(parameter, 'fit', fitCheckBox.checked)
        }
        EaElements.ParamTextField {
            parameter: Globals.Proxies.experimentMainParam('_tof_background', 'coeff2')
            onEditingFinished: Globals.Proxies.setExperimentMainParam(parameter, 'value', Number(text))
            fitCheckBox.onToggled: Globals.Proxies.setExperimentMainParam(parameter, 'fit', fitCheckBox.checked)
        }
        EaElements.ParamTextField {
            parameter: Globals.Proxies.experimentMainParam('_tof_background', 'coeff3')
            onEditingFinished: Globals.Proxies.setExperimentMainParam(parameter, 'value', Number(text))
            fitCheckBox.onToggled: Globals.Proxies.setExperimentMainParam(parameter, 'fit', fitCheckBox.checked)
        }
        EaElements.ParamTextField {
            parameter: Globals.Proxies.experimentMainParam('_tof_background', 'coeff4')
            onEditingFinished: Globals.Proxies.setExperimentMainParam(parameter, 'value', Number(text))
            fitCheckBox.onToggled: Globals.Proxies.setExperimentMainParam(parameter, 'fit', fitCheckBox.checked)
        }
        EaElements.ParamTextField {
            parameter: Globals.Proxies.experimentMainParam('_tof_background', 'coeff5')
            onEditingFinished: Globals.Proxies.setExperimentMainParam(parameter, 'value', Number(text))
            fitCheckBox.onToggled: Globals.Proxies.setExperimentMainParam(parameter, 'fit', fitCheckBox.checked)
        }
        EaElements.ParamTextField {
            parameter: Globals.Proxies.experimentMainParam('_tof_background', 'coeff6')
            onEditingFinished: Globals.Proxies.setExperimentMainParam(parameter, 'value', Number(text))
            fitCheckBox.onToggled: Globals.Proxies.setExperimentMainParam(parameter, 'fit', fitCheckBox.checked)
        }
    }

    EaElements.GroupRow {
        EaElements.ParamTextField {
            parameter: Globals.Proxies.experimentMainParam('_tof_background', 'coeff7')
            onEditingFinished: Globals.Proxies.setExperimentMainParam(parameter, 'value', Number(text))
            fitCheckBox.onToggled: Globals.Proxies.setExperimentMainParam(parameter, 'fit', fitCheckBox.checked)
        }
        EaElements.ParamTextField {
            parameter: Globals.Proxies.experimentMainParam('_tof_background', 'coeff8')
            onEditingFinished: Globals.Proxies.setExperimentMainParam(parameter, 'value', Number(text))
            fitCheckBox.onToggled: Globals.Proxies.setExperimentMainParam(parameter, 'fit', fitCheckBox.checked)
        }
        EaElements.ParamTextField {
            parameter: Globals.Proxies.experimentMainParam('_tof_background', 'coeff9')
            onEditingFinished: Globals.Proxies.setExperimentMainParam(parameter, 'value', Number(text))
            fitCheckBox.onToggled: Globals.Proxies.setExperimentMainParam(parameter, 'fit', fitCheckBox.checked)
        }
        EaElements.ParamTextField {
            parameter: Globals.Proxies.experimentMainParam('_tof_background', 'coeff10')
            onEditingFinished: Globals.Proxies.setExperimentMainParam(parameter, 'value', Number(text))
            fitCheckBox.onToggled: Globals.Proxies.setExperimentMainParam(parameter, 'fit', fitCheckBox.checked)
        }
        EaElements.ParamTextField {
            parameter: Globals.Proxies.experimentMainParam('_tof_background', 'coeff11')
            onEditingFinished: Globals.Proxies.setExperimentMainParam(parameter, 'value', Number(text))
            fitCheckBox.onToggled: Globals.Proxies.setExperimentMainParam(parameter, 'fit', fitCheckBox.checked)
        }
        EaElements.ParamTextField {
            parameter: Globals.Proxies.experimentMainParam('_tof_background', 'coeff12')
            onEditingFinished: Globals.Proxies.setExperimentMainParam(parameter, 'value', Number(text))
            fitCheckBox.onToggled: Globals.Proxies.setExperimentMainParam(parameter, 'fit', fitCheckBox.checked)
        }
    }

    EaElements.GroupRow {
        EaElements.ParamTextField {
            parameter: Globals.Proxies.experimentMainParam('_tof_background', 'coeff13')
            onEditingFinished: Globals.Proxies.setExperimentMainParam(parameter, 'value', Number(text))
            fitCheckBox.onToggled: Globals.Proxies.setExperimentMainParam(parameter, 'fit', fitCheckBox.checked)
        }
        EaElements.ParamTextField {
            parameter: Globals.Proxies.experimentMainParam('_tof_background', 'coeff14')
            onEditingFinished: Globals.Proxies.setExperimentMainParam(parameter, 'value', Number(text))
            fitCheckBox.onToggled: Globals.Proxies.setExperimentMainParam(parameter, 'fit', fitCheckBox.checked)
        }
        EaElements.ParamTextField {
            parameter: Globals.Proxies.experimentMainParam('_tof_background', 'coeff15')
            onEditingFinished: Globals.Proxies.setExperimentMainParam(parameter, 'value', Number(text))
            fitCheckBox.onToggled: Globals.Proxies.setExperimentMainParam(parameter, 'fit', fitCheckBox.checked)
        }
        EaElements.ParamTextField {
            parameter: Globals.Proxies.experimentMainParam('_tof_background', 'coeff16')
            onEditingFinished: Globals.Proxies.setExperimentMainParam(parameter, 'value', Number(text))
            fitCheckBox.onToggled: Globals.Proxies.setExperimentMainParam(parameter, 'fit', fitCheckBox.checked)
        }
        EaElements.ParamTextField {
            parameter: Globals.Proxies.experimentMainParam('_tof_background', 'coeff17')
            onEditingFinished: Globals.Proxies.setExperimentMainParam(parameter, 'value', Number(text))
            fitCheckBox.onToggled: Globals.Proxies.setExperimentMainParam(parameter, 'fit', fitCheckBox.checked)
        }
        EaElements.ParamTextField {
            parameter: Globals.Proxies.experimentMainParam('_tof_background', 'coeff18')
            onEditingFinished: Globals.Proxies.setExperimentMainParam(parameter, 'value', Number(text))
            fitCheckBox.onToggled: Globals.Proxies.setExperimentMainParam(parameter, 'fit', fitCheckBox.checked)
        }
    }

}

