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
        id: measuredRangeGroup
        title: qsTr("Measured range")
        icon: 'arrows-alt-h'
        //visible: Globals.Proxies.main.experiment.defined
        visible: false

        Loader { source: {
                if (JSON.stringify(Globals.Proxies.experimentMainParam('_diffrn_radiation', 'type')) === '{}') {
                    measuredRangeGroup.visible = false
                    return ''
                }
                if (Globals.Proxies.experimentMainParam('_sample', 'type').value === 'pd') {
                    measuredRangeGroup.visible = true
                    if (Globals.Proxies.experimentMainParam('_diffrn_radiation', 'type').value === 'cwl') {
                        return 'SideBarBasic/PdMeas_PD-CWL.qml'
                    } else if (Globals.Proxies.experimentMainParam('_diffrn_radiation', 'type').value === 'tof') {
                        return 'SideBarBasic/PdMeas_PD-TOF.qml'
                    }
                } else {
                    measuredRangeGroup.visible = false
                    return ''
                }
            }
        }
    }

    EaElements.GroupBox {
        id: diffrnRadiationGroup
        title: qsTr("Diffractometer")
        icon: 'microscope'
        //visible: Globals.Proxies.main.experiment.defined
        visible: false

        Loader { source: {
                if (JSON.stringify(Globals.Proxies.experimentMainParam('_diffrn_radiation', 'type')) === '{}') {
                    diffrnRadiationGroup.visible = false
                    return ''
                }
                if (Globals.Proxies.experimentMainParam('_sample', 'type').value === 'pd') {
                    if (Globals.Proxies.experimentMainParam('_diffrn_radiation', 'type').value === 'cwl') {
                        diffrnRadiationGroup.visible = true
                        return 'SideBarBasic/PdInstrParams_PD-CWL.qml'
                    } else if (Globals.Proxies.experimentMainParam('_diffrn_radiation', 'type').value === 'tof') {
                        diffrnRadiationGroup.visible = true
                        return 'SideBarBasic/PdInstrParams_PD-TOF.qml'
                    } else {
                        diffrnRadiationGroup.visible = false
                        return ''
                    }
                } else if (Globals.Proxies.experimentMainParam('_sample', 'type').value === 'sg') {
                    if (Globals.Proxies.experimentMainParam('_diffrn_radiation', 'type').value === 'cwl') {
                        diffrnRadiationGroup.visible = true
                        return 'SideBarBasic/PdInstrParams_SG.qml'
                    } else {
                        diffrnRadiationGroup.visible = false
                        return ''
                    }
                }
            }
        }
    }

    EaElements.GroupBox {
        id: extinctionGroup
        title: qsTr("Extinction")
        icon: 'arrow-down'
        //visible: Globals.Proxies.main.experiment.defined
        visible: false

        Loader { source: {
                if (JSON.stringify(Globals.Proxies.experimentMainParam('_sample', 'type')) === '{}') {
                    extinctionGroup.visible = false
                    return ''
                }
                if (Globals.Proxies.experimentMainParam('_sample', 'type').value === 'pd') {
                    extinctionGroup.visible = false
                    return ''
                } else if (Globals.Proxies.experimentMainParam('_sample', 'type').value === 'sg') {
                    extinctionGroup.visible = true
                    return 'SideBarBasic/Extinction_SG.qml'
                } else {
                    extinctionGroup.visible = false
                    return ''
                }
            }
        }
    }

    EaElements.GroupBox {
        id: peakProfileGroup
        title: qsTr("Profile shape")
        icon: 'shapes'
        //visible: Globals.Proxies.main.experiment.defined
        visible: false

        Loader { source: {
                if (JSON.stringify(Globals.Proxies.experimentMainParam('_diffrn_radiation', 'type')) === '{}') {
                    peakProfileGroup.visible = false
                    return ''
                }
                if (Globals.Proxies.experimentMainParam('_sample', 'type').value === 'pd') {
                    peakProfileGroup.visible = true
                    if (Globals.Proxies.experimentMainParam('_diffrn_radiation', 'type').value === 'cwl') {
                        return 'SideBarBasic/PdPeakProfile_PD-CWL.qml'
                    } else if (Globals.Proxies.experimentMainParam('_diffrn_radiation', 'type').value === 'tof') {
                        return 'SideBarBasic/PdPeakProfile_PD-TOF.qml'
                    }
                } else {
                    peakProfileGroup.visible = false
                    return ''
                }
            }
        }
    }

    EaElements.GroupBox {
        id: peakAsymmetryGroup
        title: qsTr("Peak asymmetry")
        icon: 'balance-scale-left'
        visible: false

        Loader { source: {
                if (JSON.stringify(Globals.Proxies.experimentMainParam('_diffrn_radiation', 'type')) === '{}') {
                    peakAsymmetryGroup.visible = false
                    return ''
                }
                if (Globals.Proxies.experimentMainParam('_diffrn_radiation', 'type').value === 'cwl' &&
                        Globals.Proxies.experimentMainParam('_sample', 'type').value === 'pd') {
                    peakAsymmetryGroup.visible = true
                    return 'SideBarBasic/PdInstrPeakAsymm_PD-CWL.qml'
                } else {
                    peakAsymmetryGroup.visible = false
                    return ''
                }
            }
        }
    }

    EaElements.GroupBox {
        id: backgroundGroup
        title: Globals.Proxies.experimentLoopTitle(qsTr('Background'), '_pd_background')
        icon: 'wave-square'
        //visible: Globals.Proxies.main.experiment.defined
        visible: false

        Loader { source: {
                if (JSON.stringify(Globals.Proxies.experimentMainParam('_diffrn_radiation', 'type')) === '{}') {
                    backgroundGroup.visible = false
                    return ''
                }
                if (Globals.Proxies.experimentMainParam('_sample', 'type').value === 'pd') {
                    backgroundGroup.visible = true
                    return 'SideBarBasic/PdBackground_PD.qml'
                } else {
                    backgroundGroup.visible = false
                    return ''
                }
            }
        }
    }

    EaElements.GroupBox {
        title: Globals.Proxies.experimentLoopTitle(qsTr('Associated phases'), '_pd_phase_block')
        icon: 'layer-group'
        visible: Globals.Proxies.main.experiment.defined

        Loader { source: 'SideBarBasic/Phase.qml' }
    }

}
