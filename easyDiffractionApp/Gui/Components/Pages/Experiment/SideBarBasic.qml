// SPDX-FileCopyrightText: 2023 EasyDiffraction contributors <support@easydiffraction.org>
// SPDX-License-Identifier: BSD-3-Clause
// © 2023 Contributors to the EasyDiffraction project <https://github.com/easyscience/EasyDiffraction>

import QtQuick

import EasyApp.Gui.Elements as EaElements
import EasyApp.Gui.Components as EaComponents

import Gui.Globals as Globals


EaComponents.SideBarColumn {

    EaElements.GroupBox {
        title: Globals.Proxies.experimentGroupTitle(qsTr("Experiments"))
        icon: 'microscope'
        collapsed: false
        last: !Globals.Proxies.main.experiment.defined

        Loader { source: 'SideBarBasic/Experiments.qml' }
    }

    EaElements.GroupBox {
        title: qsTr("Diffraction radiation")
        icon: 'radiation'
        visible: Globals.Proxies.main.experiment.defined

        Loader { source: 'SideBarBasic/DiffrnRadiation.qml' }
    }

    EaElements.GroupBox {
        title: qsTr("Measured range")
        icon: 'arrows-alt-h'
        visible: Globals.Proxies.main.experiment.defined

        Loader { source: {
                if (JSON.stringify(Globals.Proxies.experimentMainParam('_diffrn_radiation', 'type')) === '{}') {
                    return ''
                }
                if (Globals.Proxies.experimentMainParam('_diffrn_radiation', 'type').value === 'cw') {
                    return 'SideBarBasic/PdMeas_CW.qml'
                } else if (Globals.Proxies.experimentMainParam('_diffrn_radiation', 'type').value === 'tof') {
                    return 'SideBarBasic/PdMeas_TOF.qml'
                } else {
                    return ''
                }
            }
        }
    }

    EaElements.GroupBox {
        title: qsTr("Diffractometer")
        icon: 'microscope'
        visible: Globals.Proxies.main.experiment.defined

        Loader { source: {
                if (JSON.stringify(Globals.Proxies.experimentMainParam('_diffrn_radiation', 'type')) === '{}') {
                    return ''
                }
                if (Globals.Proxies.experimentMainParam('_diffrn_radiation', 'type').value === 'cw') {
                    return 'SideBarBasic/PdInstrParams_CW.qml'
                } else if (Globals.Proxies.experimentMainParam('_diffrn_radiation', 'type').value === 'tof') {
                    return 'SideBarBasic/PdInstrParams_TOF.qml'
                } else {
                    return ''
                }
            }
        }
    }

    EaElements.GroupBox {
        title: qsTr("Peak profile")
        icon: 'shapes'
        visible: Globals.Proxies.main.experiment.defined

        Loader { source: {
                if (JSON.stringify(Globals.Proxies.experimentMainParam('_diffrn_radiation', 'type')) === '{}') {
                    return ''
                }
                if (Globals.Proxies.experimentMainParam('_diffrn_radiation', 'type').value === 'cw') {
                    return 'SideBarBasic/PdPeakProfile_CW.qml'
                } else if (Globals.Proxies.experimentMainParam('_diffrn_radiation', 'type').value === 'tof') {
                    return 'SideBarBasic/PdPeakProfile_TOF.qml'
                } else {
                    return ''
                }
            }
        }
    }

    EaElements.GroupBox {
        id: peakAsymmetryGroup
        title: qsTr("Peak asymmetry")
        icon: 'balance-scale-left'

        Loader { source: {
                if (JSON.stringify(Globals.Proxies.experimentMainParam('_diffrn_radiation', 'type')) === '{}') {
                    peakAsymmetryGroup.visible = false
                    return ''
                }
                if (Globals.Proxies.experimentMainParam('_diffrn_radiation', 'type').value === 'cw') {
                    peakAsymmetryGroup.visible = true
                    return 'SideBarBasic/PdInstrPeakAsymm_CW.qml'
                } else {
                    peakAsymmetryGroup.visible = false
                    return ''
                }
            }
        }
    }

    EaElements.GroupBox {
        title: Globals.Proxies.experimentLoopTitle(qsTr('Background'), '_pd_background')
        icon: 'wave-square'
        visible: Globals.Proxies.main.experiment.defined

        Loader { source: 'SideBarBasic/PdBackground.qml' }
    }

    EaElements.GroupBox {
        title: Globals.Proxies.experimentLoopTitle(qsTr('Associated phases'), '_pd_phase_block')
        icon: 'layer-group'
        visible: Globals.Proxies.main.experiment.defined

        Loader { source: 'SideBarBasic/Phase.qml' }
    }

}
