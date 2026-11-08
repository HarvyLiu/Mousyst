import QtQuick
import QtQuick.Window
import QtQuick.Effects

Window {
    id: main
    width: 680
    height: 510
    minimumWidth: 620
    minimumHeight: 510
    visible: controller.practiceMode || !controller.trayAvailable
    color: "#131518"
    title: "Mousyst — Qt Quick typing preview"
    x: 60
    y: 90
    onClosing: (close) => {
        if (controller.trayAvailable) {
            close.accepted = false
            keyboard.hide()
            main.hide()
        } else {
            Qt.quit()
        }
    }
    onVisibilityChanged: {
        if (controller.trayAvailable && visibility === Window.Minimized) {
            keyboard.hide()
            main.hide()
        }
    }

    function openKeyboard() {
        controller.cancel()
        keyboard.x = Math.max(main.Screen.virtualX,
            Math.min(main.x + main.width + 16, main.Screen.virtualX + main.Screen.width - keyboard.width))
        keyboard.y = Math.max(main.Screen.virtualY,
            Math.min(main.y, main.Screen.virtualY + main.Screen.height - keyboard.height - 40))
        keyboard.show()
        keyboard.raise()
        keyboard.requestActivate()
    }
    Component.onCompleted: if (controller.practiceMode) Qt.callLater(openKeyboard)

    Column {
        anchors.fill: parent
        anchors.margins: 32
        spacing: 18
        Row {
            spacing: 12
            Rectangle {
                width: 34; height: 34; radius: 11; color: "#e6ede8"
                Text { anchors.centerIn: parent; text: "m"; color: "#171c19"; font.family: "Segoe UI"; font.pixelSize: 23; font.weight: Font.DemiBold }
            }
            Column {
                spacing: 3
                Text { text: "mousyst"; color: "#f1f2f4"; font.family: "Segoe UI"; font.pixelSize: 18; font.weight: Font.DemiBold }
                Text { text: "DESKTOP TYPING"; color: "#858d96"; font.family: "Segoe UI"; font.pixelSize: 9; font.letterSpacing: 1.6 }
            }
        }
        Column {
            spacing: 7
            Text { text: "A little movement. A whole thought."; color: "#f1f2f4"; font.family: "Segoe UI"; font.pixelSize: 25; font.weight: Font.Medium }
            Text { text: "Choose a group. Slice through a letter. Return to the center."; color: "#929aa4"; font.family: "Segoe UI"; font.pixelSize: 12 }
        }
        Rectangle {
            width: parent.width
            height: 144
            radius: 18
            color: "#1c1f24"
            border.color: "#30343a"
            Column {
                anchors.fill: parent; anchors.margins: 20; spacing: 12
                Text { text: "DIRECT TO YOUR APP"; color: "#868f99"; font.family: "Segoe UI"; font.pixelSize: 9; font.letterSpacing: 1.4 }
                Text { width: parent.width; text: controller.practiceMode ? controller.target : "Click a text field, then middle-click to summon the keyboard."; color: "#aeb5bd"; font.family: "Segoe UI"; font.pixelSize: 15; wrapMode: Text.Wrap }
                Text { width: parent.width; text: controller.typed || "Your words start here…"; color: controller.typed ? "#eff5f1" : "#606975"; font.family: "Segoe UI"; font.pixelSize: 19; wrapMode: Text.Wrap; maximumLineCount: 2; elide: Text.ElideRight }
            }
        }
        Row {
            spacing: 40
            Repeater {
                model: [{value: "Middle-click", label: "OPEN / HIDE"},
                        {value: "Esc", label: "DISMISS"},
                        {value: "Direct", label: "TEXT OUTPUT"}]
                Column {
                    required property var modelData
                    spacing: 5
                    Text { text: modelData.value; color: "#eef0f3"; font.family: "Segoe UI"; font.pixelSize: 22 }
                    Text { text: modelData.label; color: "#7f8995"; font.family: "Segoe UI"; font.pixelSize: 9; font.letterSpacing: 1 }
                }
            }
        }
        Row {
            spacing: 10
            ActionButton { text: controller.trayAvailable ? "Hide to tray" : "Minimize panel"; primary: true; onClicked: controller.trayAvailable ? main.hide() : main.showMinimized() }
            ActionButton { text: "Clear local display"; onClicked: controller.reset() }
        }
        Text {
            width: parent.width; wrapMode: Text.Wrap; text: controller.status
            color: controller.complete ? "#b7dfc7" : "#777f89"
            font.family: "Segoe UI"; font.pixelSize: 11
        }
    }

    Window {
        id: keyboard
        objectName: "keyboard"
        width: 560; height: 600
        title: "Mousyst — radial keyboard"
        color: "transparent"
        flags: Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.WindowDoesNotAcceptFocus
        property bool moving: headerDrag.active
        onVisibleChanged: controller.cancel()

        Item {
            id: keys
            anchors.fill: parent
            focus: true
            Keys.onEscapePressed: keyboard.hide()
            opacity: keyboard.visible ? 1 : 0
            Behavior on opacity { NumberAnimation { duration: 140; easing.type: Easing.OutCubic } }

            // All surfaces remain readable over an arbitrary desktop. The
            // surrounding window uses actual alpha, including the shadow.
            Item {
                anchors.fill: parent
                layer.enabled: true
                layer.effect: MultiEffect {
                    shadowEnabled: true
                    shadowColor: "#b0000000"
                    shadowBlur: 0.65
                    shadowVerticalOffset: 5
                    shadowHorizontalOffset: 0
                }
                Repeater {
                    model: controller.groups
                    Sector {
                        required property var modelData
                        segment: modelData
                        highlighted: controller.activeGroup === modelData.index
                    }
                }
                Repeater {
                    model: controller.fan
                    Sector {
                        required property var modelData
                        segment: modelData
                        letter: true
                        highlighted: controller.selected === modelData.value
                        opacity: 0
                        Component.onCompleted: opacity = 1
                        Behavior on opacity { NumberAnimation { duration: 85 } }
                    }
                }
                Rectangle {
                    x: 242; y: 262; width: 76; height: 76; radius: 38
                    color: controller.armed ? "#e3ece6" : "#202328"
                    border.color: controller.armed ? "#f2faf5" : "#525860"
                    Behavior on color { ColorAnimation { duration: 110 } }
                    Text {
                        anchors.centerIn: parent
                        text: controller.flash || "MOUSYST"
                        font.family: "Segoe UI"
                        font.pixelSize: controller.flash ? 25 : 10
                        font.weight: Font.DemiBold
                        color: controller.armed ? "#24322a" : "#eef1f4"
                    }
                }
            }
            Rectangle {
                x: 172; y: 28; width: 216; height: 38; radius: 19
                color: "#24272c"; border.color: "#44484e"
                Text { x: 18; anchors.verticalCenter: parent.verticalCenter; text: "mousyst"; color: "#e0e5e1"; font.family: "Segoe UI"; font.pixelSize: 12; font.weight: Font.DemiBold }
                Text { x: 87; anchors.verticalCenter: parent.verticalCenter; text: "··· drag"; color: "#87918c"; font.family: "Segoe UI"; font.pixelSize: 11 }
                DragHandler {
                    id: headerDrag
                    target: null
                    onActiveChanged: {
                        controller.cancel()
                        if (active) keyboard.startSystemMove()
                    }
                }
                Rectangle {
                    x: 178; y: 5; width: 28; height: 28; radius: 14
                    color: closeMouse.containsMouse ? "#42474e" : "transparent"
                    Text { anchors.centerIn: parent; text: "×"; color: "#b9c0c7"; font.pixelSize: 19 }
                    MouseArea { id: closeMouse; anchors.fill: parent; hoverEnabled: true; onClicked: keyboard.hide() }
                }
            }
            Rectangle {
                x: 135; y: 552; width: 290; height: 30; radius: 15
                color: "#ed202328"; border.color: "#394047"
                Text {
                    anchors.centerIn: parent
                    text: controller.complete ? "Complete — try another phrase"
                          : !controller.armed ? "Return to the center"
                          : controller.activeGroup < 0 ? "Choose a direction"
                          : "Slice outward to enter · inward to cancel"
                    color: "#b8c0c8"; font.family: "Segoe UI"; font.pixelSize: 10
                }
            }
        }
    }
}
