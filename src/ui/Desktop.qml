import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Window
import QtQuick.Dialogs

Window {
    id: root
    visible:false
    property bool settingsOpen:false
    property bool numbers:false
    property var prefs:mousyst.preferences
    property real pitch:54*prefs.scale
    width:14*pitch+24
    height:Math.min(body.implicitHeight+20,Screen.desktopAvailableHeight-50)
    color:'transparent'
    title:'Mousyst'
    flags:Qt.Tool|Qt.FramelessWindowHint|Qt.WindowStaysOnTopHint|Qt.WindowDoesNotAcceptFocus
    onClosing:event=>{event.accepted=false;mousyst.hideRequested()}
    onVisibleChanged:if(!visible){board.abort();board.clearVisual();mousyst.cancel()}
    Rectangle {anchors.fill:parent;radius:12;color:prefs.background;border.color:'#37373c'}
    component Key:Button {
        id:key
        Accessible.name:text || value || iconName
        Accessible.role:Accessible.Button
        property string value:text
        property string hint:''
        property string iconName:''
        property bool repeatable:false
        property bool direct:true
        implicitHeight:root.pitch-5;implicitWidth:root.pitch-5;focusPolicy:Qt.NoFocus
        contentItem:Item {
            LineIcon {anchors.centerIn:parent;width:Math.min(22,key.height-8);height:width;name:key.iconName;visible:name!=='';ink:key.checked?'#101012':'#f1f1f3'}
            Text {visible:key.iconName==='';anchors.centerIn:parent;text:key.text;color:key.checked?'#101012':'#f1f1f3';font.family:'Segoe UI';font.pixelSize:Math.max(13,root.pitch*.29)}
            Text {x:3;y:1;text:key.hint;color:'#a2a2ad';font.pixelSize:Math.max(9,root.pitch*.18)}
        }
        background:Rectangle {radius:5;color:key.down?'#55555f':key.checked?prefs.accent:key.hovered?'#36363e':'#29292f';border.color:'#404048'
            Rectangle {anchors.left:parent.left;anchors.right:parent.right;anchors.bottom:parent.bottom;anchors.margins:1;height:2;radius:1;color:'#111114';opacity:.6}
            Behavior on color {ColorAnimation {duration:65}}
        }
        onPressed:if(repeatable)mousyst.hold(value)
        onReleased:{if(!direct)return;let repeated=mousyst.isRepeating;mousyst.releaseHold();if(!repeatable||(!repeated&&['Back','Left','Right','Up','Down'].indexOf(value)<0))mousyst.key(value)}
        onCanceled:mousyst.releaseHold()
    }
    Flickable {
        anchors.fill:parent;contentHeight:body.implicitHeight+20;clip:true
        ColumnLayout {
            id:body;x:12;y:8;width:root.width-24;spacing:5
            RowLayout {
                Layout.fillWidth:true;Layout.preferredHeight:28
                Rectangle {width:27;height:27;radius:5;color:'black';Text {anchors.centerIn:parent;text:'M';font.family:'Monotype Corsiva';font.italic:true;font.pixelSize:25;color:'white'}}
                Label {text:'MOUSYST';font.pixelSize:10;font.letterSpacing:2;color:'#a7a7b2'}
                MouseArea {Layout.fillWidth:true;Layout.preferredHeight:28;property point origin
                    onPressed:mouse=>origin=Qt.point(mouse.x,mouse.y)
                    onPositionChanged:mouse=>{if(pressed){root.x+=mouse.x-origin.x;root.y+=mouse.y-origin.y}}
                    Rectangle {anchors.centerIn:parent;width:36;height:3;radius:2;color:'#55555f'}
                }
                Key {direct:false;text:'';iconName:'settings';implicitHeight:27;implicitWidth:30;onReleased:{mousyst.cancel();root.settingsOpen=true}}
                Key {direct:false;text:'';iconName:'close';implicitHeight:27;implicitWidth:30;onReleased:mousyst.hideRequested()}
            }
            RowLayout {
                id:suggestions;objectName:'desktopSuggestions';Layout.minimumHeight:34;Layout.preferredHeight:34;Layout.maximumHeight:34
                property int candidateIndex:0
                property real wheelDelta:0
                Repeater {model:3;Key {required property int index;direct:false;text:mousyst.suggestions[index]||'';enabled:index<mousyst.suggestions.length;opacity:enabled?1:.25;checked:enabled&&index===suggestions.candidateIndex;Layout.fillWidth:true;implicitHeight:34;onReleased:{suggestions.candidateIndex=index;mousyst.alternative(index)}}}
                Key {text:'';iconName:'undo';direct:false;enabled:mousyst.suggestions.length>0;opacity:enabled?1:.25;implicitHeight:34;onReleased:mousyst.undoWord()}
                MouseArea {anchors.fill:parent;acceptedButtons:Qt.NoButton
                    onWheel:wheel=>{if(mousyst.suggestions.length===0){wheel.accepted=false;return}suggestions.wheelDelta+=wheel.angleDelta.y;if(Math.abs(suggestions.wheelDelta)>=120){suggestions.candidateIndex=Math.max(0,Math.min(mousyst.suggestions.length-1,suggestions.candidateIndex+(suggestions.wheelDelta<0?1:-1)));suggestions.wheelDelta=0;mousyst.alternative(suggestions.candidateIndex)}wheel.accepted=true}
                }
            }
            RowLayout {visible:prefs.layout==='Full';spacing:5;Repeater {model:12;Key {required property int index;text:'F'+(index+1);Layout.fillWidth:true}}}
            RowLayout {visible:prefs.layout!=='Compact';spacing:5;Repeater {model:['1','2','3','4','5','6','7','8','9','0','-','='];Key {required property string modelData;text:modelData;Layout.fillWidth:true;repeatable:true}}}
            Item {
                id:board;objectName:'desktopLetters';visible:!root.numbers;Layout.preferredWidth:14*root.pitch;Layout.preferredHeight:3*root.pitch
                property var path:[]
                property var visualPoints:[]
                function clearVisual(){visualPoints=[];fadeClock.stop();trail.requestPaint()}
                function paintPoint(p){
                    let now=Date.now(), x=(p.x+1)*root.pitch, y=p.y*root.pitch
                    let previous=visualPoints.length?visualPoints[visualPoints.length-1]:null
                    if(previous && Math.hypot(x-previous.x,y-previous.y)<2 && now-previous.t<16)return
                    if(previous){x=previous.x+(x-previous.x)*.65;y=previous.y+(y-previous.y)*.65}
                    visualPoints.push({x:Math.max(0,Math.min(board.width,x)),y:Math.max(0,Math.min(board.height,y)),t:now})
                    visualPoints=visualPoints.slice(-48);fadeClock.start();trail.requestPaint()
                }
                Timer {id:fadeClock;interval:16;repeat:true;onTriggered:{let now=Date.now();board.visualPoints=board.visualPoints.filter(p=>now-p.t<240);trail.requestPaint();if(board.visualPoints.length===0)stop()}}
                property string first:''
                property bool tracking:false
                property bool swiping:false
                function abort(){tracking=false;path=[];mousyst.releaseHold()}
                function letterAt(x,y){for(let k of mousyst.keys)if(x>=k.kx&&x<k.kx+.95&&y>=k.ky&&y<k.ky+.95)return k.letter;return ''}
                Repeater {model:mousyst.keys;Key {required property var modelData;x:(modelData.kx+1)*root.pitch;y:modelData.ky*root.pitch;text:mousyst.shifted?modelData.letter.toUpperCase():modelData.letter;hint:prefs.symbols[modelData.letter]||'';checked:board.tracking&&board.first===modelData.letter;direct:false}}
                Canvas {id:trail;anchors.fill:parent;onPaint:{
                    let c=getContext('2d');c.clearRect(0,0,width,height)
                    let points=board.visualPoints;if(points.length<2)return
                    let now=Date.now();c.strokeStyle=prefs.accent;c.lineCap='round';c.lineJoin='round'
                    for(let i=1;i<points.length;i++){
                        let a=points[i-1],b=points[i],last=i===points.length-1
                        let start=i===1?a:{x:(points[i-2].x+a.x)/2,y:(points[i-2].y+a.y)/2}
                        let end=last?b:{x:(a.x+b.x)/2,y:(a.y+b.y)/2}
                        c.globalAlpha=Math.max(0,1-(now-b.t)/240)*.65
                        c.lineWidth=(2+1.5*i/points.length)*root.pitch/54
                        c.beginPath();c.moveTo(start.x,start.y);c.quadraticCurveTo(a.x,a.y,end.x,end.y);c.stroke()
                    }
                    c.globalAlpha=1
                }}
                MouseArea {
                    anchors.fill:parent;acceptedButtons:Qt.LeftButton|Qt.RightButton;preventStealing:true
                    onPressed:mouse=>{let x=mouse.x/root.pitch-1,y=mouse.y/root.pitch;let exact=board.letterAt(x,y);if(!exact){mouse.accepted=false;return}board.first=mouse.button===Qt.RightButton?exact:mousyst.aim(x,y);board.clearVisual();board.tracking=true;board.swiping=false;board.path=[{x:x,y:y}];if(mouse.button===Qt.LeftButton)mousyst.hold(board.first)}
                    onPositionChanged:mouse=>{if(!board.tracking||!(pressedButtons&Qt.LeftButton))return;if(mouse.x<0||mouse.y<0||mouse.x>=width||mouse.y>=height){board.abort();return}let p={x:mouse.x/root.pitch-1,y:mouse.y/root.pitch};if(!mousyst.isRepeating&&Math.hypot(p.x-board.path[0].x,p.y-board.path[0].y)>1/3&&mousyst.activeModifiers.length===0){board.swiping=true;mousyst.releaseHold()}board.path.push(p);if(board.swiping)board.paintPoint(p)}
                    onReleased:mouse=>{if(!board.tracking)return;let repeated=mousyst.isRepeating;mousyst.releaseHold();if(mouse.x>=0&&mouse.y>=0&&mouse.x<width&&mouse.y<height){if(mouse.button===Qt.RightButton&&board.letterAt(mouse.x/root.pitch-1,mouse.y/root.pitch)===board.first)mousyst.secondary(board.first);else if(mouse.button===Qt.LeftButton&&board.swiping){board.path.push({x:mouse.x/root.pitch-1,y:mouse.y/root.pitch});suggestions.candidateIndex=0;mousyst.stroke(board.path)}else if(mouse.button===Qt.LeftButton&&!repeated)mousyst.key(board.first)}board.abort()}
                    onCanceled:board.abort()
                }
                Key {x:0;y:0;width:root.pitch-5;text:'Esc';value:'Escape'}
                Key {objectName:'desktopBackspace';x:11*root.pitch;y:0;width:3*root.pitch-5;text:'';iconName:'backspace';value:'Back';repeatable:true}
                Key {x:0;y:root.pitch;width:1.5*root.pitch-5;text:'Tab'}
                Key {x:10.5*root.pitch;y:root.pitch;text:';';hint:':'}
                Key {x:11.5*root.pitch;y:root.pitch;text:"'";hint:'"'}
                Key {objectName:'desktopEnter';x:12.5*root.pitch;y:root.pitch;width:1.5*root.pitch-5;text:'';iconName:'enter';value:'Enter'}
                Key {x:0;y:2*root.pitch;width:2.5*root.pitch-5;text:'';iconName:'shift';value:'Shift';checked:mousyst.shifted}
                Repeater {model:[',','.','/'];Key {required property string modelData;required property int index;x:(9.5+index)*root.pitch;y:2*root.pitch;text:modelData;hint:['<','>','?'][index]}}
                Key {x:12.5*root.pitch;y:2*root.pitch;width:1.5*root.pitch-5;text:'';iconName:'shift';value:'Shift';checked:mousyst.shifted}
            }
            Item {
                id:numberBoard;objectName:'desktopNumbers';visible:root.numbers
                Layout.preferredWidth:14*root.pitch;Layout.preferredHeight:3*root.pitch
                property bool pad:prefs.numberFormat==='Numpad'
                Repeater {
                    model:numberBoard.pad?['7','8','9','/','4','5','6','*','1','2','3','-','0','.','=','+']:['1','2','3','4','5','6','7','8','9','0','+','-','*','/','=','(',')','[',']','<','>','!','?','@','#','$','%','&',':',';','"',"'",'\\','_','^']
                    Key {required property string modelData;required property int index;text:modelData;repeatable:true
                        x:(numberBoard.pad?3+index%4*2:index%14)*root.pitch
                        y:(numberBoard.pad?Math.floor(index/4)*.75:Math.floor(index/14))*root.pitch
                        width:(numberBoard.pad?2:1)*root.pitch-5
                        height:(numberBoard.pad?.75:1)*root.pitch-5
                    }
                }
                Key {objectName:'numberFormatToggle';direct:false;x:12*root.pitch;y:2*root.pitch;width:2*root.pitch-5
                    text:numberBoard.pad?'Symbols':'Numpad'
                    onReleased:mousyst.setPreference('numberFormat',numberBoard.pad?'Rows':'Numpad')
                }
            }
            RowLayout {spacing:5
                Key {objectName:'numericLayerToggle';direct:false;text:root.numbers?'ABC':'&123';Layout.preferredWidth:1.4*root.pitch-5;onReleased:{board.abort();board.clearVisual();root.numbers=!root.numbers}}
                Key {text:'Ctrl';checked:mousyst.activeModifiers.indexOf('Ctrl')>=0}
                Key {text:'';iconName:'windows';value:'Win';checked:mousyst.activeModifiers.indexOf('Win')>=0}
                Key {text:'Alt';checked:mousyst.activeModifiers.indexOf('Alt')>=0}
                Key {text:'';value:' ';Layout.fillWidth:true
                    property real startX:0;property real lastX:0;property bool scrubbing:false
                    MouseArea {anchors.fill:parent;preventStealing:true
                        onPressed:mouse=>{parent.startX=mouse.x;parent.lastX=mouse.x;parent.scrubbing=false;scrubDelay.restart()}
                        onPositionChanged:mouse=>{if(!pressed)return;if(Math.abs(mouse.x-parent.startX)>=6)parent.scrubbing=true;if(parent.scrubbing){let step=Math.trunc((mouse.x-parent.lastX)/prefs.scrubPixels);if(step){mousyst.scrub(step);parent.lastX+=step*prefs.scrubPixels}}}
                        onReleased:{scrubDelay.stop();if(!parent.scrubbing)mousyst.key(' ')}onCanceled:scrubDelay.stop()
                    }
                    Timer {id:scrubDelay;interval:250;onTriggered:parent.scrubbing=true}
                    Rectangle {anchors.horizontalCenter:parent.horizontalCenter;anchors.bottom:parent.bottom;anchors.bottomMargin:9;width:30;height:2;color:'#777780';radius:1}
                }
                Key {text:'';iconName:'left';value:'Left';repeatable:true} Key {text:'';iconName:'right';value:'Right';repeatable:true}
                ColumnLayout {spacing:2;Key {text:'';iconName:'up';value:'Up';repeatable:true;implicitHeight:(root.pitch-7)/2}Key {text:'';iconName:'down';value:'Down';repeatable:true;implicitHeight:(root.pitch-7)/2}}
            }
            RowLayout {visible:prefs.layout!=='Compact';spacing:5;Repeater {model:['Home','End','Delete','PageUp','PageDown'];Key {required property string modelData;text:modelData;Layout.fillWidth:true}}}
            Label {text:mousyst.message;color:'#858590';font.pixelSize:10;Layout.fillWidth:true;elide:Text.ElideRight}
        }
    }
    ApplicationWindow {
        id:settingsWindow;objectName:'desktopSettings';visible:root.settingsOpen;width:600;height:Math.min(800,Screen.desktopAvailableHeight-60);color:'transparent';title:'Mousyst settings'
        palette.window:'#171719'
        palette.windowText:'#eeeef1'
        palette.button:'#2c2c33'
        palette.buttonText:'#eeeef1'
        palette.base:'#24242b'
        palette.text:'#eeeef1'
        palette.highlight:'#696979'
        palette.highlightedText:'white'
        onClosing:root.settingsOpen=false
        onVisibleChanged:if(visible)requestActivate()
        flags:Qt.Window|Qt.FramelessWindowHint
        SettingsPanel {anchors.fill:parent;onDone:root.settingsOpen=false;onDragged:(dx,dy)=>{settingsWindow.x+=dx;settingsWindow.y+=dy}}
    }
}
