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

// Shape matching uses the full pointer path, including the parts between turns.
function profile(points, count) {
    const lengths=[0];
    for(let i=1;i<points.length;i++) {
        lengths.push(lengths[i-1]+Math.hypot(points[i][0]-points[i-1][0],points[i][1]-points[i-1][1]));
    }
    const length=lengths[lengths.length-1], samples=[];
    let j=1;
    for(let i=0;i<count;i++){
        const at=length*i/(count-1);
        while(j<points.length-1 && lengths[j]<at)j++;
        const t=(at-lengths[j-1])/(lengths[j]-lengths[j-1] || 1);
        samples.push(points[j-1][0]+t*(points[j][0]-points[j-1][0]),points[j-1][1]+t*(points[j][1]-points[j-1][1]));
    }
    return {length,samples};
}

function nearKeys(p,centers){
    const ordered=Object.keys(centers).map(k=>[k,Math.hypot(p[0]-centers[k][0],p[1]-centers[k][1])]).sort((a,b)=>a[1]-b[1]);
    return ordered.slice(0,2).filter(pair=>pair[1]<=ordered[0][1]+.48).map(pair=>pair[0]);
}
export function endpointPairs(points,centers){
    const pairs=[];
    for(const a of nearKeys(points[0],centers))
        for(const b of nearKeys(points[points.length-1],centers))pairs.push(a+b);
    return pairs;
}
let syllableIndex;
function sentenceTraces(points,centers,syllables){
    if(!syllableIndex){
        syllableIndex=new Map();
        for(const entry of syllables){
            const key=entry[0],id=key[0]+key[key.length-1];
            if(!syllableIndex.has(id))syllableIndex.set(id,[]);
            syllableIndex.get(id).push(entry);
        }
    }
    const turns=[points[0]];
    corners(points,0,points.length-1,turns);
    if(turns.length>48)return [];
    const nearby=turns.map(p=>nearKeys(p,centers));
    const beam=[[{reading:'',cost:0}]];
    for(let end=0;end<turns.length;end++){
        const candidates=new Map();
        for(let start=Math.max(0,end-4);start<=end;start++){
            if(!beam[start].length)continue;
            const observed=start===end?null:profile(turns.slice(start,end+1),12);
            for(const a of nearby[start])for(const b of nearby[end]){
                for(const [key,freq] of syllableIndex.get(a+b)||[]){
                    if((key.length===1)!==(start===end))continue;
                    let error=0;
                    if(!observed){
                        error=Math.hypot(turns[end][0]-centers[a][0],turns[end][1]-centers[a][1]);
                    }else{
                        const target=profile(key.split('').map(k=>centers[k]),12);
                        if(Math.abs(target.length-observed.length)>2)continue;
                        for(let i=0;i<24;i+=2)error+=Math.hypot(target.samples[i]-observed.samples[i],target.samples[i+1]-observed.samples[i+1]);
                        error=error/12+.05*Math.abs(target.length-observed.length);
                    }
                    if(error>.92)continue;
                    const cost=error*(end-start+1)+.46-.024*Math.log(1+freq);
                    for(const prev of beam[start]){
                        const reading=prev.reading+key,total=prev.cost+cost;
                        if(!candidates.has(reading)||total<candidates.get(reading))candidates.set(reading,total);
                    }
                }
            }
        }
        beam.push(Array.from(candidates,([reading,cost])=>({reading,cost})).sort((a,b)=>a.cost-b.cost).slice(0,20));
    }
    return beam[turns.length];
}
function shapeScore(observed,centers,reading,frequency,penalty){
    const count=observed.samples.length/2;
    if(reading.length<2)return;
    const path=[];
    let length=0;
    for(let i=0;i<reading.length;i++){
        const point=centers[reading[i]];
        if(!point)return;
        if(i)length+=Math.hypot(point[0]-path[i-1][0],point[1]-path[i-1][1]);
        path.push(point);
    }
    if(Math.abs(length-observed.length)>Math.max(2.5,observed.length*.38))return;
    const template=profile(path,count).samples;
    let error=0;
    for(let i=0;i<template.length;i+=2)error+=Math.hypot(template[i]-observed.samples[i],template[i+1]-observed.samples[i+1]);
    error/=count;
    if(error>1.05)return;
    return error+.025*Math.abs(length-observed.length)-Math.log(1+frequency)*.018+penalty;

}

// Align turns in order. A missed collinear key is inexpensive; skipping a
// deliberate reversal is strong evidence against an otherwise similar shape.
function turnError(turns,path){
    function skip(points,i){
        if(i===0||i===points.length-1)return 3;
        return .08+Math.min(2,segment(points[i],points[i-1],points[i+1])[1]);
    }
    let previous=[0];
    for(let j=0;j<path.length;j++)previous.push(previous[j]+skip(path,j));
    for(let i=0;i<turns.length;i++){
        const row=[previous[0]+skip(turns,i)];
        for(let j=0;j<path.length;j++){
            const distance=Math.hypot(turns[i][0]-path[j][0],turns[i][1]-path[j][1]);
            row.push(Math.min(previous[j]+distance,previous[j+1]+skip(turns,i),row[j]+skip(path,j)));
        }
        previous=row;
    }
    return previous[path.length]/turns.length;
}

function wordMatches(path,centers,lookup){
    const observed=profile(path,16), words=[];
    for(const [reading,frequency] of lookup(endpointPairs(path,centers))){
        const score=shapeScore(observed,centers,reading,frequency,0);
        if(score!==undefined)words.push([reading,score,frequency]);
    }
    return words.sort((a,b)=>a[1]-b[1]).slice(0,4);
}

function matchPath(points,centers,entries,guesses,syllables,lookup) {
    if(points.length<2)return [];
    const count=24, observed=profile(points,count);
    const scores=new Map();
    function evaluate(reading,frequency,penalty){
        const score=shapeScore(observed,centers,reading,frequency,penalty);
        if(score!==undefined && (!scores.has(reading)||score<scores.get(reading)))scores.set(reading,score);
    }
    for(const reading of guesses)evaluate(reading,0,.15);
    const sentences=sentenceTraces(points,centers,syllables);
    for(const candidate of sentences)evaluate(candidate.reading,0,.018*candidate.cost);
    // A syllable can start on a straight section immediately after a tone.
    // Recover the unseen first symbol and let the language decoder compare it.
    for(const candidate of sentences.slice(0,8)){
        const reading=candidate.reading;
        for(let i=1;i<reading.length;i++){
            if(!'ˇˋˊ˙'.includes(reading[i-1]))continue;
            for(const k of Object.keys(centers)){
                const hit=segment(centers[k],centers[reading[i-1]],centers[reading[i]]);
                if(hit[0]>.05 && hit[0]<.95 && hit[1]<.55)
                    evaluate(reading.slice(0,i)+k+reading.slice(i),0,.02*candidate.cost+.008);
            }
        }
    }
    for(const entry of entries)evaluate(entry[0],entry[1],0);
    // Match both sides of likely word boundaries. This also recovers whole
    // phrases when an intermediate sound falls on a straight part of the path.
    if(lookup){
        const turns=[points[0]];
        corners(points,0,points.length-1,turns);
        if(turns.length>=8 && turns.length<=32){
            let splits=[];
            for(let i=2;i<turns.length-2;i++){
                const keys=nearKeys(turns[i],centers);
                if(keys.some(k=>'ˊˇˋ˙'.includes(k)))splits.push(i);
            }
            splits=splits.sort((a,b)=>Math.abs(a-turns.length/2)-Math.abs(b-turns.length/2)).slice(0,4);
            for(const i of splits){
                const left=wordMatches(turns.slice(0,i+1),centers,lookup);
                if(!left.length)continue;
                const right=wordMatches(turns.slice(i+1),centers,lookup);
                for(const a of left)for(const b of right)
                    evaluate(a[0]+b[0],Math.sqrt(a[2]*b[2]),.035);
            }
        }
    }
    const turns=[points[0]];
    corners(points,0,points.length-1,turns);
    const ranked=Array.from(scores.keys()).sort((a,b)=>scores.get(a)-scores.get(b)).slice(0,100);
    for(const key of ranked){
        scores.set(key,scores.get(key)+1.4*turnError(turns,key.split('').map(k=>centers[k])));
    }
    ranked.sort((a,b)=>scores.get(a)-scores.get(b));
    if(!ranked.length)return guesses.slice(0,12);
    const best=scores.get(ranked[0]);
    return ranked.filter(k=>scores.get(k)<=best+.55).slice(0,96);
}


// Fast drags often cut inside a turn. Estimate the intended vertices using a
// bounded inverse of the same corner-rounding model used to verify candidates.
function restoreTurns(turns,amount){
    let estimate=turns;
    for(let pass=0;pass<4;pass++){
        estimate=turns.map((p,i)=>{
            if(i===0||i===turns.length-1)return p;
            const dx=amount/(1-amount)*(p[0]-(estimate[i-1][0]+estimate[i+1][0])/2);
            const dy=amount/(1-amount)*(p[1]-(estimate[i-1][1]+estimate[i+1][1])/2);
            const limit=Math.max(1,Math.hypot(dx,dy)/1.85);
            return [p[0]+dx/limit,p[1]+dy/limit];
        });
    }
    return estimate;
}

// An undershot vowel and a skipped tone can still sound like a legal syllable.
// Recover alternatives only when the following sounds form a frequent dictionary word.
export function contextualStarts(options,centers,syllables,lookup){
    if(!options.length)return [];
    const tones='ˊˇˋ˙';
    const stripTone=s=>tones.includes(s[s.length-1])?s.slice(0,-1):s;
    const phraseCache=new Map(), alternatives=new Map();
    function frequency(key){
        const id=key[0]+key[key.length-1];
        if(!phraseCache.has(id))phraseCache.set(id,new Map(lookup([id])));
        return phraseCache.get(id).get(key)||0;
    }
    for(const reading of options.slice(0,4)){
        const prefix=syllables.filter(([s])=>reading.startsWith(s)).sort((a,b)=>b[0].length-a[0].length)[0];
        if(!prefix)continue;
        const tail=reading.slice(prefix[0].length);
        const next=syllables.filter(([s])=>tail.startsWith(s)).sort((a,b)=>b[0].length-a[0].length)[0];
        if(!next)continue;
        const base=stripTone(prefix[0]);
        if(base.length<2)continue;
        const evidence=frequency(prefix[0]+next[0]);
        for(const [key,prior] of syllables){
            const alt=stripTone(key);
            if(key===prefix[0] || alt.length!==base.length || alt.slice(0,-1)!==base.slice(0,-1))continue;
            const a=centers[base[base.length-1]], b=centers[alt[alt.length-1]];
            const distance=Math.hypot(a[0]-b[0],a[1]-b[1]);
            if(distance>1.55)continue;
            const freq=frequency(key+next[0]);
            if(freq<Math.max(250,evidence*5))continue;
            const score=Math.log(1+freq)+.16*Math.log(1+prior)-distance;
            const result=key+tail;
            if(!alternatives.has(result)||score>alternatives.get(result))alternatives.set(result,score);
        }
    }
    return Array.from(alternatives.keys()).sort((a,b)=>alternatives.get(b)-alternatives.get(a)).slice(0,4);
}

export function matchSwipe(points,centers,entries,guesses,syllables,lookup){
    const original=matchPath(points,centers,entries,guesses,syllables,lookup);
    if(points.length<3 || !lookup)return original;
    const turns=[points[0]];
    corners(points,0,points.length-1,turns);
    if(turns.length<3 || turns.length>32)return original;
    const symbols=Object.keys(centers);
    const drift=turns.reduce((sum,p)=>sum+Math.min(...symbols.map(k=>Math.hypot(p[0]-centers[k][0],p[1]-centers[k][1]))),0)/turns.length;
    const known=new Set(entries.map(entry=>entry[0]));

    const context=options=>contextualStarts(options,centers,syllables,lookup);
    if(known.has(original[0]) && turnError(turns,original[0].split('').map(k=>centers[k]))<.52)
        return original;
    if(drift<.17 && original.length)
        return Array.from(new Set(original.slice(0,1).concat(context(original),original)));
    const observed=profile(points,24);
    const candidates=new Map();
    const frequencies=new Map(entries);
    const shapeCosts=new Map();
    function collect(readings){
        for(let i=0;i<Math.min(32,readings.length);i++){
            const key=readings[i];
            const prior=.055*Math.log(1+i)-.024*Math.log(1+(frequencies.get(key)||0));
            if(shapeCosts.has(key)){
                candidates.set(key,Math.min(candidates.get(key),shapeCosts.get(key)+prior));
                continue;
            }
            const path=key.split('').map(k=>centers[k]);
            if(path.length<2)continue;
            let best=Infinity;
            for(const bend of [0,.12,.22,.32]){
                const rounded=path.map((p,j)=>j===0||j===path.length-1?p:[
                    p[0]*(1-bend)+bend*(path[j-1][0]+path[j+1][0])/2,
                    p[1]*(1-bend)+bend*(path[j-1][1]+path[j+1][1])/2]);
                const template=profile(rounded,24);
                let error=0;
                for(let j=0;j<48;j+=2)error+=Math.hypot(observed.samples[j]-template.samples[j],observed.samples[j+1]-template.samples[j+1]);
                const score=error/24+turnError(turns,rounded)+.02*Math.abs(observed.length-template.length)+.48*bend;
                best=Math.min(best,score);
            }
            shapeCosts.set(key,best);
            candidates.set(key,best+prior);
        }
    }
    collect(original);
    for(const bend of [.17,.3]){
        const restored=restoreTurns(turns,bend);
        collect(matchPath(restored,centers,entries,traceReadings(restored,centers),syllables,lookup));
    }
    const ranked=Array.from(candidates.keys()).sort((a,b)=>candidates.get(a)-candidates.get(b));
    if(original.length && candidates.has(original[0]) && (known.has(original[0]) || known.has(original[1])) && candidates.get(original[0])-candidates.get(ranked[0])<.48)
        return Array.from(new Set(original.concat(ranked))).slice(0,96);
    const suggestions=context(ranked);
    return Array.from(new Set(ranked.slice(0,1).concat(suggestions,ranked))).slice(0,96);
}
