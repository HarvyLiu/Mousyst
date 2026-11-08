import QtQuick
import QtQuick.Shapes

Item {
    id: sector
    required property var segment
    property bool highlighted: false
    property bool letter: false
    width: 560
    height: 600
    Shape {
        anchors.fill: parent
        preferredRendererType: Shape.CurveRenderer
        ShapePath {
            strokeWidth: 1
            strokeColor: sector.highlighted ? "#dce9e2" : "#44484f"
            fillColor: sector.highlighted ? "#e1eee6" : "#25282e"
            Behavior on fillColor { ColorAnimation { duration: 90 } }
            Behavior on strokeColor { ColorAnimation { duration: 90 } }
            PathSvg { path: sector.segment.path }
        }
    }
    Text {
        x: sector.segment.x - width / 2
        y: sector.segment.y - height / 2
        text: sector.segment.label
        font.family: "Segoe UI"
        font.pixelSize: sector.letter ? 23 : (text.length > 1 ? 11 : 23)
        font.weight: sector.letter ? Font.Medium : Font.DemiBold
        font.letterSpacing: sector.letter ? 0 : 0.5
        color: sector.highlighted ? "#19231e" : "#e6e8eb"
        Behavior on color { ColorAnimation { duration: 90 } }
    }
}
