import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Popup {
    id: manager
    objectName: "savedToolsManager"
    parent: Overlay.overlay
    anchors.centerIn: parent
    width: Math.min(548, parent.width - 24)
    height: Math.min(714, parent.height - 24)
    padding: 18
    modal: true
    focus: true
    property string kind: "phrases"
    property string identifier: ""
    readonly property bool isPhrase: kind === "phrases"
    readonly property var allItems: isPhrase ? mousyst.tools.phrases : mousyst.tools.favorites

    function edit(entry) {
        identifier = entry ? entry.id : ""
        titleEdit.text = entry ? entry.label : ""
        bodyEdit.text = isPhrase && entry ? entry.text : ""
        categoryEdit.text = isPhrase && entry ? entry.category : ""
        pinned.checked = isPhrase && entry ? entry.pinned : false
        keyChoice.currentIndex = !isPhrase && entry ? mousyst.tools.keys.indexOf(entry.key) : 0
        for (let i = 0; i < modifiers.count; i++) {
            let item = modifiers.itemAt(i)
            item.checked = !isPhrase && entry ? entry.modifiers.indexOf(item.text) >= 0 : false
        }
    }
    function manage(collection) {
        kind = collection
        search.text = ""
        edit(null)
        open()
    }
    function saveEntry() {
        let result
        if (isPhrase) {
            result = mousyst.tools.savePhrase(identifier, titleEdit.text, bodyEdit.text,
                                              categoryEdit.text, pinned.checked)
        } else {
            let chosen = []
            for (let i = 0; i < modifiers.count; i++) {
                let item = modifiers.itemAt(i)
                if (item.checked) chosen.push(item.text)
            }
            result = mousyst.tools.saveFavorite(identifier, titleEdit.text, keyChoice.currentText, chosen)
        }
        if (result) identifier = result
    }
    component Action: Button {
        id: action
        padding: 8; implicitHeight: 34
        background: Rectangle {
            radius: 6; color: action.down ? "#44444e" : action.hovered ? "#383840" : "#2c2c33"
            border.color: action.activeFocus ? "#aaaab5" : "#45454e"
        }
        contentItem: Text {
            text: action.text; color: action.enabled ? "#eeeef1" : "#858590"
            horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter
        }
    }
    background: Rectangle { radius: 12; color: "#1b1b20"; border.color: "#464650" }
    ColumnLayout {
        anchors.fill: parent; spacing: 8
        RowLayout {
            Layout.fillWidth: true
            Label {
                Layout.fillWidth: true; color: "#eeeef1"; font.pixelSize: 21
                text: manager.isPhrase ? "Saved phrases" : "Favorite shortcuts"
            }
            Action { text: "Done"; onClicked: manager.close() }
        }
        TextField {
            id: search; Layout.fillWidth: true
            placeholderText: manager.isPhrase ? "Search labels, text or categories" : "Search shortcut labels"
        }
        ListView {
            id: libraryList
            Layout.fillWidth: true; Layout.preferredHeight: Math.min(160, manager.height * .23)
            clip: true; boundsBehavior: Flickable.StopAtBounds
            model: manager.allItems.filter(entry => (entry.label + " " + (entry.category || "") + " " +
                       (entry.text || "")).toLowerCase().includes(search.text.toLowerCase()))
            ScrollBar.vertical: ScrollBar {}
            delegate: ItemDelegate {
                required property var modelData
                width: libraryList.width; height: 32
                highlighted: manager.identifier === modelData.id
                text: modelData.label + (manager.isPhrase ?
                      ((modelData.pinned ? "   ·   Pinned" : "") + (modelData.category ? "   ·   " + modelData.category : "")) :
                      ("   ·   " + modelData.modifiers.concat([modelData.key]).join("+")))
                contentItem: Text {
                    text: parent.text; textFormat: Text.PlainText
                    color: "#eeeef1"; elide: Text.ElideRight; verticalAlignment: Text.AlignVCenter
                }
                onClicked: manager.edit(modelData)
            }
            Label { anchors.centerIn: parent; visible: libraryList.count === 0; text: "No matching entries"; color: "#aaaab5" }
        }
        RowLayout {
            Action { text: "New"; onClicked: manager.edit(null) }
            Action { text: "Move up"; enabled: !!manager.identifier; onClicked: mousyst.tools.change(manager.kind, manager.identifier, "up") }
            Action { text: "Move down"; enabled: !!manager.identifier; onClicked: mousyst.tools.change(manager.kind, manager.identifier, "down") }
            Action { text: "Delete"; enabled: !!manager.identifier; onClicked: deleteEntry.open() }
        }
        ScrollView {
            Layout.fillWidth: true; Layout.fillHeight: true; clip: true
            contentWidth: availableWidth
            ColumnLayout {
                width: parent.width; spacing: 6
                Label { text: "Label"; color: "#bdbdc7" }
                TextField { id: titleEdit; objectName: "savedToolLabel"; Layout.fillWidth: true; maximumLength: 60; placeholderText: manager.isPhrase ? "e.g. Email signature" : "e.g. Find" }
                Label { visible: manager.isPhrase; text: "Phrase"; color: "#bdbdc7" }
                ScrollView {
                    visible: manager.isPhrase; Layout.fillWidth: true; Layout.preferredHeight: 80
                    TextArea { id: bodyEdit; objectName: "savedToolText"; textFormat: TextEdit.PlainText; wrapMode: TextEdit.Wrap; placeholderText: "Text to insert" }
                }
                RowLayout {
                    visible: manager.isPhrase
                    TextField { id: categoryEdit; Layout.fillWidth: true; maximumLength: 50; placeholderText: "Category (optional)" }
                    CheckBox { id: pinned; text: "Pinned" }
                }
                RowLayout {
                    visible: !manager.isPhrase
                    Repeater { id: modifiers; model: ["Ctrl", "Alt", "Shift", "Win"]; CheckBox { required property string modelData; text: modelData } }
                    ComboBox { id: keyChoice; model: mousyst.tools.keys; implicitWidth: 92 }
                }
                RowLayout {
                    Action { objectName:"saveShelfEntry"; text: manager.identifier ? "Save changes" : "Add entry"; onClicked: manager.saveEntry() }
                    Label { Layout.fillWidth: true; text: mousyst.tools.message; wrapMode: Text.Wrap; color: "#aaaab5" }
                }
            }
        }
        RowLayout {
            Action { text: "Import…"; onClicked: importLibrary.open() }
            Action { text: "Export…"; onClicked: mousyst.tools.transfer(manager.kind, false) }
        }
    }
    Dialog {
        id: deleteEntry; anchors.centerIn: parent; modal: true; title: "Delete this entry?"
        standardButtons: Dialog.Yes | Dialog.Cancel
        onAccepted: if (mousyst.tools.change(manager.kind, manager.identifier, "delete")) manager.edit(null)
    }
    Dialog {
        id: importLibrary; anchors.centerIn: parent; modal: true; title: "Replace this library from a file?"
        standardButtons: Dialog.Yes | Dialog.Cancel
        onAccepted: { mousyst.tools.transfer(manager.kind, true); manager.edit(null) }
    }
}
