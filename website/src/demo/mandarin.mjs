export function makeConverter(csv) {
    const readings=new Map(), buckets=new Map(), syllables=[];
    for(const line of csv.split('\n')){
        const [word,score,pronunciation]=line.trim().split(',');
        if(!pronunciation || !/^\d+$/.test(score) || /^[ㄅ-ㄩˊˇˋ˙]$/.test(word))continue;
        const key=pronunciation.replaceAll(' ','');
        let entries=readings.get(key);
        if(!entries){entries=new Map();readings.set(key,entries);}
        entries.set(word,Math.max(entries.get(word) || 0,Number(score)));
    }
    for(const [key,entries] of readings){
        const ranked=[...entries].sort((a,b)=>b[1]-a[1]);
        readings.set(key,ranked);
        const single=ranked.find(([word])=>[...word].length===1);
        if(single)syllables.push([key,single[1]]);
        if(key.length<2)continue;
        const id=key[0]+key.at(-1);
        if(!buckets.has(id))buckets.set(id,[]);
        buckets.get(id).push([key,ranked[0][1]]);
    }
    const cache=new Map();
    function decode(key){
        if(readings.has(key)){
            const list=readings.get(key),[first,freq]=list[0];
            return {words:list.map(([word])=>word),cost:(15-Math.log1p(freq))/[...first].length};
        }
        if(cache.has(key))return cache.get(key);
        const paths=[[[0,'']]];
        for(let end=1;end<=key.length;end++){
            const best=new Map();
            for(let start=0;start<end;start++){
                if(!paths[start].length)continue;
                const entries=readings.get(key.slice(start,end));
                if(!entries)continue;
                for(const [word,freq] of entries.slice(0,4)){
                    const cost=15-Math.log1p(freq);
                    for(const [prev,prefix] of paths[start]){
                        const phrase=prefix+word, total=prev+cost;
                        if(!best.has(phrase)||total<best.get(phrase))best.set(phrase,total);
                    }
                }
            }
            paths.push([...best].sort((a,b)=>a[1]-b[1] || (a[0]<b[0]?-1:1)).slice(0,12).map(([phrase,cost])=>[cost,phrase]));
        }
        const words=paths[key.length].map(([,word])=>word);
        if(cache.size>=512)cache.delete(cache.keys().next().value);
        const best=paths[key.length][0];
        const result={words,cost:best?best[0]/[...best[1]].length:Infinity};
        cache.set(key,result);
        return result;
    }
    function convert(options){
        const matches=options.map((key,i)=>{
            const {words,cost}=decode(key);
            return [key,words,.45*Math.log1p(i)+cost*.38];
        }).filter(([,words])=>words.length).sort((a,b)=>a[2]-b[2]);
        if(!matches.length)return {reading:options[0],words:[]};
        const words=new Set(matches[0][1].slice(0,2));
        for(const [,items] of matches.slice(0,5))words.add(items[0]);
        for(const [,items] of matches)for(const word of items)words.add(word);
        return {reading:matches[0][0],words:[...words]};
    }
    return {buckets,syllables,compose:key=>decode(key).words,convert};
}
