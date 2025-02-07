// SPDX-FileCopyrightText: 2023 EasyDiffraction contributors <support@easydiffraction.org>
// SPDX-License-Identifier: BSD-3-Clause
// © 2023 Contributors to the EasyDiffraction project <https://github.com/easyscience/EasyDiffraction>

import QtQuick
import QtQuick.Controls

import EasyApp.Gui.Style as EaStyle
import EasyApp.Gui.Elements as EaElements

import Gui.Globals as Globals

EaElements.GroupRow {
    //property real titleSpacing: 0.5

    //Column {
    //    spacing: titleSpacing
    //    EaElements.Label {
    //        color: EaStyle.Colors.themeForegroundMinor
    //        text: 'Exponential decay parameters'
    //    }
    //    EaElements.GroupRow {
            EaElements.ParamTextField {
                parameter: Globals.Proxies.experimentMainParam('_pd_instr', 'alpha0')
                onEditingFinished: Globals.Proxies.setExperimentMainParam(parameter, 'value', Number(text))
                fitCheckBox.onToggled: Globals.Proxies.setExperimentMainParam(parameter, 'fit', fitCheckBox.checked)
            }
            EaElements.ParamTextField {
                parameter: Globals.Proxies.experimentMainParam('_pd_instr', 'alpha1')
                onEditingFinished: Globals.Proxies.setExperimentMainParam(parameter, 'value', Number(text))
                fitCheckBox.onToggled: Globals.Proxies.setExperimentMainParam(parameter, 'fit', fitCheckBox.checked)
            }
    //   }
    //}

    //Column {
    //    spacing: titleSpacing
    //    EaElements.Label {
    //        color: EaStyle.Colors.themeForegroundMinor
    //        text: 'Exponential decay parameters'
    //    }
    //    EaElements.GroupRow {
            EaElements.ParamTextField {
                parameter: Globals.Proxies.experimentMainParam('_pd_instr', 'beta0')
                onEditingFinished: Globals.Proxies.setExperimentMainParam(parameter, 'value', Number(text))
                fitCheckBox.onToggled: Globals.Proxies.setExperimentMainParam(parameter, 'fit', fitCheckBox.checked)
            }
            EaElements.ParamTextField {
                parameter: Globals.Proxies.experimentMainParam('_pd_instr', 'beta1')
                onEditingFinished: Globals.Proxies.setExperimentMainParam(parameter, 'value', Number(text))
                fitCheckBox.onToggled: Globals.Proxies.setExperimentMainParam(parameter, 'fit', fitCheckBox.checked)
            }
    //    }
    //}

    //Column {
    //    spacing: titleSpacing
    //    EaElements.Label {
    //        color: EaStyle.Colors.themeForegroundMinor
    //        text: 'Variance of the Gaussian component'
    //    }
    //    EaElements.GroupRow {
            EaElements.ParamTextField {
                parameter: Globals.Proxies.experimentMainParam('_pd_instr', 'sigma0')
                onEditingFinished: Globals.Proxies.setExperimentMainParam(parameter, 'value', Number(text))
                fitCheckBox.onToggled: Globals.Proxies.setExperimentMainParam(parameter, 'fit', fitCheckBox.checked)
            }
            EaElements.ParamTextField {
                parameter: Globals.Proxies.experimentMainParam('_pd_instr', 'sigma1')
                onEditingFinished: Globals.Proxies.setExperimentMainParam(parameter, 'value', Number(text))
                fitCheckBox.onToggled: Globals.Proxies.setExperimentMainParam(parameter, 'fit', fitCheckBox.checked)
            }
            EaElements.ParamTextField {
                parameter: Globals.Proxies.experimentMainParam('_pd_instr', 'sigma2')
                onEditingFinished: Globals.Proxies.setExperimentMainParam(parameter, 'value', Number(text))
                fitCheckBox.onToggled: Globals.Proxies.setExperimentMainParam(parameter, 'fit', fitCheckBox.checked)
            }
            //EaElements.ParamTextField {  // Empty spot for better visual alignment
            //    visible: false
            //}
    //    }
    //}

    //Column {
    //    spacing: titleSpacing
    //    EaElements.Label {
    //        color: EaStyle.Colors.themeForegroundMinor
    //        text: 'FWHM parameters of the Lorentzian component'
    //    }
        /*
        EaElements.GroupRow {
            EaElements.ParamTextField {
                parameter: Globals.Proxies.experimentMainParam('_pd_instr', 'gamma0')
                onEditingFinished: Globals.Proxies.setExperimentMainParam(parameter, 'value', Number(text))
                fitCheckBox.onToggled: Globals.Proxies.setExperimentMainParam(parameter, 'fit', fitCheckBox.checked)
            }
            EaElements.ParamTextField {
                parameter: Globals.Proxies.experimentMainParam('_pd_instr', 'gamma1')
                onEditingFinished: Globals.Proxies.setExperimentMainParam(parameter, 'value', Number(text))
                fitCheckBox.onToggled: Globals.Proxies.setExperimentMainParam(parameter, 'fit', fitCheckBox.checked)
            }
            EaElements.ParamTextField {
                parameter: Globals.Proxies.experimentMainParam('_pd_instr', 'gamma2')
                onEditingFinished: Globals.Proxies.setExperimentMainParam(parameter, 'value', Number(text))
                fitCheckBox.onToggled: Globals.Proxies.setExperimentMainParam(parameter, 'fit', fitCheckBox.checked)
            }
            EaElements.ParamTextField {  // Empty spot for better visual alignment
                visible: false
            }
        }
        */
    //}

}

