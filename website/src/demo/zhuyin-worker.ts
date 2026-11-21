import dictionaryUrl from '../../../src/data/zhuyin.csv?url';
import {makeConverter} from './mandarin.mjs';
import {contextualStarts,endpointPairs,matchSwipe} from '../../../src/ui/zhuyin-trace.mjs';

async function loadDictionary() {
  const response=await fetch(dictionaryUrl);
  if(!response.ok)throw new Error('Dictionary unavailable');
  return makeConverter(await response.text());
}
const dictionary=loadDictionary();
dictionary.catch(()=>{});
let previous={id:-1,reading:"",startCenters:null as Record<string,number[]>|null};
self.onmessage=async ({data})=>{
  try {
    const decoder=await dictionary;
    let options=data.options ?? [data.reading];
    const base=previous.id===data.id-1 ? previous.reading : data.previousReading;
    if(!data.gesture && data.reading.startsWith(data.previousReading)){
      options=[base+data.reading.slice(data.previousReading.length)];
    }else if(!data.gesture && data.reading===data.previousReading.slice(0,-1)){
      options=[base.slice(0,-1)];
    }
    const lookup=(pairs:string[])=>pairs.flatMap(id=>decoder.buckets.get(id) ?? []);
    const startCenters=base && previous.id===data.id-1 ? previous.startCenters : data.gesture?.centers ?? null;
    if(data.gesture){
      const {points,centers,suffixes}=data.gesture;
      const bucket=lookup(endpointPairs(points,centers));
      const ranked=matchSwipe(points,centers,bucket,suffixes,decoder.syllables,lookup)
        .map((suffix:string)=>base+suffix).filter((key:string)=>key.length<=60);
      if(ranked.length)options=ranked;
    }
    options=options.filter((key:string)=>key.length<=60);
    const result=decoder.convert(options);
    if(base && startCenters && options.length && data.reading.length>=data.previousReading.length){
      const variants=contextualStarts(options,startCenters,decoder.syllables,lookup).filter((s:string)=>s.length<=60);
      if(variants.length)result.words=decoder.convert([...new Set([options[0],...variants,...options])]).words;
    }
    previous={id:data.id,reading:result.reading ?? base,startCenters};
    self.postMessage({id:data.id,...result});
  } catch {self.postMessage({id:data.id,failed:true});}
};
