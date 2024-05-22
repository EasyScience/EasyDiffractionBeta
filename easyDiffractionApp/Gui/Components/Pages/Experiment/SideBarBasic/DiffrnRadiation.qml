// SPDX-FileCopyrightText: 2023 EasyDiffraction contributors <support@easydiffraction.org>
// SPDX-License-Identifier: BSD-3-Clause
// © 2023 Contributors to the EasyDiffraction project <https://github.com/easyscience/EasyDiffraction>

import QtQuick
import QtQuick.Controls

import EasyApp.Gui.Style as EaStyle
import EasyApp.Gui.Elements as EaElements

import Gui.Globals as Globals


EaElements.GroupRow {

    EaElements.ParamComboBox {
        parameter: Globals.Proxies.experimentMainParam('_diffrn_radiation', 'probe')
        onActivated: Globals.Proxies.setExperimentMainParamWithFullUpdate(parameter, 'value', currentText)
    }

    EaElements.ParamTextField {
        readOnly: true
        parameter: {
            if (JSON.stringify(Globals.Proxies.experimentMainParam('_diffrn_radiation', 'type')) === '{}') {
                return {}
            }
            let param = Globals.Proxies.experimentMainParam('_diffrn_radiation', 'type')
            let val = param.value
            val = val.replace('cw', 'constant wavelength')
            val = val.replace('tof', 'time-of-flight')
            param.value = val
            return param
        }
    }

}
