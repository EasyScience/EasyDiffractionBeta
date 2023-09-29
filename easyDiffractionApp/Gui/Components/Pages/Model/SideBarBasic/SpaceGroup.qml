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
        readOnly: true
        parameter: {
            console.error(` *** SPACE GROUP ***`);
            console.error(` *** spaceGroup ${Globals.Proxies.modelMainParam('_space_group', 'crystal_system-M_alt')}`);

            Globals.Proxies.modelMainParam('_space_group', 'crystal_system')
        }
    }

    EaElements.ParamTextField {
        readOnly: true
        parameter: Globals.Proxies.modelMainParam('_space_group', 'IT_number')
    }

    EaElements.ParamTextField {
        parameter: Globals.Proxies.modelMainParam('_space_group', 'name_H-M_alt')
        onEditingFinished: Globals.Proxies.setModelMainParamWithFullUpdate(parameter, 'value', text)
        warned: !Globals.Proxies.main.model.spaceGroupNames.includes(text)
    }

    EaElements.ParamComboBox {
        parameter: Globals.Proxies.modelMainParam('_space_group', 'IT_coordinate_system_code')
        onActivated: Globals.Proxies.setModelMainParamWithFullUpdate(parameter, 'value', currentText)
    }

}
