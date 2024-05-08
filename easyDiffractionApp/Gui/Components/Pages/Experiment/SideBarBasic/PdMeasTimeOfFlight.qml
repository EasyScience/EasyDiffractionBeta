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
        enabled: false
        parameter: Globals.Proxies.experimentMainParam('_pd_meas', 'tof_range_min')
    }

    EaElements.ParamTextField {
        enabled: false
        parameter: Globals.Proxies.experimentMainParam('_pd_meas', 'tof_range_max')
    }

    EaElements.ParamTextField {
        enabled: false
        parameter: Globals.Proxies.experimentMainParam('_pd_meas', 'tof_range_inc')
    }

    EaElements.ParamTextField {
        parameter: Globals.Proxies.experimentMainParam('_pd_instr', 'zero')
        onEditingFinished: Globals.Proxies.setExperimentMainParam(parameter, 'value', Number(text))
        fitCheckBox.onToggled: Globals.Proxies.setExperimentMainParam(parameter, 'fit', fitCheckBox.checked)
    }

}
