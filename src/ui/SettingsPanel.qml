import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs

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
    ColorDialog {id:backgroundDialog;selectedColor:prefs.background;onAccepted:mousyst.setPreference('background',selectedColor.toString())}
    ColorDialog {id:accentDialog;selectedColor:prefs.accent;onAccepted:mousyst.setPreference('accent',selectedColor.toString())}
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
                RowLayout {Caption {text:'Colors'}Action {text:'Background';onClicked:backgroundDialog.open()}Action {text:'Accent';onClicked:accentDialog.open()}}
                Section {text:'TYPING & POINTER'}
                RowLayout {Caption {text:'Predictive aim · experimental'}Switch {id:aim;checked:prefs.hitboxAssist;onToggled:if(checked!==prefs.hitboxAssist)mousyst.setPreference('hitboxAssist',checked)
                    indicator:Rectangle {implicitWidth:38;implicitHeight:22;radius:11;color:aim.checked?'#bebecb':'#34343d';border.color:'#50505c';Rectangle {x:aim.checked?19:3;y:3;width:16;height:16;radius:8;color:aim.checked?'#25252b':'#a1a1af';Behavior on x {NumberAnimation {duration:90}}}}
                }}
                RowLayout {Caption {text:'Repeat delay · ms'}Stepper {from:200;to:1500;stepSize:50;value:prefs.repeatDelay;onValueModified:mousyst.setPreference('repeatDelay',value)}}
                RowLayout {Caption {text:'Repeat interval · ms'}Stepper {from:25;to:500;stepSize:25;value:prefs.repeatInterval;onValueModified:mousyst.setPreference('repeatInterval',value)}}
                RowLayout {Caption {text:'Caret sensitivity'}Stepper {from:3;to:40;value:prefs.scrubPixels;onValueModified:mousyst.setPreference('scrubPixels',value)}}
                RowLayout {Caption {text:'Right-click symbol'}Choice {id:letter;model:'qwertyuiopasdfghjklzxcvbnm'.split('');implicitWidth:74}TextField {text:prefs.symbols[letter.currentText]||'';maximumLength:1;implicitWidth:66;implicitHeight:36;color:'#eeeef1';horizontalAlignment:Text.AlignHCenter;onEditingFinished:if(text.length===1)mousyst.setSymbol(letter.currentText,text);background:Rectangle {radius:6;color:'#24242a';border.color:'#404048'}}}
                Section {text:'CONFIGURATION'}
                RowLayout {Action {text:'Import…';onClicked:mousyst.importSettings()}Action {text:'Export…';onClicked:mousyst.exportSettings()}Action {text:'Reset defaults';onClicked:mousyst.resetSettings()}}
                Caption {text:mousyst.message;font.pixelSize:11;color:'#81818f';wrapMode:Text.Wrap;Layout.topMargin:8}
            }
        }
        Action {text:'Done';Layout.alignment:Qt.AlignRight;onClicked:panel.done()}
    }
}
