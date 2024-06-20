// SPDX-FileCopyrightText: 2023 EasyDiffraction contributors <support@easydiffraction.org>
// SPDX-License-Identifier: BSD-3-Clause
// © 2023 Contributors to the EasyDiffraction project <https://github.com/easyscience/EasyDiffraction>

import QtQuick
import QtQuick.Controls

import EasyApp.Gui.Style as EaStyle
import EasyApp.Gui.Elements as EaElements
import EasyApp.Gui.Components as EaComponents

Rectangle {

    width: 500
    height: 300

    color: 'transparent'

    // Flickable
    Flickable {
        id: flick

        anchors.fill: parent

        contentWidth: textArea.contentWidth
        contentHeight: textArea.contentHeight

        clip: true
        flickableDirection: Flickable.VerticalFlick

        ScrollBar.vertical: EaElements.ScrollBar {
            policy: ScrollBar.AsNeeded
            interactive: false
        }

        // Main text area
        EaElements.TextArea {
            id: textArea

            width: flick.width
            topPadding: 0
            bottomPadding: 0

            //backgroundRect.border.color: EaStyle.Colors.appBarComboBoxBorder
            textFormat: TextEdit.RichText
            text: content
        }
        // Main text area

    }
    // Flickable

    property string content: `
<!DOCTYPE html>

<html>

<style>
    th, td {
        padding-right: 18px;
    }
</style>

<body>

    <h1>Summary</h1>

    <tr>
        <td><h3>Crystal data</h3></td>
    </tr>

    <tr></tr>

    <tr>
        <td><b>coo<b></td>
    </tr>
    <tr>
        <td>Crystal system, space group</td>
        <td>Orthorhombic, <i>Pnma</i></td>
    </tr>
    <tr>
        <td><i>a</i>, <i>b</i>, <i>c</i> (Å)</td>
        <td>8.92(1), 8.92(1), 8.92(1)</td>
    </tr>
    <tr>
        <td><i>α</i>, <i>β</i>, <i>γ</i> (°)</td>
        <td>90(1), 90(1), 90(1)</td>
    </tr>

    <tr></tr>

    <tr>
        <td><h3>Data collection</h3></td>
    </tr>

    <tr></tr>

    <tr>
        <td><b>hrpt</b></td>
    </tr>
    <tr>
        <td>Radiation probe</td>
        <td>Neutron</td>
    </tr>
    <tr>
        <td>Radiation type</td>
        <td>Constant wavelength</td>
    </tr>
    <tr>
        <td>Radiation wavelength, λ (Å)</td>
        <td>0.793</td>
    </tr>
    <tr>
        <td>Measured range, <i>θ</i><sub>min</sub>, <i>θ</i><sub>max</sub>, <i>θ</i><sub>inc</sub> (°)</td>
        <td>10, 150, 0.05</td>
    </tr>
    <tr>
        <td>No. of data points</td>
        <td>347</td>
    </tr>

    <tr></tr>

    <tr>
        <td><h3>Refinement</h3></td>
    </tr>

    <tr></tr>

    <tr>
        <td>Goodness-of-fit (<i>χ</i><sup>2</sup>)</td>
        <td>3.17</td>
    </tr>
    <tr>
        <td>No. of reflections</td>
        <td>347</td>
    </tr>
    <tr>
        <td>No. of total, free, fixed parameters</td>
        <td>50, 20, 10</td>
    </tr>
    <tr>
        <td>No. of constraints</td>
        <td>0</td>
    </tr>

</body>

</html>
`

}
