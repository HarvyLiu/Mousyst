import QtQuick
import QtQuick.Controls.Basic

Button {
    id: button
    property bool primary: false
    implicitHeight: 42
    implicitWidth: label.implicitWidth + 32
    hoverEnabled: true
    contentItem: Text {
        id: label
        text: button.text
        font.family: "Segoe UI"
        font.pixelSize: 13
        font.weight: Font.DemiBold
        color: button.primary ? "#151719" : "#e4e6e9"
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
    }
    background: Rectangle {
        radius: 12
        color: button.primary ? (button.hovered ? "#ffffff" : "#e8eeeb")
                              : (button.hovered ? "#30343a" : "#22252a")
        border.width: button.primary ? 0 : 1
        border.color: "#363a40"
        Behavior on color { ColorAnimation { duration: 110 } }
    }
}
