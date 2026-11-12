import QtQuick

Canvas {
    id: icon
    property string name: ''
    property color ink: '#ececf0'
    implicitWidth:22; implicitHeight:22
    onNameChanged:requestPaint()
    onInkChanged:requestPaint()
    onWidthChanged:requestPaint()
    onHeightChanged:requestPaint()
    onPaint: {
        let c=getContext('2d');c.reset();c.clearRect(0,0,width,height)
        c.scale(width/24,height/24);c.strokeStyle=ink;c.fillStyle=ink;c.lineWidth=1.6;c.lineCap='round';c.lineJoin='round'
        function path(points,close){c.beginPath();c.moveTo(points[0][0],points[0][1]);for(let i=1;i<points.length;i++)c.lineTo(points[i][0],points[i][1]);if(close)c.closePath();c.stroke()}
        if(name==='shift')path([[5,13],[12,5],[19,13],[15,13],[15,20],[9,20],[9,13]],true)
        else if(name==='backspace'){path([[9,5],[21,5],[21,19],[9,19],[3,12]],true);path([[12,9],[17,15]],false);path([[17,9],[12,15]],false)}
        else if(name==='enter'){path([[19,5],[19,13],[5,13]],false);path([[9,9],[5,13],[9,17]],false)}
        else if(name==='close'){path([[6,6],[18,18]],false);path([[18,6],[6,18]],false)}
        else if(name==='windows'){for(let y of [5,13])for(let x of [5,13])c.strokeRect(x,y,6,6)}
        else if(name==='undo'){path([[9,5],[4,9],[9,13]],false);c.beginPath();c.moveTo(4,9);c.lineTo(14,9);c.quadraticCurveTo(20,9,20,15);c.quadraticCurveTo(20,20,12,20);c.stroke()}
        else if(name==='settings'){
            let points=[];for(let i=0;i<32;i++){let a=-Math.PI/2+i*Math.PI/16;let r=(i%4===0||i%4===3)?10:8;points.push([12+Math.cos(a)*r,12+Math.sin(a)*r])}path(points,true);c.beginPath();c.arc(12,12,3,0,Math.PI*2);c.stroke()
        } else if(['left','right','up','down'].indexOf(name)>=0){
            c.translate(12,12);c.rotate(({left:0,right:Math.PI,up:Math.PI/2,down:-Math.PI/2})[name]);path([[3,-6],[-3,0],[3,6]],false)
        }
    }
}
