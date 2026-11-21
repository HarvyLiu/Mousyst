// Coordinates are measured in key widths and row heights on the rendered board.
function segment(point, start, end) {
    const dx=end[0]-start[0], dy=end[1]-start[1];
    const t=Math.max(0,Math.min(1,((point[0]-start[0])*dx+(point[1]-start[1])*dy)/(dx*dx+dy*dy || 1)));
    return [t,Math.hypot(point[0]-start[0]-t*dx,point[1]-start[1]-t*dy)];
}

function corners(points, first, last, output) {
    let farthest=0.40, pivot=-1;
    for (let i=first+1;i<last;i++) {
        const distance=segment(points[i],points[first],points[last])[1];
        if (distance>farthest) {farthest=distance;pivot=i;}
    }
    if (pivot<0) {output.push(points[last]);return;}
    corners(points,first,pivot,output);
    corners(points,pivot,last,output);
}

export function traceReadings(points, centers) {
    if (points.length<2) return [];
    const vertices=[points[0]];
    corners(points,0,points.length-1,vertices);
    const symbols=Object.keys(centers);
    const nearest=point=>symbols.reduce((best,key)=>
        Math.hypot(point[0]-centers[key][0],point[1]-centers[key][1]) <
        Math.hypot(point[0]-centers[best][0],point[1]-centers[best][1]) ? key : best);
    const keys=vertices.map(nearest).filter((key,i,list)=>i===0 || key!==list[i-1]);
    if (keys.length<2 || keys.length>24) return [];
    let options=[keys[0]];
    for (let i=1;i<keys.length;i++) {
        const from=keys[i-1],to=keys[i];
        const along=symbols.map(key=>[key,segment(centers[key],centers[from],centers[to])])
            .filter(item=>item[0]!==from && item[0]!==to && item[1][0]>0 && item[1][0]<1 && item[1][1]<0.32)
            .sort((a,b)=>a[1][0]-b[1][0]);
        // Turning points are intentional. Straight-through symbols are ambiguous.
        for (const item of along) {
            options=options.concat(options.map(prefix=>prefix+item[0]))
                .sort((a,b)=>a.length-b.length).slice(0,128);
        }
        options=options.map(prefix=>prefix+to);
    }
    return options;
}
