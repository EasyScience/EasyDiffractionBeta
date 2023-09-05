// SPDX-FileCopyrightText: 2023 EasyDiffraction contributors <support@easydiffraction.org>
// SPDX-License-Identifier: BSD-3-Clause
// © 2023 Contributors to the EasyDiffraction project <https://github.com/easyscience/EasyDiffraction>

import QtQuick
import QtQuick.Controls

import EasyApp.Gui.Style as EaStyle
import EasyApp.Gui.Elements as EaElements

import Gui.Globals as Globals


EaElements.GroupRow {

    EaElements.ParamTextField {
        parameter: Globals.Proxies.experimentMainParam('_pd_instr', 'resolution_u')
        onEditingFinished: Globals.Proxies.setExperimentMainParam(parameter, 'value', Number(text))
        fitCheckBox.onToggled: Globals.Proxies.setExperimentMainParam(parameter, 'fit', fitCheckBox.checked)
    }

    EaElements.ParamTextField {
        parameter: Globals.Proxies.experimentMainParam('_pd_instr', 'resolution_v')
        onEditingFinished: Globals.Proxies.setExperimentMainParam(parameter, 'value', Number(text))
        fitCheckBox.onToggled: Globals.Proxies.setExperimentMainParam(parameter, 'fit', fitCheckBox.checked)
    }

    EaElements.ParamTextField {
        parameter: Globals.Proxies.experimentMainParam('_pd_instr', 'resolution_w')
        onEditingFinished: Globals.Proxies.setExperimentMainParam(parameter, 'value', Number(text))
        fitCheckBox.onToggled: Globals.Proxies.setExperimentMainParam(parameter, 'fit', fitCheckBox.checked)
    }

    EaElements.ParamTextField {
        parameter: Globals.Proxies.experimentMainParam('_pd_instr', 'resolution_x')
        onEditingFinished: Globals.Proxies.setExperimentMainParam(parameter, 'value', Number(text))
        fitCheckBox.onToggled: Globals.Proxies.setExperimentMainParam(parameter, 'fit', fitCheckBox.checked)
    }

    EaElements.ParamTextField {
        parameter: Globals.Proxies.experimentMainParam('_pd_instr', 'resolution_y')
        onEditingFinished: Globals.Proxies.setExperimentMainParam(parameter, 'value', Number(text))
        fitCheckBox.onToggled: Globals.Proxies.setExperimentMainParam(parameter, 'fit', fitCheckBox.checked)
    }

}
