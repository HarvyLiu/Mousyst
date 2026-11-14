import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id:panel
    property var prefs:mousyst.preferences
    signal done()
    signal dragged(real dx,real dy)
    Rectangle {anchors.fill:parent;radius:12;color:'#171719';border.color:'#37373c'}
    component Action:Button {
        id:control
        implicitHeight:36;implicitWidth:Math.max(100,contentItem.implicitWidth+28)
        font.family:'Segoe UI';font.pixelSize:13
        contentItem:Text {text:control.text;font:control.font;color:'#eeeef1';horizontalAlignment:Text.AlignHCenter;verticalAlignment:Text.AlignVCenter}
        background:Rectangle {radius:6;color:control.down?'#41414c':control.hovered?'#34343d':'#29292f';border.color:control.activeFocus?'#8b8b99':'#404048'}
    }
    component Choice:ComboBox {
        id:control;implicitWidth:180;implicitHeight:36;font.family:'Segoe UI';font.pixelSize:13
        background:Rectangle {radius:6;color:control.hovered?'#303038':'#24242a';border.color:control.activeFocus?'#8b8b99':'#404048'}
        contentItem:Text {text:control.displayText;font:control.font;color:'#eeeef1';leftPadding:12;rightPadding:32;verticalAlignment:Text.AlignVCenter}
        indicator:LineIcon {x:control.width-width-10;y:(control.height-height)/2;width:16;height:16;name:'down';ink:'#aaaab5'}
        delegate:ItemDelegate {id:entry;width:control.width-10;implicitHeight:34;highlighted:control.highlightedIndex===index
            contentItem:Text {text:modelData;color:'#eeeef1';font:control.font;verticalAlignment:Text.AlignVCenter;leftPadding:8}
            background:Rectangle {radius:4;color:entry.highlighted?'#3b3b45':'transparent'}
        }
        popup:Popup {y:control.height+5;width:control.width;padding:5
            background:Rectangle {radius:7;color:'#202025';border.color:'#44444e'}
            contentItem:ListView {implicitHeight:Math.min(contentHeight,220);clip:true;model:control.popup.visible?control.delegateModel:null;currentIndex:control.highlightedIndex;ScrollIndicator.vertical:ScrollIndicator{}}
        }
    }
    component Stepper:SpinBox {
        id:control;implicitWidth:148;implicitHeight:36;editable:false
        background:Rectangle {radius:6;color:'#24242a';border.color:'#404048'}
        contentItem:Text {text:control.textFromValue(control.value,control.locale);color:'#eeeef1';font.pixelSize:13;horizontalAlignment:Text.AlignHCenter;verticalAlignment:Text.AlignVCenter}
        up.indicator:Rectangle {x:control.width-width;width:34;height:control.height;radius:6;color:control.up.pressed?'#41414c':'#2d2d35';Text {anchors.centerIn:parent;text:'+';font.pixelSize:19;color:'#d0d0da'}}
        down.indicator:Rectangle {width:34;height:control.height;radius:6;color:control.down.pressed?'#41414c':'#2d2d35';Text {anchors.centerIn:parent;text:'−';font.pixelSize:19;color:'#d0d0da'}}
    }
    component Caption:Label {color:'#bdbdc9';font.family:'Segoe UI';font.pixelSize:13;Layout.fillWidth:true}
    component Section:Label {color:'#828290';font.family:'Segoe UI';font.pixelSize:10;font.letterSpacing:1.8;Layout.topMargin:12}
    component ColorSlider:Slider {
        id:control;from:0;to:1;Layout.fillWidth:true;Layout.minimumWidth:0;implicitWidth:160;implicitHeight:30
        property color trackColor:'#aaaab8'
        background:Rectangle {x:control.leftPadding;y:control.topPadding+control.availableHeight/2-3;width:control.availableWidth;height:6;radius:3;color:'#393942'
            Rectangle {width:control.visualPosition*parent.width;height:6;radius:3;color:control.trackColor}
        }
        handle:Rectangle {x:control.leftPadding+control.visualPosition*(control.availableWidth-width);y:control.topPadding+control.availableHeight/2-height/2;width:18;height:18;radius:9;color:control.pressed?'white':'#eeeef1';border.color:'#777784'}
    }
    Popup {
        id:colorPicker;objectName:'settingsColorPicker';parent:Overlay.overlay;anchors.centerIn:parent
        width:Math.min(440,parent.width-32);padding:22;modal:true;focus:true
        closePolicy:Popup.CloseOnEscape
        property string setting:'accent'
        property color draft:'#eeeeef'
        property real hue:0
        property real saturation:0
        property real brightness:1
        property string hexDraft:'#eeeeef'
        function load(value){
            draft=value;hue=Math.max(0,draft.hsvHue);saturation=draft.hsvSaturation;brightness=draft.hsvValue;hexDraft=draft.toString()
        }
        function choose(name){setting=name;load(prefs[name]);open()}
        function mix(){draft=Qt.hsva(hue,saturation,brightness,1);hexDraft=draft.toString()}
        background:Rectangle {radius:12;color:'#202025';border.color:'#44444e'}
        Overlay.modal:Rectangle {color:'#99000000'}
        contentItem:ColumnLayout {
            spacing:14
            Label {text:colorPicker.setting==='background'?'Background color':'Accent color';color:'#eeeef1';font.family:'Segoe UI';font.pixelSize:19}
            RowLayout {
                spacing:12
                Rectangle {Layout.preferredWidth:58;Layout.preferredHeight:42;radius:6;color:colorPicker.draft;border.color:'#777784'}
                TextField {
                    id:hexInput;objectName:'settingsColorHex';Layout.fillWidth:true;Layout.minimumWidth:0;implicitWidth:160;implicitHeight:42
                    text:colorPicker.hexDraft;maximumLength:7;color:'#eeeef1';font.family:'Segoe UI';font.pixelSize:14;selectByMouse:true
                    validator:RegularExpressionValidator {regularExpression:/#[0-9a-fA-F]{6}/}
                    onTextEdited:{colorPicker.hexDraft=text;if(acceptableInput)colorPicker.load(text)}
                    background:Rectangle {radius:6;color:'#29292f';border.color:hexInput.activeFocus?'#8b8b99':'#404048'}
                    Accessible.name:'Hex color'
                }
            }
            RowLayout {
                spacing:8
                Repeater {
                    model:colorPicker.setting==='background'?['#171719','#202025','#272b32','#182923','#202438','#35232b']:['#eeeeef','#bfe8d5','#a5caff','#c7b6ef','#f0c5a0','#efaeb8']
                    delegate:AbstractButton {
                        required property string modelData
                        objectName:'colorSwatch'+modelData
                        Layout.fillWidth:true;Layout.minimumWidth:0;implicitWidth:30;implicitHeight:30
                        Accessible.name:'Use '+modelData
                        background:Rectangle {radius:5;color:parent.modelData;border.width:parent.activeFocus?2:1;border.color:parent.activeFocus?'white':'#666671'}
                        onClicked:colorPicker.load(modelData)
                    }
                }
            }
            RowLayout {Caption {text:'Hue';Layout.preferredWidth:72;Layout.fillWidth:false}ColorSlider {objectName:'colorHue';value:colorPicker.hue;trackColor:Qt.hsva(colorPicker.hue,1,1,1);onMoved:{colorPicker.hue=value;colorPicker.mix()}Accessible.name:'Hue'}}
            RowLayout {Caption {text:'Saturation';Layout.preferredWidth:72;Layout.fillWidth:false}ColorSlider {objectName:'colorSaturation';value:colorPicker.saturation;onMoved:{colorPicker.saturation=value;colorPicker.mix()}Accessible.name:'Saturation'}}
            RowLayout {Caption {text:'Brightness';Layout.preferredWidth:72;Layout.fillWidth:false}ColorSlider {objectName:'colorBrightness';value:colorPicker.brightness;onMoved:{colorPicker.brightness=value;colorPicker.mix()}Accessible.name:'Brightness'}}
            Label {text:'Changes apply only when you press Apply.';color:'#aaaab5';font.family:'Segoe UI';font.pixelSize:12;Layout.fillWidth:true;Layout.minimumWidth:0;wrapMode:Text.Wrap}
            RowLayout {
                Layout.alignment:Qt.AlignRight
                Action {objectName:'settingsColorCancel';text:'Cancel';onClicked:colorPicker.close()}
                Action {objectName:'settingsColorApply';text:'Apply';enabled:hexInput.acceptableInput;opacity:enabled?1:.4;onClicked:{mousyst.setPreference(colorPicker.setting,colorPicker.hexDraft);colorPicker.close()}}
            }
        }
    }
    ColumnLayout {anchors.fill:parent;anchors.margins:24;spacing:18
        RowLayout {
            Rectangle {width:30;height:30;radius:5;color:'black';Text {anchors.centerIn:parent;text:'M';font.family:'Monotype Corsiva';font.italic:true;font.pixelSize:28;color:'white'}}
            Label {text:'Settings';color:'#eeeef1';font.family:'Segoe UI';font.pixelSize:21}
            MouseArea {Layout.fillWidth:true;Layout.preferredHeight:32;property point origin
                onPressed:mouse=>origin=Qt.point(mouse.x,mouse.y)
                onPositionChanged:mouse=>{if(pressed)panel.dragged(mouse.x-origin.x,mouse.y-origin.y)}
            }
            Action {implicitWidth:32;implicitHeight:32;padding:7;contentItem:LineIcon {name:'close';width:18;height:18}onClicked:panel.done()}
        }
        Rectangle {Layout.fillWidth:true;height:1;color:'#303037'}
        ScrollView {Layout.fillWidth:true;Layout.fillHeight:true;clip:true
            ColumnLayout {width:panel.width-54;spacing:12
                Section {text:'KEYBOARD'}
                RowLayout {Caption {text:'Layout'}Choice {model:['Compact','Standard','Full'];currentIndex:model.indexOf(prefs.layout);onActivated:mousyst.setPreference('layout',currentText)}}
                RowLayout {Caption {text:'Size'}Slider {id:size;from:.65;to:1.6;value:prefs.scale;implicitWidth:140
                    onPressedChanged:if(!pressed)mousyst.setPreference('scale',value)
                    background:Rectangle {x:size.leftPadding;y:size.topPadding+size.availableHeight/2-2;width:size.availableWidth;height:4;radius:2;color:'#393942';Rectangle {width:size.visualPosition*parent.width;height:4;radius:2;color:'#aaaab8'}}
                    handle:Rectangle {x:size.leftPadding+size.visualPosition*(size.availableWidth-width);y:size.topPadding+size.availableHeight/2-height/2;width:16;height:16;radius:8;color:size.pressed?'#ffffff':'#d0d0da';border.color:'#777784'}
                }Label {text:Math.round(prefs.scale*100)+'%';color:'#aaaab5';Layout.preferredWidth:40;horizontalAlignment:Text.AlignRight}}
                RowLayout {Caption {text:'Number panel'}Choice {model:['Rows','Numpad'];currentIndex:model.indexOf(prefs.numberFormat);onActivated:mousyst.setPreference('numberFormat',currentText)}}
                RowLayout {Caption {text:'Colors'}Action {objectName:'settingsBackgroundColor';text:'Background';onClicked:colorPicker.choose('background')}Action {objectName:'settingsAccentColor';text:'Accent';onClicked:colorPicker.choose('accent')}}
                Section {text:'TYPING & POINTER'}
                RowLayout {Caption {text:'Predictive aim · experimental'}Switch {id:aim;checked:prefs.hitboxAssist;onToggled:if(checked!==prefs.hitboxAssist)mousyst.setPreference('hitboxAssist',checked)
                    indicator:Rectangle {implicitWidth:38;implicitHeight:22;radius:11;color:aim.checked?'#bebecb':'#34343d';border.color:'#50505c';Rectangle {x:aim.checked?19:3;y:3;width:16;height:16;radius:8;color:aim.checked?'#25252b':'#a1a1af';Behavior on x {NumberAnimation {duration:90}}}}
                }}
                RowLayout {Caption {text:'Repeat delay · ms'}Stepper {from:200;to:1500;stepSize:50;value:prefs.repeatDelay;onValueModified:mousyst.setPreference('repeatDelay',value)}}
                RowLayout {Caption {text:'Repeat interval · ms'}Stepper {from:25;to:500;stepSize:25;value:prefs.repeatInterval;onValueModified:mousyst.setPreference('repeatInterval',value)}}
                RowLayout {Caption {text:'Caret sensitivity'}Stepper {from:3;to:40;value:prefs.scrubPixels;onValueModified:mousyst.setPreference('scrubPixels',value)}}
                Caption {text:'Drag Space left/right by character or up/down by line.';font.pixelSize:11;color:'#81818f';wrapMode:Text.Wrap}
                RowLayout {Caption {text:'Right-click symbol'}Choice {id:letter;model:'qwertyuiopasdfghjklzxcvbnm'.split('');implicitWidth:74}TextField {text:prefs.symbols[letter.currentText]||'';maximumLength:1;implicitWidth:66;implicitHeight:36;color:'#eeeef1';horizontalAlignment:Text.AlignHCenter;onEditingFinished:if(text.length===1)mousyst.setSymbol(letter.currentText,text);background:Rectangle {radius:6;color:'#24242a';border.color:'#404048'}}}
                Section {text:'CONFIGURATION'}
                RowLayout {Action {text:'Import…';onClicked:mousyst.importSettings()}Action {text:'Export…';onClicked:mousyst.exportSettings()}Action {text:'Reset defaults';onClicked:mousyst.resetSettings()}}
                Caption {text:mousyst.message;font.pixelSize:11;color:'#81818f';wrapMode:Text.Wrap;Layout.topMargin:8}
            }
        }
        Action {text:'Done';Layout.alignment:Qt.AlignRight;onClicked:panel.done()}
    }
}
