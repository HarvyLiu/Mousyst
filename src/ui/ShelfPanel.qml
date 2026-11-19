import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: shelf
    required property string section
    required property real pitch
    property bool phraseAllowed: false
    property string query: ""
    property bool searching: false
    function refresh() {
        searching = false
        query = ""
        phraseAllowed = visible && section === "phrases" && mousyst.tools.allowPhraseShelf()
    }
    onSectionChanged: refresh()
    onVisibleChanged: refresh()
    Timer {
        running: shelf.visible && shelf.section === "phrases" && shelf.phraseAllowed
        interval: 450; repeat: true
        onTriggered: shelf.phraseAllowed = mousyst.tools.allowPhraseShelf()
    }

    component Tile: Button {
        id: tile
        focusPolicy: Qt.NoFocus
        padding: 4
        background: Rectangle {
            radius: 5; color: tile.down ? "#4c4c56" : tile.hovered ? "#34343c" : "#29292f"
            border.color: "#404048"
        }
        contentItem: Text {
            text: tile.text; textFormat: Text.PlainText; color: "#eeeef1"; font.family: "Segoe UI"
            font.pixelSize: Math.max(11, Math.min(15, shelf.pitch * .25))
            elide: Text.ElideRight; horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
        }
    }
    ColumnLayout {
        anchors.fill: parent; spacing: 4
        RowLayout {
            Layout.fillWidth: true; visible: shelf.section === "phrases" && shelf.phraseAllowed
            Label {
                Layout.fillWidth: true; text: shelf.query ? ("Filter · " + shelf.query) : "Saved phrases"
                color: "#aaaab5"; elide: Text.ElideRight
            }
            Tile {
                text: shelf.searching ? "Show matches" : "Filter"
                implicitHeight: 24; implicitWidth: 100
                onClicked: shelf.searching = !shelf.searching
            }
            Tile {
                visible: shelf.query.length > 0
                text: "Clear"; implicitHeight: 24; implicitWidth: 62
                onClicked: shelf.query = ""
            }
        }
        GridLayout {
            visible: shelf.searching && shelf.phraseAllowed
            columns: 10; rowSpacing: 3; columnSpacing: 3; Layout.fillWidth: true; Layout.fillHeight: true
            Repeater {
                model: "abcdefghijklmnopqrstuvwxyz".split("").concat(["Space", "Back"])
                Tile {
                    required property string modelData
                    text: modelData; Layout.fillWidth: true; Layout.fillHeight: true
                    onClicked: shelf.query = modelData === "Back" ? shelf.query.slice(0,-1) :
                        shelf.query + (modelData === "Space" ? " " : modelData)
                }
            }
        }
        GridView {
            id: entries
            visible: !shelf.searching || !shelf.phraseAllowed
            Layout.fillWidth: true; Layout.fillHeight: true; clip: true
            boundsBehavior: Flickable.StopAtBounds
            cellWidth: width / (shelf.section === "phrases" ? 3 : 4)
            cellHeight: Math.min(52, Math.max(30, shelf.pitch - 4))
            model: shelf.section === "edit" ? mousyst.tools.edits : shelf.section === "favorites" ?
                   mousyst.tools.favorites : shelf.phraseAllowed ? mousyst.tools.phrases.filter(
                       p => (p.label + " " + p.category + " " + p.text).toLowerCase().includes(shelf.query.toLowerCase())) : []
            delegate: Item {
                required property var modelData
                width: entries.cellWidth; height: entries.cellHeight
                Tile {
                    anchors.fill: parent; anchors.margins: 2
                    objectName: "shelfEntry_" + modelData.id
                    text: modelData.label + (shelf.section === "favorites" ? "\n" +
                          modelData.modifiers.concat([modelData.key]).join("+") : "")
                    onClicked: mousyst.tools.run(shelf.section, modelData.id)
                }
            }
            ScrollBar.vertical: ScrollBar {}
            Label {
                anchors.centerIn: parent; visible: entries.count === 0
                width: parent.width - 24; horizontalAlignment: Text.AlignHCenter
                color: "#aaaab5"; wrapMode: Text.Wrap
                text: shelf.section === "phrases" && !shelf.phraseAllowed ?
                      "Middle-click a non-password text field to use saved phrases." :
                      shelf.query ? "No matching phrases." : "Add entries in Settings."
            }
        }
    }
}
