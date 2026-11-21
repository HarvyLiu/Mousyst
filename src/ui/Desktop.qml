import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Window
import QtQuick.Dialogs
import "zhuyin-trace.mjs" as ZhTrace
import "next-words.mjs" as Predict

Window {
    id: root
    visible:false
    property bool settingsOpen:false
    property bool numbers:false
    property bool zhuyin:false
    property bool allChoices:false
    property string shelf:""
    onSettingsOpenChanged: if (settingsOpen) shelf = ""
    function toggleShelf(name) {
        if (!mousyst.tools.ready()) return
        board.abort()
        board.clearVisual()
        mousyst.cancel()
        shelf = shelf === name ? "" : name
    }
    readonly property point spaceCenter:spaceBar.mapToItem(root.contentItem,spaceBar.width/2,spaceBar.height/2)
    property var prefs:mousyst.preferences
    property real availableKeyboardWidth: Screen.width
    property real pitch:Math.min(54*prefs.scale, (availableKeyboardWidth-24)/14)
    width:14*pitch+24
    height:Math.min(body.implicitHeight+20,Screen.desktopAvailableHeight-50)
    color:'transparent'
    title:'Mousyst'
    flags:Qt.Tool|Qt.FramelessWindowHint|Qt.WindowStaysOnTopHint|Qt.WindowDoesNotAcceptFocus
    onClosing:event=>{event.accepted=false;mousyst.hideRequested()}
    onVisibleChanged:if(!visible){shelf="";board.abort();board.clearVisual();mousyst.cancel()}
    Rectangle {anchors.fill:parent;radius:12;color:prefs.background;border.color:'#37373c'}
    component Key:Button {
        id:key
        Accessible.name: value === ' ' ? 'Space' : text || value || iconName
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
                Key {objectName:"languageToggle";text:root.zhuyin?"EN":"注音"; direct:false;implicitHeight:27;implicitWidth:48
                    onReleased:{if(!mousyst.tools.ready())return;board.abort();mousyst.cancel();root.numbers=false;root.shelf="";root.zhuyin=!root.zhuyin}}
                Repeater {
                    model:[["edit","Edit"],["favorites","Shortcuts"],["phrases","Phrases"]]
                    Key {
                        required property var modelData
                        objectName:"desktopShelf_" + modelData[0]
                        direct:false; text:modelData[1]; checked:root.shelf===modelData[0]
                        implicitHeight:27; implicitWidth:Math.max(42,modelData[1].length*9+12)
                        onReleased:root.toggleShelf(modelData[0])
                    }
                }
                Key {direct:false;text:'';iconName:'settings';implicitHeight:27;implicitWidth:30;onReleased:{root.shelf="";mousyst.cancel();root.settingsOpen=true}}
                Key {direct:false;text:'';iconName:'close';implicitHeight:27;implicitWidth:30;onReleased:mousyst.hideRequested()}
            }
            RowLayout {
                id:suggestions;objectName:'desktopSuggestions';Layout.minimumHeight:34;Layout.preferredHeight:34;Layout.maximumHeight:34
                property bool composing: mousyst.pronunciation.length > 0
                property var choices: composing ? mousyst.readingChoices : mousyst.suggestions
                property int candidateIndex: composing ? mousyst.highlightedReading : mousyst.selectedSuggestion
                readonly property string context: mousyst.predictionContext
                readonly property var nextWords: Predict.nextWords(context,root.zhuyin)
                readonly property bool predicting: !composing && !root.allChoices && nextWords.length>0
                property int page:0
                onCandidateIndexChanged: page=Math.floor(candidateIndex/3)
                Connections {target:mousyst; function onDesktopChanged(){if(suggestions.lastReading!==mousyst.pronunciation){suggestions.lastReading=mousyst.pronunciation;suggestions.page=0}}}
                property string lastReading:""
                property int session:mousyst.suggestionSession
                property real wheelDelta:0
                onSessionChanged:{wheelDelta=0;page=0;root.allChoices=false}
                onChoicesChanged:if(choices.length<=1 || (composing && choices.length<=3))root.allChoices=false
                Repeater {
                    model:3
                    Key {
                        required property int index
                        readonly property int choice:suggestions.page*3+index
                        objectName:'desktopSuggestion'+index
                        direct:false; visible:!mousyst.needsSpelling
                        text:(suggestions.predicting ? suggestions.nextWords[index] : suggestions.choices[choice]) || ''
                        enabled:mousyst.pendingCount===0 && text.length>0
                        opacity:enabled?1:.25
                        checked:enabled && !suggestions.predicting && choice===suggestions.candidateIndex
                        Layout.fillWidth:true; implicitHeight:34
                        onReleased:{
                            if(suggestions.predicting) mousyst.appendPrediction(text,suggestions.context,root.zhuyin)
                            else if(suggestions.composing) mousyst.commitReading(choice)
                            else mousyst.alternative(choice)
                            root.allChoices=false
                        }
                    }
                }
                Key {objectName:"expandSuggestions";text:root.allChoices?"▴":"▾";Accessible.name:"More suggestions";direct:false;visible:suggestions.choices.length>3 || (!suggestions.composing && suggestions.choices.length>1 && suggestions.nextWords.length>0);implicitHeight:34
                    onReleased:root.allChoices=!root.allChoices}
                Key {text:'';iconName:'undo';direct:false;visible:!mousyst.needsSpelling;enabled:mousyst.pendingCount===0 && mousyst.suggestions.length>0;opacity:enabled?1:.25;implicitHeight:34;onReleased:mousyst.undoWord()}
                Key {visible:mousyst.needsSpelling;direct:false;text:mousyst.isSpelling?'Insert word':'Spell word';Layout.fillWidth:true;implicitHeight:34;onReleased:mousyst.isSpelling?mousyst.finishSpelling():mousyst.spellWord()}
                Key {visible:mousyst.needsSpelling;direct:false;text:'Cancel pending';Layout.fillWidth:true;implicitHeight:34;onReleased:mousyst.cancel()}
                MouseArea {anchors.fill:parent;acceptedButtons:Qt.NoButton
                    onWheel:wheel=>{if(suggestions.choices.length===0){suggestions.wheelDelta=0;wheel.accepted=false;return}suggestions.wheelDelta+=wheel.angleDelta.y;let steps=Math.trunc(suggestions.wheelDelta/120);if(steps){suggestions.wheelDelta-=steps*120;mousyst.cycleSuggestion(-steps)}wheel.accepted=true}
                }
            }
            RowLayout {visible:prefs.layout==='Full';spacing:5;Repeater {model:12;Key {required property int index;text:'F'+(index+1);Layout.fillWidth:true}}}
            RowLayout {visible:prefs.layout!=='Compact';spacing:5;Repeater {model:['1','2','3','4','5','6','7','8','9','0','-','='];Key {required property string modelData;text:modelData;Layout.fillWidth:true;repeatable:true}}}
            Item {
                id:board;objectName:'desktopLetters';visible:!root.allChoices&&!root.zhuyin&&!root.numbers&&!root.shelf;Layout.preferredWidth:14*root.pitch;Layout.preferredHeight:3*root.pitch
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
                    onReleased:mouse=>{if(!board.tracking)return;let repeated=mousyst.isRepeating;mousyst.releaseHold();if(mouse.x>=0&&mouse.y>=0&&mouse.x<width&&mouse.y<height){if(mouse.button===Qt.RightButton&&board.letterAt(mouse.x/root.pitch-1,mouse.y/root.pitch)===board.first)mousyst.secondary(board.first);else if(mouse.button===Qt.LeftButton && !repeated){
                            const end={x:mouse.x/root.pitch-1,y:mouse.y/root.pitch}
                            const distance=Math.hypot(end.x-board.path[0].x,end.y-board.path[0].y)
                            if(board.swiping || (distance>1/3 && mousyst.activeModifiers.length===0)){
                                board.path.push(end)
                                mousyst.stroke(board.path)
                            } else mousyst.key(board.first)
                        }}board.abort()}
                    onCanceled:board.abort()
                }
                Key {x:0;y:0;width:root.pitch-5;text:'Esc';value:'Escape'}
                Key {objectName:'desktopBackspace';x:11*root.pitch;y:0;width:3*root.pitch-5;text:'';iconName:'backspace';value:'Back';repeatable:true}
                Key {x:0;y:root.pitch;width:1.5*root.pitch-5;text:'Tab'}
                Key {x:10.5*root.pitch;y:root.pitch;text:mousyst.shifted?':':';';value:';';hint:':'}
                Key {x:11.5*root.pitch;y:root.pitch;text:mousyst.shifted?'"':"'";value:"'";hint:'"'}
                Key {objectName:'desktopEnter';x:12.5*root.pitch;y:root.pitch;width:1.5*root.pitch-5;text:'';iconName:'enter';value:'Enter'}
                Key {x:0;y:2*root.pitch;width:2.5*root.pitch-5;text:'';iconName:'shift';value:'Shift';checked:mousyst.shifted}
                Repeater {model:[',','.','/'];Key {required property string modelData;required property int index;x:(9.5+index)*root.pitch;y:2*root.pitch;text:mousyst.shifted?mousyst.shiftLabel(modelData):modelData;value:modelData;hint:['<','>','?'][index]}}
                Key {x:12.5*root.pitch;y:2*root.pitch;width:1.5*root.pitch-5;text:'';iconName:'shift';value:'Shift';checked:mousyst.shifted}
            }
            Item {
                id:numberBoard;objectName:'desktopNumbers';visible:!root.allChoices&&root.numbers&&!root.shelf
                Layout.preferredWidth:14*root.pitch;Layout.preferredHeight:3*root.pitch
                property bool pad:prefs.numberFormat==='Numpad'
                Repeater {
                    model:numberBoard.pad?['7','8','9','/','4','5','6','*','1','2','3','-','0','.','=','+']:['1','2','3','4','5','6','7','8','9','0','+','-','*','/','=','(',')','[',']','<','>','!','?','@','#','$','%','&',':',';','"',"'",'\\','_','^']
                    Key {required property string modelData;required property int index;text:mousyst.shifted?mousyst.shiftLabel(modelData):modelData;value:modelData;repeatable:true
                        x:(numberBoard.pad?1+index%4*2:index%12)*root.pitch
                        y:(numberBoard.pad?Math.floor(index/4)*.75:Math.floor(index/12))*root.pitch
                        width:(numberBoard.pad?2:1)*root.pitch-5
                        height:(numberBoard.pad?.75:1)*root.pitch-5
                    }
                }
                Key {x:12*root.pitch;y:0;width:2*root.pitch-5;text:'';iconName:'backspace';value:'Back';repeatable:true}
                Key {x:12*root.pitch;y:root.pitch;width:2*root.pitch-5;text:'';iconName:'enter';value:'Enter'}
                Key {x:12*root.pitch;y:2*root.pitch;width:2*root.pitch-5;text:'Esc';value:'Escape'}
                Key {x:9*root.pitch;y:2*root.pitch;width:root.pitch-5;text:'';iconName:'shift';value:'Shift';checked:mousyst.shifted;visible:numberBoard.pad}
                Key {objectName:'numberFormatToggle';direct:false;x:(numberBoard.pad?10:11)*root.pitch;y:2*root.pitch;width:(numberBoard.pad?2:1)*root.pitch-5
                    text:numberBoard.pad?'Symbols':'Pad'
                    onReleased:mousyst.setPreference('numberFormat',numberBoard.pad?'Rows':'Numpad')
                }
            }
            Item {
                id:phoneticBoard;objectName:"phoneticBoard";visible:!root.allChoices&&root.zhuyin&&!root.numbers&&!root.shelf
                Layout.preferredWidth:14*root.pitch;Layout.preferredHeight:3*root.pitch
                ColumnLayout {
                    anchors.fill:parent;spacing:2
                    Repeater {id:zhRows;model:mousyst.phoneticRows
                        RowLayout {id:soundRow;required property string modelData;Layout.fillWidth:true;spacing:3
                            property alias keys:sounds
                            Repeater {id:sounds;model:soundRow.modelData.split("")
                                Key {required property string modelData;text:modelData;direct:false;Layout.fillWidth:true;Layout.preferredHeight:root.pitch*.67;onReleased:mousyst.phonetic(modelData)}
                            }
                        }
                    }
                }
                Canvas {id:zhTrail;anchors.fill:parent
                    onPaint:{const c=getContext("2d");c.clearRect(0,0,width,height);c.lineWidth=3;c.lineJoin="round";c.lineCap="round";c.strokeStyle=root.prefs.accent;c.beginPath()
                        const path=zhPointer.points;for(let i=Math.max(0,path.length-32);i<path.length;i++){let x=path[i][0]*width/11,y=path[i][1]*height/4;if(i===Math.max(0,path.length-32))c.moveTo(x,y);else c.lineTo(x,y)}c.stroke()}
                }
                MouseArea {id:zhPointer;anchors.fill:parent;preventStealing:true
                    property var points:[];property var centers:({});property string first:"";property bool dragged:false
                    property var cachedSyllables:null
                    property var buckets:new Map()
                    function lookup(pairs){
                        let entries=[]
                        for(const pair of pairs){
                            if(!buckets.has(pair)){
                                if(buckets.size>=24)buckets.delete(buckets.keys().next().value)
                                buckets.set(pair,mousyst.swipeReadings([pair]))
                            }
                            entries=entries.concat(buckets.get(pair))
                        }
                        return entries
                    }
                    function submit(suffixes){
                        if(!suffixes.length)return
                        let alternatives=[]
                        if(mousyst.readingStartedWithSwipe){
                            const options=suffixes.slice(0,4).map(s=>mousyst.pronunciation+s)
                            alternatives=ZhTrace.contextualStarts(options,centers,cachedSyllables,pairs=>lookup(pairs))
                        }
                        mousyst.phoneticTrace(suffixes,alternatives)
                    }
                    function reset(){first="";points=[];dragged=false;zhTrail.requestPaint()}
                    function point(x,y){return [11*x/width,4*y/height]}
                    function record(x,y){let p=point(x,y);if(Math.hypot(p[0]-points[0][0],p[1]-points[0][1])>0.33)dragged=true
                        let last=points[points.length-1];if(Math.hypot(last[0]-p[0],last[1]-p[1])>.035){points.push(p);zhTrail.requestPaint()}}
                    onPressed:mouse=>{reset();if(!mousyst.beginPhoneticGesture())return;let map={};for(let r=0;r<zhRows.count;r++){let row=zhRows.itemAt(r)
                        for(let k=0;k<row.keys.count;k++){let key=row.keys.itemAt(k);let pos=key.mapToItem(zhPointer,0,0)
                            map[key.text]=point(pos.x+key.width/2,pos.y+key.height/2)
                            if(mouse.x>=pos.x&&mouse.x<pos.x+key.width&&mouse.y>=pos.y&&mouse.y<pos.y+key.height)first=key.text}}
                        centers=map;points=[point(mouse.x,mouse.y)]}
                    onPositionChanged:mouse=>{if(pressed&&first)record(mouse.x,mouse.y)}
                    onReleased:mouse=>{if(first&&mouse.x>=0&&mouse.x<width&&mouse.y>=0&&mouse.y<height){
                        record(mouse.x,mouse.y);if(dragged){
                            const guesses=ZhTrace.traceReadings(points,centers)
                            if(!cachedSyllables)cachedSyllables=mousyst.swipeSyllables()
                            const bucket=lookup(ZhTrace.endpointPairs(points,centers))
                            submit(ZhTrace.matchSwipe(points,centers,bucket,guesses,cachedSyllables,pairs=>lookup(pairs)))
                        }else if(mousyst.readingStartedWithSwipe)submit([first]);else mousyst.releasePhoneticTap(first)}reset()}
                    onCanceled:reset()
                    onVisibleChanged:if(!visible)reset()
                }
            }
            GridView {
                objectName:"candidateGrid";visible:root.allChoices; Layout.preferredWidth:14*root.pitch;Layout.preferredHeight:3*root.pitch
                cellWidth:width/4;cellHeight:root.pitch*.68;clip:true
                model:root.allChoices?suggestions.choices:[]
                delegate:Item {id:choiceTile;required property string modelData;required property int index
                    width:GridView.view.cellWidth;height:GridView.view.cellHeight
                    Key {anchors.fill:parent;anchors.margins:2;text:choiceTile.modelData;direct:false;checked:suggestions.candidateIndex===choiceTile.index
                        onReleased:{const selected=choiceTile.index;if(suggestions.composing)mousyst.commitReading(selected);else mousyst.alternative(selected);root.allChoices=false}}
                }
                ScrollBar.vertical:ScrollBar{}
            }
            ShelfPanel {
                objectName:"desktopShelfPanel"; visible:root.shelf!==""
                section:root.shelf; pitch:root.pitch
                onManageRequested: kind => { mousyst.cancel(); root.settingsOpen=true; settingsPanel.manage(kind) }
                Layout.preferredWidth:14*root.pitch; Layout.preferredHeight:3*root.pitch
            }
            RowLayout {spacing:5
                Key {objectName:'numericLayerToggle';direct:false;text:root.numbers||root.shelf?(root.zhuyin?'注音':'ABC'):'&123';Layout.preferredWidth:1.4*root.pitch-5;onReleased:{root.allChoices=false;if(mousyst.pronunciation)mousyst.cancel();board.abort();board.clearVisual();root.numbers=root.shelf?false:!root.numbers;root.shelf=""}}
                Key {visible:root.zhuyin&&!root.numbers&&!root.shelf;text:'';iconName:'backspace';value:'Back';repeatable:true}
                Key {text:'Ctrl';checked:mousyst.activeModifiers.indexOf('Ctrl')>=0}
                Key {text:'';iconName:'windows';value:'Win';checked:mousyst.activeModifiers.indexOf('Win')>=0}
                Key {text:'Alt';checked:mousyst.activeModifiers.indexOf('Alt')>=0}
                Key {id:spaceBar;objectName:'desktopSpace';text:'';value:' ';Layout.fillWidth:true
                    property real startX:0;property real startY:0;property real lastX:0;property real lastY:0;property bool scrubbing:false
                    MouseArea {anchors.fill:parent;preventStealing:true
                        onPressed:mouse=>{parent.startX=mouse.x;parent.startY=mouse.y;parent.lastX=mouse.x;parent.lastY=mouse.y;parent.scrubbing=false;scrubDelay.restart()}
                        onPositionChanged:mouse=>{
                            if(!pressed)return
                            if(Math.hypot(mouse.x-parent.startX,mouse.y-parent.startY)>=6)parent.scrubbing=true
                            if(!parent.scrubbing)return
                            let dx=(mouse.x-parent.lastX)/prefs.scrubPixels
                            let verticalStep=Math.max(18,prefs.scrubPixels*3)
                            let dy=(mouse.y-parent.lastY)/verticalStep
                            if(Math.abs(dy)>=1&&Math.abs(dy)>Math.abs(dx)){
                                let step=Math.trunc(dy);mousyst.scrubVertical(step);parent.lastY+=step*verticalStep;parent.lastX=mouse.x
                            }else if(Math.abs(dx)>=1){
                                let step=Math.trunc(dx);mousyst.scrub(step);parent.lastX+=step*prefs.scrubPixels;parent.lastY=mouse.y
                            }
                        }
                        onReleased:{scrubDelay.stop();if(!parent.scrubbing)mousyst.key(' ')}onCanceled:scrubDelay.stop()
                    }
                    Timer {id:scrubDelay;interval:250;onTriggered:parent.scrubbing=true}
                    Rectangle {anchors.horizontalCenter:parent.horizontalCenter;anchors.bottom:parent.bottom;anchors.bottomMargin:9;width:30;height:2;color:'#777780';radius:1}
                }
                Key {text:'';iconName:'left';value:'Left';repeatable:true} Key {text:'';iconName:'right';value:'Right';repeatable:true}
                ColumnLayout {spacing:2;Key {text:'';iconName:'up';value:'Up';repeatable:true;implicitHeight:(root.pitch-7)/2}Key {text:'';iconName:'down';value:'Down';repeatable:true;implicitHeight:(root.pitch-7)/2}}
            }
            RowLayout {visible:prefs.layout!=='Compact';spacing:5;Repeater {model:['Home','End','Delete','PageUp','PageDown'];Key {required property string modelData;text:modelData;Layout.fillWidth:true}}}
            Label {text:(mousyst.pronunciation ? mousyst.pronunciation+'   ' : '')+(mousyst.pendingCount ? mousyst.pendingCount+' pending · ' : '')+mousyst.message;color:mousyst.pronunciation?prefs.accent:'#858590';font.pixelSize:root.zhuyin?15:10;Layout.fillWidth:true;elide:Text.ElideRight}
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
        SettingsPanel {id:settingsPanel;anchors.fill:parent;onDone:root.settingsOpen=false;onDragged:(dx,dy)=>{settingsWindow.x+=dx;settingsWindow.y+=dy}}
    }
}
