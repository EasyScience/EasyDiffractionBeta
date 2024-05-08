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
                    return 'SideBarBasic/PdMeas2Theta.qml'
                } else if (Globals.Proxies.experimentMainParam('_diffrn_radiation', 'type').value === 'tof') {
                    return 'SideBarBasic/PdMeasTimeOfFlight.qml'
                } else {
                    return ''
                }
            }
        }
    }

    EaElements.GroupBox {
        id: instrumentResolutionGroup
        title: qsTr("Instrument resolution")
        icon: 'grip-lines-vertical'
        visible: Globals.Proxies.main.experiment.defined  // not needed, as redefined in Loader?

        Loader { source: {
                if (JSON.stringify(Globals.Proxies.experimentMainParam('_diffrn_radiation', 'type')) === '{}') {
                    instrumentResolutionGroup.visible = false
                    return ''
                }
                if (Globals.Proxies.experimentMainParam('_diffrn_radiation', 'type').value === 'cw') {
                    instrumentResolutionGroup.visible = true
                    return 'SideBarBasic/PdInstrResolution.qml'
                } else {
                    instrumentResolutionGroup.visible = false
                    return ''
                }
            }
        }
    }

    EaElements.GroupBox {
        id: peakAsymmetryGroup
        title: qsTr("Peak asymmetry")
        icon: 'balance-scale-left'
        visible: Globals.Proxies.main.experiment.defined  // not needed, as redefined in Loader?

        Loader { source: {
                if (JSON.stringify(Globals.Proxies.experimentMainParam('_diffrn_radiation', 'type')) === '{}') {
                    peakAsymmetryGroup.visible = false
                    return ''
                }
                if (Globals.Proxies.experimentMainParam('_diffrn_radiation', 'type').value === 'cw') {
                    peakAsymmetryGroup.visible = true
                    return 'SideBarBasic/PdInstrReflexAsymmetry.qml'
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
