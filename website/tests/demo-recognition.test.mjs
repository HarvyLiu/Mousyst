import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import { keyCenters, makeRecognizer } from '../src/demo/recognizer.mjs';

const read = path => readFileSync(new URL(path, import.meta.url), 'utf8');
const data = read('../src/demo/vocabulary.json');
const recognize = makeRecognizer(JSON.parse(data).words);
const stroke = letters => [...letters].map(letter => keyCenters[letter]);

test('the standalone website uses the desktop frequency list and bundled notices', () => {
  assert.equal(data, read('../../src/data/vocabulary.json'));
  for (const filename of ['LICENSE.txt', 'ATTRIBUTION.md']) {
    assert.equal(read('../public/demo-credits/' + filename), read('../../src/data/' + filename));
  }
});

test('sparse strokes recognize repeated letters without extra turns', () => {
  assert.equal(recognize(stroke('helo'))[0], 'hello');
  assert.equal(recognize(stroke('schol'))[0], 'school');
});

test('recognition ranks alternatives and tolerates imprecise aim', () => {
  const points = stroke('world').map(([x, y], index) =>
    [x + (index % 2 ? 0.13 : -0.11), y + (index % 2 ? -0.09 : 0.08)]);
  const choices = recognize(points);
  assert.equal(choices[0], 'world');
  assert.equal(choices.length, 9);
  assert.equal(new Set(choices).size, 9);
});

test('a single point and an off-board path produce no suggestions', () => {
  assert.deepEqual(recognize(stroke('w')), []);
  assert.deepEqual(recognize([[-9, -9], [-7, -8]]), []);
});


test('contractions share their letter-only paths with ordinary spellings', () => {
  const english = makeRecognizer(JSON.parse(data).words, JSON.parse(read('../../src/data/contractions.json')));
  assert.equal(english(stroke('dont'))[0], "don't");
  assert.equal(english(stroke('im'))[0], "I'm");
  assert.deepEqual(english(stroke('well')).slice(0,2), ['well', "we'll"]);
});


test('Zhuyin keeps corners and permits straight-through symbols in a phrase', async () => {
  const {traceReadings}=await import('../../src/ui/zhuyin-trace.mjs');
  const rows=['ㄅㄉˇˋㄓˊ˙ㄚㄞㄢㄦ','ㄆㄊㄍㄐㄔㄗㄧㄛㄟㄣ','ㄇㄋㄎㄑㄕㄘㄨㄜㄠㄤ','ㄈㄌㄏㄒㄖㄙㄩㄝㄡㄥ'];
  const centers=Object.fromEntries(rows.flatMap((row,y)=>[...row].map((k,x)=>[k,[(x+.5)*11/row.length,y+.5]])));
  const phrase='ㄕˋㄐㄧㄝˋ';
  const trace=[...phrase].map(k=>centers[k]);
  assert.ok(traceReadings(trace,centers).includes(phrase));
  assert.deepEqual(traceReadings([centers['ㄕ'],centers['ㄕ']],centers),[]);
});


test('Mandarin composes unlisted sentences and recognizes a multiword glide', async () => {
  const {makeConverter}=await import('../src/demo/mandarin.mjs');
  const {traceReadings,matchSwipe,endpointPairs}=await import('../../src/ui/zhuyin-trace.mjs');
  const decoder=makeConverter(read('../../src/data/zhuyin.csv'));
  const rows=['ㄅㄉˇˋㄓˊ˙ㄚㄞㄢㄦ','ㄆㄊㄍㄐㄔㄗㄧㄛㄟㄣ','ㄇㄋㄎㄑㄕㄘㄨㄜㄠㄤ','ㄈㄌㄏㄒㄖㄙㄩㄝㄡㄥ'];
  const centers=Object.fromEntries(rows.flatMap((row,y)=>[...row].map((key,x)=>[key,[(x+.5)*11/row.length,y+.5]])));
  const lookup=pairs=>pairs.flatMap(pair=>decoder.buckets.get(pair)??[]);
  for(const [reading,word,noise] of [['ㄨㄛˇㄧㄠˋㄔㄈㄢˋ','我要吃飯',0],['ㄒㄩㄝˊㄕㄥ','學生',.36],['ㄕˋㄐㄧㄝˋ','世界',.32]]){
    assert.equal(decoder.compose(reading)[0],word);
    const points=[...reading].map((key,i)=>[centers[key][0]+noise*Math.sin(i*3),centers[key][1]+noise*Math.cos(i*2)]);
    const ranked=matchSwipe(points,centers,lookup(endpointPairs(points,centers)),traceReadings(points,centers),decoder.syllables,lookup);
    assert.equal(decoder.convert(ranked).words[0],word);
  }
  const target='ㄨㄛˇㄕˋㄋㄧˇㄉㄜ˙';
  const recognize=points=>decoder.convert(matchSwipe(points,centers,lookup(endpointPairs(points,centers)),traceReadings(points,centers),decoder.syllables,lookup)).words;
  const slipped=[...target].map(k=>centers[k].slice());
  slipped[1]=slipped[1].map((v,d)=>.2*v+.8*centers['ㄞ'][d]);
  slipped[2]=slipped[1].map((v,d)=>(v+slipped[3][d])/2);
  const corrected=recognize(slipped);
  assert.equal(corrected[0],'我是你的');
  assert.ok(corrected.includes('歪是你的'));
  assert.equal(decoder.compose('ㄨㄞㄕˋㄋㄧˇㄉㄜ˙')[0],'歪是你的');
  for(let run=0;run<8;run++){
    const noisy=[...target].map((key,i)=>centers[key].map((v,d)=>v+.48*Math.sin(7*i+13*run+2*d)));
    const fast=noisy.map((p,i)=>i===0||i===noisy.length-1?p:p.map((v,d)=>.8*v+.1*(noisy[i-1][d]+noisy[i+1][d])));
    assert.equal(recognize(fast)[0],'我是你的');
  }
  // Separate vocabulary from the examples used during recognizer development.
  const heldOut=['ㄌㄠˇㄕ','ㄊㄨㄥˊㄒㄩㄝˊ','ㄒㄧㄣㄨㄣˊ','ㄧㄣㄩㄝˋ','ㄕˊㄐㄧㄢ','ㄍㄨㄥㄩㄢˊ',
    'ㄅㄧㄥㄒㄧㄤ','ㄒㄧㄤㄐㄧㄠ','ㄆㄥˊㄧㄡˇ','ㄉㄧㄢˋㄧㄥˇ','ㄧㄣˊㄏㄤˊ','ㄒㄧㄚˋㄩˇ'];
  let correct=0, roundedCorrect=0;
  for(const [i,reading] of heldOut.entries()){
    for(let run=0;run<4;run++){
      const points=[...reading].map((key,j)=>[
        centers[key][0]+.53*Math.sin(37*i+17*j+run),
        centers[key][1]+.42*Math.cos(23*i-7*j+run)
      ]);
      const options=matchSwipe(points,centers,lookup(endpointPairs(points,centers)),traceReadings(points,centers),decoder.syllables,lookup);
      if(decoder.convert(options).reading===reading)correct++;
      const rounded=points.map((p,j)=>!j||j===points.length-1?p:p.map((v,d)=>.8*v+.1*(points[j-1][d]+points[j+1][d])));
      const fastOptions=matchSwipe(rounded,centers,lookup(endpointPairs(rounded,centers)),traceReadings(rounded,centers),decoder.syllables,lookup);
      if(decoder.convert(fastOptions).reading===reading)roundedCorrect++;
    }
  }
  assert.ok(roundedCorrect>=32, `Only ${roundedCorrect}/48 rounded traces ranked the expected reading first`);
  assert.ok(correct>=42,`Only ${correct}/48 noisy traces ranked the expected reading first`);
});
