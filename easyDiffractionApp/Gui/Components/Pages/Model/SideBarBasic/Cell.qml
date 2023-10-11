// SPDX-FileCopyrightText: 2022 easyDiffraction contributors <support@easydiffraction.org>
// SPDX-License-Identifier: BSD-3-Clause
// © 2023 Contributors to the EasyDiffraction project <https://github.com/easyscience/EasyDiffractionApp>

import QtQuick
import QtQuick.Controls

import EasyApp.Gui.Style as EaStyle
import EasyApp.Gui.Elements as EaElements

import Gui.Globals as Globals


EaElements.GroupRow {

    EaElements.ParamTextField {
        parameter: Globals.Proxies.modelMainParam('_cell', 'length_a')
        onEditingFinished: Globals.Proxies.setModelMainParamWithFullUpdate(parameter, 'value', Number(text))
        fitCheckBox.onToggled: Globals.Proxies.setModelMainParam(parameter, 'fit', fitCheckBox.checked)
    }

    EaElements.ParamTextField {
        parameter: Globals.Proxies.modelMainParam('_cell', 'length_b')
        onEditingFinished: Globals.Proxies.setModelMainParamWithFullUpdate(parameter, 'value', Number(text))
        fitCheckBox.onToggled: Globals.Proxies.setModelMainParam(parameter, 'fit', fitCheckBox.checked)
    }

    EaElements.ParamTextField {
        parameter: Globals.Proxies.modelMainParam('_cell', 'length_c')
        onEditingFinished: Globals.Proxies.setModelMainParamWithFullUpdate(parameter, 'value', Number(text))
        fitCheckBox.onToggled: Globals.Proxies.setModelMainParam(parameter, 'fit', fitCheckBox.checked)
    }

    EaElements.ParamTextField {
        parameter: Globals.Proxies.modelMainParam('_cell', 'angle_alpha')
        onEditingFinished: Globals.Proxies.setModelMainParamWithFullUpdate(parameter, 'value', Number(text))
        fitCheckBox.onToggled: Globals.Proxies.setModelMainParam(parameter, 'fit', fitCheckBox.checked)
    }

    EaElements.ParamTextField {
        parameter: Globals.Proxies.modelMainParam('_cell', 'angle_beta')
        onEditingFinished: Globals.Proxies.setModelMainParamWithFullUpdate(parameter, 'value', Number(text))
        fitCheckBox.onToggled: Globals.Proxies.setModelMainParam(parameter, 'fit', fitCheckBox.checked)
    }

    EaElements.ParamTextField {
        parameter: Globals.Proxies.modelMainParam('_cell', 'angle_gamma')
        onEditingFinished: Globals.Proxies.setModelMainParamWithFullUpdate(parameter, 'value', Number(text))
        fitCheckBox.onToggled: Globals.Proxies.setModelMainParam(parameter, 'fit', fitCheckBox.checked)
    }

}
