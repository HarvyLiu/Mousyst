import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Window

ApplicationWindow {
    component SoftButton: Button {
        implicitWidth: Math.max(36, contentItem.implicitWidth + 24)
        implicitHeight: 34
        background: Rectangle { radius: 8; color: parent.down || parent.checked ? '#54725e' : parent.hovered ? '#35483c' : '#29312d'; border.color: '#46574b' }
    }
    id: root
    visible: true
    width: 860; height: 940
    minimumWidth: 820; minimumHeight: 900
    color: '#131518'
    title: 'Mousyst — click & swipe experiment'
    property real pitch: size.currentIndex === 0 ? 36 : size.currentIndex === 2 ? 48 : 42
    property bool symbols: false
    property bool keyboardOpen: false
    function pressKey(value) { practice.activateKey(value, output.selectionStart, output.selectionEnd, output.cursorPosition) }
    palette.button: '#29312d'
    palette.buttonText: '#e3ece6'
    palette.base: '#20252a'
    palette.text: '#e3ece6'
    palette.windowText: '#e3ece6'
    palette.highlight: '#6eaa87'
    Connections { target: practice; function onTrialReset() { root.keyboardOpen = false; board.abort() } }
    Connections {
        target: practice
        function onSelectionRequested(start,end) { output.select(start,end) }
        function onCaptureRequested() { snip.visible = true; snip.selection = Qt.rect(0,0,0,0) }
    }
    onActiveChanged: if (!active) { board.abort(); practice.cancel(); snip.visible = false }
    Shortcut { sequence: 'Escape'; onActivated: { board.abort(); practice.cancel(); snip.visible = false } }
    ColumnLayout {
        anchors.fill: parent; anchors.margins: 28; spacing: 12
        Label { text: 'm  mousyst'; color: '#e3ece6'; font.pixelSize: 26; font.weight: Font.DemiBold }
        Label { text: 'Short words. One continuous movement.'; color: '#a9b6ae'; font.pixelSize: 18 }
        RowLayout {
            Label { text: 'Condition'; color: '#a9b6ae' }
            ComboBox { id: condition; model: ['Click only', 'Click + swipe', 'Physical keyboard']; currentIndex: 1
                onActivated: { board.abort(); practice.condition(currentIndex) } }
            ComboBox { id: size; model: ['Small', 'Default', 'Large']; currentIndex: 1; onActivated: { board.abort(); practice.cancel() } }
            Label { text: 'Tester'; color: '#a9b6ae' }
            SpinBox { from: 0; to: 99; onValueModified: practice.participantChanged(value) }
        }
        Label { text: 'TASK  ·  ' + practice.target; color: '#e3ece6'; font.pixelSize: 19; Layout.fillWidth: true; wrapMode: Text.Wrap }
        CheckBox { id: shortcutExercise; text: 'Shortcut practice (local clipboard and snipping exercise)'; onToggled: { practice.shortcutActivity(checked); root.keyboardOpen = true } }
        ScrollView {
            Layout.fillWidth: true; Layout.preferredHeight: 96
            TextArea {
                id: output
                objectName: 'practiceText'
                selectByMouse: true
                persistentSelection: true
                text: practice.text
                readOnly: condition.currentIndex !== 2
                color: '#f1f5f2'; font.pixelSize: 23; wrapMode: TextEdit.Wrap
                placeholderText: 'Your text appears here…'
                background: Rectangle { color: '#20252a'; radius: 12; border.color: '#424c46' }
                onTextChanged: if (text !== practice.text) practice.physical(text)
            }
        }
        Label { text: condition.currentIndex === 2 ? 'Type in the box with your physical keyboard.' : 'Click to spell • Hold left-click and trace letters to swipe • Escape cancels'; color: '#a9b6ae' }
        RowLayout {
            SoftButton { text: root.keyboardOpen ? 'Hide keyboard' : 'Open keyboard'; visible: condition.currentIndex !== 2; onClicked: { root.keyboardOpen = !root.keyboardOpen; board.abort() } }
            Repeater {
                model: practice.suggestions
                SoftButton { required property string modelData; required property int index
                    text: (index === 0 ? '✓ ' : '') + modelData
                    onClicked: practice.alternative(index) }
            }
            Item { Layout.fillWidth: true }
            SoftButton { text: 'Undo word'; enabled: condition.currentIndex !== 2; onClicked: practice.key('Undo') }
        }
        Item {
            id: board
            objectName: 'letterBoard'
            Layout.alignment: Qt.AlignHCenter
            Layout.preferredWidth: root.pitch * 10
            Layout.preferredHeight: root.pitch * 3
            visible: condition.currentIndex !== 2 && root.keyboardOpen
            property var path: []
            property real maxDistance: 0
            property string first: ''
            property bool dragging: false
            property point lastPointer: Qt.point(-1,-1)
            function letterAt(x,y) {
                for (let i = 0; i < practice.keys.length; i++) {
                    let k = practice.keys[i]
                    if (x >= k.kx && x <= k.kx+.94 && y >= k.ky && y <= k.ky+.94) return k.letter
                }
                return ''
            }
            function abort() { dragging = false; path = []; trail.requestPaint() }
            Repeater {
                model: practice.keys
                Rectangle {
                    required property var modelData
                    x: modelData.kx * root.pitch; y: modelData.ky * root.pitch
                    width: root.pitch - 3; height: root.pitch - 3; radius: 8
                    color: board.dragging && board.letterAt(pointer.mouseX/root.pitch,pointer.mouseY/root.pitch) === modelData.letter ? '#bad9c5' : '#29312d'
                    border.color: '#47564c'
                    Text { objectName: 'keyLabel_' + modelData.letter; anchors.centerIn: parent; text: root.symbols ? board.symbolFor(modelData.letter) : practice.shifted ? modelData.letter.toUpperCase() : modelData.letter; color: '#ecf5ef'; font.pixelSize: 19 }
                }
            }
            function symbolFor(letter) {
                let letters = 'qwertyuiopasdfghjklzxcvbnm'
                let chars = ['1','2','3','4','5','6','7','8','9','0','+','-','*','/','=','(',')','^','%','[',']','<','>','!','?','@']
                return chars[letters.indexOf(letter)]
            }
            Canvas {
                id: trail; anchors.fill: parent
                onPaint: {
                    let ctx = getContext('2d'); ctx.clearRect(0,0,width,height)
                    if (board.path.length < 2) return
                    ctx.strokeStyle = '#b9ead0'; ctx.lineWidth = 2; ctx.lineJoin = 'round'; ctx.beginPath()
                    ctx.moveTo(board.path[0].x*root.pitch,board.path[0].y*root.pitch)
                    for (let i=1;i<board.path.length;i++) ctx.lineTo(board.path[i].x*root.pitch,board.path[i].y*root.pitch)
                    ctx.stroke()
                }
            }
            MouseArea {
                id: pointer; anchors.fill: parent; hoverEnabled: true; preventStealing: true
                onPressed: mouse => {
                    board.first = board.letterAt(mouse.x/root.pitch,mouse.y/root.pitch)
                    board.dragging = board.first !== ''
                    board.path = [{x: mouse.x/root.pitch,y: mouse.y/root.pitch}]; board.maxDistance = 0
                }
                onPositionChanged: mouse => {
                    board.lastPointer = Qt.point(mouse.x,mouse.y)
                    if (!board.dragging) return
                    let p = {x: mouse.x/root.pitch,y: mouse.y/root.pitch}
                    board.path.push(p)
                    board.maxDistance = Math.max(board.maxDistance,Math.hypot(p.x-board.path[0].x,p.y-board.path[0].y))
                    trail.requestPaint()
                }
                onExited: if (!pressed) board.lastPointer = Qt.point(-1,-1)
                onCanceled: { board.abort(); practice.cancel() }
                onReleased: mouse => {
                    if (!board.dragging) return
                    let end = board.letterAt(mouse.x/root.pitch,mouse.y/root.pitch)
                    board.path.push({x:mouse.x/root.pitch,y:mouse.y/root.pitch})
                    board.maxDistance = Math.max(board.maxDistance,Math.hypot(mouse.x/root.pitch-board.path[0].x,mouse.y/root.pitch-board.path[0].y))
                    if (mouse.x>=0 && mouse.y>=0 && mouse.x<=width && mouse.y<=height) {
                        if (!root.symbols && practice.activeModifiers.length === 0 && condition.currentIndex === 1 && board.maxDistance > 1/3) practice.stroke(board.path)
                        else if (end === board.first) root.pressKey(root.symbols ? board.symbolFor(end) : end)
                    } else practice.cancel()
                    board.abort()
                }
            }
        }
        RowLayout {
            Layout.alignment: Qt.AlignHCenter; visible: condition.currentIndex !== 2 && root.keyboardOpen
            Repeater {
                model: ['Ctrl', 'Alt', 'Win']
                SoftButton { required property string modelData; objectName: 'modifier_' + modelData; text: modelData; checked: practice.activeModifiers.indexOf(modelData) !== -1; onClicked: practice.modifier(modelData) }
            }
            SoftButton { objectName: 'modifier_Shift'; text: practice.shifted ? 'SHIFT ↑' : 'Shift'; checked: practice.shifted; onClicked: practice.key('Shift') }
            SoftButton { objectName: 'endKey'; text: 'End'; onClicked: root.pressKey('End') }
            Label { text: practice.activeModifiers.length ? practice.activeModifiers.join(' + ') + (practice.shifted ? ' + Shift' : '') + ' + …' : 'Modifiers apply to the next key'; color: '#b0c7b9' }
        }
        RowLayout {
            Layout.alignment: Qt.AlignHCenter; visible: condition.currentIndex !== 2 && root.keyboardOpen
            SoftButton { objectName: 'numericToggle'; text: root.symbols ? 'ABC' : '123 / +'; onClicked: { board.abort(); practice.cancel(); root.symbols = !root.symbols } }
            SoftButton { text: 'Space'; Layout.preferredWidth: 100; onClicked: root.pressKey(' ') }
            Repeater { model: ['.', ',', "'", ':', ';']; SoftButton { required property string modelData; text: modelData; onClicked: root.pressKey(modelData) } }
            SoftButton { text: '⌫'; onClicked: root.pressKey('Back') }
        }
        Label { text: practice.message; color: '#b0c7b9'; Layout.fillWidth: true; wrapMode: Text.Wrap }
        RowLayout {
            Label { text: 'Comfort (1–5)'; color: '#a9b6ae' }
            SpinBox { id: comfort; from: 1; to: 5; value: 3 }
            ComboBox { id: preference; model: ['Undecided', 'Prefer click', 'Prefer swipe', 'Prefer physical'] }
            SoftButton { text: shortcutExercise.checked ? 'Finish shortcut trial' : 'Finish / next task'; onClicked: { practice.finish(comfort.value,preference.currentText); if(condition.currentIndex===2) output.forceActiveFocus() } }
        }
        RowLayout {
            SoftButton { text: 'Restart task'; onClicked: practice.reset() }
            CheckBox { text: 'Record strokes for testing'; onToggled: practice.record(checked) }
            SoftButton { text: 'Export results…'; onClicked: practice.export() }
        }
        Label { text: 'Results stay in memory until you export. No desktop typing is active.\nFor a comparison: rotate the three conditions between testers and give each equal practice time.'; color: '#7f9386'; wrapMode: Text.Wrap; Layout.fillWidth: true }
        Item { Layout.fillHeight: true }
    }
    Rectangle {
        id: snip; objectName: 'practiceSnip'; anchors.fill: parent; visible: false; z: 20; color: '#e0131518'
        property rect selection: Qt.rect(0,0,0,0)
        Label { anchors.horizontalCenter: parent.horizontalCenter; y: 40; text: 'Practice snip · drag a rectangle · Esc cancels'; color: '#e3ece6'; font.pixelSize: 20 }
        Rectangle { x: snip.selection.x; y: snip.selection.y; width: snip.selection.width; height: snip.selection.height; color: '#304b9065'; border.color: '#b9ead0'; border.width: 2 }
        MouseArea {
            anchors.fill: parent; cursorShape: Qt.CrossCursor
            property point origin
            onPressed: mouse => { origin = Qt.point(mouse.x,mouse.y) }
            onPositionChanged: mouse => { if (pressed) snip.selection = Qt.rect(Math.min(origin.x,mouse.x),Math.min(origin.y,mouse.y),Math.abs(origin.x-mouse.x),Math.abs(origin.y-mouse.y)) }
            onReleased: mouse => {
                let w = Math.round(Math.abs(origin.x-mouse.x)), h = Math.round(Math.abs(origin.y-mouse.y))
                if (w > 0 && h > 0) practice.captureRegion(w,h)
                else practice.cancel()
                snip.visible = false
            }
        }
    }
}
