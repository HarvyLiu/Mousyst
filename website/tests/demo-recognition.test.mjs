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
