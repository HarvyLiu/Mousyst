import dictionaryUrl from '../../../src/data/zhuyin.csv?url';

async function loadDictionary() {
  const response = await fetch(dictionaryUrl);
  if (!response.ok) throw new Error('Dictionary unavailable');
  const readings = new Map<string, Map<string,number>>();
  for (const line of (await response.text()).split('\n')) {
    const [word, score, pronunciation] = line.trim().split(',');
    if (!pronunciation || !/^\d+$/.test(score) || /^[ㄅ-ㄩˊˇˋ˙]$/.test(word)) continue;
    const key = pronunciation.replaceAll(' ', '');
    let choices = readings.get(key);
    if (!choices) { choices = new Map(); readings.set(key,choices); }
    choices.set(word,Math.max(choices.get(word) ?? 0, Number(score)));
  }
  return readings;
}
const dictionary = loadDictionary();
dictionary.catch(() => {}); // Each waiting request reports the load failure.
self.onmessage = async ({data}) => {
  try {
    const lexicon=await dictionary;
    const matches=(data.options ?? [data.reading]).filter((key:string)=>lexicon.has(key));
    const words=new Set<string>();
    for (const key of matches) {
      for (const [word] of [...lexicon.get(key)!].sort((a,b)=>b[1]-a[1])) words.add(word);
    }
    self.postMessage({id:data.id,reading:matches[0] ?? data.reading,words:[...words]});
  } catch { self.postMessage({id:data.id,failed:true}); }
};
