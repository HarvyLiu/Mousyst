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
    const entries = (await dictionary).get(data.reading);
    const words = entries ? [...entries].sort((a,b)=>b[1]-a[1]).map(([word])=>word) : [];
    self.postMessage({id:data.id,words});
  } catch { self.postMessage({id:data.id,failed:true}); }
};
