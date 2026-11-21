import dictionaryUrl from '../../../src/data/zhuyin.csv?url';
import {makeConverter} from './mandarin.mjs';
import {endpointPairs,matchSwipe} from '../../../src/ui/zhuyin-trace.mjs';

async function loadDictionary() {
  const response=await fetch(dictionaryUrl);
  if(!response.ok)throw new Error('Dictionary unavailable');
  return makeConverter(await response.text());
}
const dictionary=loadDictionary();
dictionary.catch(()=>{});
let previous={id:-1,reading:""};
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
    if(data.gesture){
      const {points,centers,suffixes}=data.gesture;
      const lookup=(pairs:string[])=>pairs.flatMap(id=>decoder.buckets.get(id) ?? []);
      const bucket=lookup(endpointPairs(points,centers));
      const ranked=matchSwipe(points,centers,bucket,suffixes,decoder.syllables,lookup)
        .map((suffix:string)=>base+suffix).filter((key:string)=>key.length<=60);
      if(ranked.length)options=ranked;
    }
    const result=decoder.convert(options.filter((key:string)=>key.length<=60));
    previous={id:data.id,reading:result.reading ?? base};
    self.postMessage({id:data.id,...result});
  } catch {self.postMessage({id:data.id,failed:true});}
};
