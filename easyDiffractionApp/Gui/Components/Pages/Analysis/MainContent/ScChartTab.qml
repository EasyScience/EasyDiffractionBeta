// SPDX-FileCopyrightText: 2023 EasyDiffraction contributors <support@easydiffraction.org>
// SPDX-License-Identifier: BSD-3-Clause
// © 2023 Contributors to the EasyDiffraction project <https://github.com/easyscience/EasyDiffraction>

import QtQuick
import QtQuick.Controls
import QtCharts

import EasyApp.Gui.Style as EaStyle
import EasyApp.Gui.Globals as EaGlobals
import EasyApp.Gui.Elements as EaElements
import EasyApp.Gui.Charts as EaCharts

import Gui.Globals as Globals


Rectangle {
    id: container

    color: EaStyle.Colors.chartBackground

    EaCharts.QtCharts1dBase {
        id: chartView

        property alias scSerie: scSerie

        anchors.topMargin: EaStyle.Sizes.toolButtonHeight - EaStyle.Sizes.fontPixelSize - 1

        useOpenGL: EaGlobals.Vars.useOpenGL //Globals.Proxies.main.plotting.useWebGL1d

        axisX.title: "Icalc"
        axisX.min: Globals.Proxies.rangeValue('x2Min')
        axisX.max: Globals.Proxies.rangeValue('x2Max')
        axisX.minAfterReset: Globals.Proxies.rangeValue('x2Min')
        axisX.maxAfterReset: Globals.Proxies.rangeValue('x2Max')

        axisY.title: "Imeas"
        axisY.min: Globals.Proxies.rangeValue('y2Min')
        axisY.max: Globals.Proxies.rangeValue('y2Max')
        axisY.minAfterReset: Globals.Proxies.rangeValue('y2Min')
        axisY.maxAfterReset: Globals.Proxies.rangeValue('y2Max')

        // Diagonal line
        LineSeries {
            axisX: chartView.axisX
            axisY: chartView.axisY

            color: EaStyle.Colors.chartAxis
            width: 1

            XYPoint { x: Globals.Proxies.rangeValue('x2Min'); y: Globals.Proxies.rangeValue('y2Min') }
            XYPoint { x: Globals.Proxies.rangeValue('x2Max'); y: Globals.Proxies.rangeValue('y2Max') }
        }
        // Diagonal line

        // Main scatters
        LineSeries {
            id: scSerie

            axisX: chartView.axisX
            axisY: chartView.axisY

            useOpenGL: chartView.useOpenGL

            color: EaStyle.Colors.chartForegroundsExtra[2]
            width: 2

            style: Qt.NoPen
            pointsVisible: true

            onHovered: (point, state) => showMainTooltip(chartView, point, state)
        }
        // Main scatters

        // Tool buttons
        Row {
            id: toolButtons

            x: chartView.plotArea.x + chartView.plotArea.width - width
            y: chartView.plotArea.y - height - EaStyle.Sizes.fontPixelSize

            spacing: 0.25 * EaStyle.Sizes.fontPixelSize

            EaElements.TabButton {
                checked: chartView.allowHover
                autoExclusive: false
                height: EaStyle.Sizes.toolButtonHeight
                width: EaStyle.Sizes.toolButtonHeight
                borderColor: EaStyle.Colors.chartAxis
                fontIcon: "comment-alt"
                ToolTip.text: qsTr("Show coordinates tooltip on hover")
                onClicked: chartView.allowHover = !chartView.allowHover
            }

            Item { height: 1; width: 0.5 * EaStyle.Sizes.fontPixelSize }  // spacer

            EaElements.TabButton {
                checked: !chartView.allowZoom
                autoExclusive: false
                height: EaStyle.Sizes.toolButtonHeight
                width: EaStyle.Sizes.toolButtonHeight
                borderColor: EaStyle.Colors.chartAxis
                fontIcon: "arrows-alt"
                ToolTip.text: qsTr("Enable pan")
                onClicked: chartView.allowZoom = !chartView.allowZoom
            }

            EaElements.TabButton {
                checked: chartView.allowZoom
                autoExclusive: false
                height: EaStyle.Sizes.toolButtonHeight
                width: EaStyle.Sizes.toolButtonHeight
                borderColor: EaStyle.Colors.chartAxis
                fontIcon: "expand"
                ToolTip.text: qsTr("Enable box zoom")
                onClicked: chartView.allowZoom = !chartView.allowZoom
            }

            EaElements.TabButton {
                checkable: false
                height: EaStyle.Sizes.toolButtonHeight
                width: EaStyle.Sizes.toolButtonHeight
                borderColor: EaStyle.Colors.chartAxis
                fontIcon: "backspace"
                ToolTip.text: qsTr("Reset axes")
                onClicked: chartView.resetAxes()
            }

        }
        // Tool buttons

        // ToolTips
        EaElements.ToolTip {
            id: dataToolTip

            arrowLength: 0
            textFormat: Text.RichText
        }
        // ToolTips

        // Data is set in python backend

        Component.onCompleted: {
            Globals.Refs.app.experimentPage.plotView = chartView
            Globals.Proxies.main.plotting.setQtChartsSerieRef('analysisPage',
                                                              'scSerie',
                                                              chartView.scSerie)
        }

    }

    // Logic

    function showMainTooltip(chart, point, state) {
        if (!chartView.allowHover) {
            return
        }
        const pos = chart.mapToPosition(Qt.point(point.x, point.y))
        dataToolTip.x = pos.x
        dataToolTip.y = pos.y
        dataToolTip.text = `<p align="left">x: ${point.x.toFixed(2)}<br\>y: ${point.y.toFixed(2)}</p>`
        dataToolTip.parent = chart
        dataToolTip.visible = state
    }

}

