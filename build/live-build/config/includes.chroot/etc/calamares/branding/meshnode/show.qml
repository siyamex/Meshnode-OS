/* show.qml — minimal Calamares slideshow for meshnode OS (Phase 6 placeholder).
 * Phase 7 will replace this with proper slides and graphics.
 */
import QtQuick 2.0
import calamares.slideshow 1.0

Presentation {
    id: presentation

    property bool activatedInCalamares: false

    Slide {
        anchors.fill: parent

        Rectangle {
            anchors.fill: parent
            color: "#0f172a"

            Column {
                anchors.centerIn: parent
                spacing: 16

                Text {
                    anchors.horizontalCenter: parent.horizontalCenter
                    text: "meshnode OS"
                    color: "#38bdf8"
                    font.pixelSize: 36
                    font.bold: true
                }
                Text {
                    anchors.horizontalCenter: parent.horizontalCenter
                    text: "Installing — this takes a few minutes…"
                    color: "#94a3b8"
                    font.pixelSize: 16
                }
                Text {
                    anchors.horizontalCenter: parent.horizontalCenter
                    text: "After reboot, the setup wizard will guide you\nthrough joining the mesh and forming a cluster."
                    color: "#64748b"
                    font.pixelSize: 13
                    horizontalAlignment: Text.AlignHCenter
                    lineHeight: 1.5
                }
            }
        }
    }

    Timer {
        interval: 20000
        running: presentation.activatedInCalamares
        repeat: true
        onTriggered: presentation.goToNextSlide()
    }
}
