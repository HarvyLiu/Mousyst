import { keyCenters } from './recognizer.mjs';

type Point = [number, number];
type Insertion = { start: number; end: number; before: string; after: string; candidates: string[]; selected: number };
type Edit = {kind:'phrase'; value:string} | {kind:'key'; key:string} | {kind:'word'; id:number; shift:boolean; candidates?:string[]};
type Stroke = {id:number; letter:string; start:Point; points:Point[]; dragged:boolean; threshold:number};

const demo = document.querySelector<HTMLElement>('#typing-demo')!;
const text = demo.querySelector<HTMLTextAreaElement>('textarea')!;
const board = demo.querySelector<HTMLElement>('.letter-board')!;
const symbols = demo.querySelector<HTMLElement>('.symbol-board')!;
const layer = demo.querySelector<HTMLButtonElement>('#layer')!;
const shift = demo.querySelector<HTMLButtonElement>('#demo-shift')!;
const status = demo.querySelector<HTMLElement>('.status')!;
const undo = demo.querySelector<HTMLButtonElement>('#undo-word')!;
const strip = demo.querySelector<HTMLElement>('.candidates')!;
const buttons = [...strip.querySelectorAll<HTMLButtonElement>('[data-candidate]')];
const letters = [...board.querySelectorAll<HTMLButtonElement>('[data-letter]')];
const trail = board.querySelector<SVGPathElement>('path')!;
const edits: Edit[] = [];
let owner: Insertion | null = null;
let stroke: Stroke | null = null;
let shifted = false;
let sequence = 0;
let worker: Worker | undefined;
let wheelRemainder = 0;

function notice(en = '', zh = '') {
  status.dataset.en = en;
  status.dataset.zh = zh;
  status.textContent = document.documentElement.lang.startsWith('zh') ? zh : en;
}

function ownsWord() {
  return owner && text.value === owner.after &&
    text.selectionStart === owner.end && text.selectionEnd === owner.end;
}

function refreshSuggestions() {
  const active = ownsWord() && edits.length === 0 ? owner : null;
  buttons.forEach((button,i) => {
    button.textContent = active?.candidates[i] ?? '';
    button.disabled = !button.textContent;
    button.setAttribute('aria-pressed',String(active?.selected === i));
  });
  undo.disabled = !active;
}

function insert(value: string, start = text.selectionStart, end = text.selectionEnd) {
  text.setRangeText(value,start,end,'end');
}

function setShift(on: boolean) {
  shifted = on;
  shift.setAttribute('aria-pressed',String(on));
  for (const button of letters) {
    const value = button.dataset.letter!;
    button.textContent = on ? value.toUpperCase() : value;
  }
}

const graphemes = typeof Intl.Segmenter === 'function'
  ? new Intl.Segmenter(undefined, {granularity: 'grapheme'})
  : undefined;
function applyKey(value: string) {
  const {selectionStart:start,selectionEnd:end} = text;
  if (value === ' ' && ownsWord()) return;
  if (value === 'Backspace') {
    let from = start;
    if (start === end && start > 0) {
      from = graphemes?.segment(text.value).containing(start - 1)?.index
        ?? start - ([...text.value.slice(0, start)].at(-1)?.length ?? 0);
    }
    insert('',from,end);
  } else {
    const join = /^[.,!?;:'"%)}\]…。，、；：！？％’”»]$/u.test(value) && ownsWord();
    insert(value,join ? start-1 : start,end);
  }
  owner=null;
}

function drain() {
  while (edits.length) {
    const action=edits[0];
    if (action.kind === 'word' && !action.candidates) break;
    edits.shift();
    if (action.kind === 'phrase') {
      insert(action.value);
      owner = null;
    } else if (action.kind === 'key') {
      applyKey(action.key);
    } else if (action.candidates?.length) {
      const choices = action.candidates.map(word => action.shift ? word[0].toUpperCase()+word.slice(1) : word);
      const start=text.selectionStart;
      const before=text.value.slice(start,text.selectionEnd);
      insert(choices[0]+' ');
      owner={start,end:text.selectionEnd,before,after:text.value,candidates:choices,selected:0};
      wheelRemainder=0;
      notice();
    } else {
      notice('Try another swipe, or click the letters to spell it.','請再滑一次，或逐鍵點擊以輸入單字。');
    }
  }
  refreshSuggestions();
}

function key(value: string) {
  notice();
  edits.push({kind:'key',key:value});
  drain();
}

function exact(letter: string) {
  key(shifted ? letter.toUpperCase() : letter);
  setShift(false);
}

function recognize(points: Point[]) {
  try {
    if (!worker) {
      worker = new Worker(new URL('./worker.ts',import.meta.url),{type:'module'});
      worker.onmessage = event => {
        const action = edits.find(item => item.kind==='word' && item.id===event.data.id);
        if (action?.kind!=='word') return;
        action.candidates=event.data.candidates;
        drain();
      };
      worker.onerror = () => {
        worker?.terminate(); worker=undefined;
        for (const action of edits) if (action.kind==='word') action.candidates=[];
        drain();
        notice('Swipe recognition could not load. Click letters to type.','無法載入滑行辨識，請點擊字母輸入。');
      };
    }
    const id=++sequence;
    worker.postMessage({id,points});
    edits.push({kind:'word',id,shift:shifted});
    setShift(false);
    notice('Recognizing…','辨識中…');
    refreshSuggestions();
  } catch {
    notice('Swipe recognition is unavailable. Click letters to type.','滑行辨識無法使用，請點擊字母輸入。');
  }
}

function choose(i: number) {
  if (!edits.length && ownsWord() && owner && owner.candidates[i]) {
    insert(owner.candidates[i]+' ',owner.start,owner.end);
    owner.end=text.selectionEnd;
    owner.after=text.value;
    owner.selected=i;
  }
  refreshSuggestions();
}
buttons.forEach((button,i)=>button.addEventListener('click',()=>choose(i)));
strip.addEventListener('wheel',event=>{
  if (!ownsWord() || !owner || edits.length || !event.deltaY) return;
  event.preventDefault();
  const pixels = event.deltaMode===1 ? event.deltaY*40 : event.deltaMode===2 ? Math.sign(event.deltaY)*50 : event.deltaY;
  wheelRemainder+=pixels;
  const steps=Math.trunc(wheelRemainder/50);
  if (!steps) return;
  wheelRemainder-=steps*50;
  choose(Math.max(0,Math.min(owner.candidates.length-1,owner.selected+steps)));
},{passive:false});
undo.addEventListener('click',()=>{
  if (ownsWord() && owner) insert(owner.before,owner.start,owner.end);
  owner=null;refreshSuggestions();
});

function cancelStroke() {
  const id=stroke?.id;
  stroke=null;
  trail.setAttribute('d','');
  if (id!==undefined && board.hasPointerCapture(id)) board.releasePointerCapture(id);
}

function record(event: PointerEvent) {
  if (!stroke) return;
  const point:Point=[event.clientX,event.clientY];
  const last=stroke.points.at(-1)!;
  if (point[0]!==last[0] || point[1]!==last[1]) stroke.points.push(point);
  if (Math.hypot(point[0]-stroke.start[0],point[1]-stroke.start[1])>stroke.threshold) stroke.dragged=true;
}

function paintTrail() {
  if (!stroke?.dragged) return;
  const rect=board.getBoundingClientRect();
  const recent = stroke.points.slice(-32);
  const vertices = recent.map(([x,y])=>[x-rect.left,y-rect.top]);
  let path = 'M '+vertices[0].join(' ');
  for (let i=1;i<vertices.length-1;i++) {
    const [x,y]=vertices[i], [nextX,nextY]=vertices[i+1];
    path+=' Q '+x+' '+y+' '+(x+nextX)/2+' '+(y+nextY)/2;
  }
  trail.setAttribute('d',path+' L '+vertices.at(-1)!.join(' '));
}

function keyCenter(letter: string): Point {
  const rect=board.querySelector<HTMLElement>('[data-letter="'+letter+'"]')!.getBoundingClientRect();
  return [rect.left+rect.width/2,rect.top+rect.height/2];
}
function normalized(points: Point[]): Point[] {
  const q=keyCenter('q'), p=keyCenter('p'), a=keyCenter('a');
  return points.map(([x,y])=>[
    keyCenters.q[0]+9*(x-q[0])/(p[0]-q[0]),
    keyCenters.q[1]+(y-q[1])/(a[1]-q[1])
  ]);
}

board.addEventListener('pointerdown',event=>{
  const button=(event.target as Element).closest<HTMLButtonElement>('[data-letter]');
  if (!button || stroke || !event.isPrimary || event.button!==0) return;
  event.preventDefault();
  const start:Point=[event.clientX,event.clientY];
  stroke={id:event.pointerId,letter:button.dataset.letter!,start,points:[start],dragged:false,threshold:button.offsetWidth/3};
  board.setPointerCapture(event.pointerId);
});
board.addEventListener('pointermove',event=>{
  if (stroke?.id!==event.pointerId) return;
  for (const sample of event.getCoalescedEvents?.() ?? []) record(sample);
  record(event);paintTrail();
});
board.addEventListener('pointerup',event=>{
  if (!stroke || stroke.id!==event.pointerId) return;
  record(event);
  const {letter,dragged,points}=stroke;
  cancelStroke();
  const rect=board.getBoundingClientRect();
  if (event.clientX<rect.left || event.clientX>=rect.right || event.clientY<rect.top || event.clientY>=rect.bottom) return;
  if (dragged) recognize(normalized(points));
  else if ((document.elementFromPoint(event.clientX,event.clientY) as HTMLElement)?.closest<HTMLElement>('[data-letter]')?.dataset.letter===letter) exact(letter);
});
function pointerCancelled(event: PointerEvent) {
  if (event.pointerId === stroke?.id) cancelStroke();
}
board.addEventListener('pointercancel',pointerCancelled);
board.addEventListener('lostpointercapture',pointerCancelled);
for (const button of letters) button.addEventListener('click',event=>{
  if (event.detail===0) exact(button.dataset.letter!);
});

function invalidate() {
  cancelStroke();
  edits.length=0;owner=null;wheelRemainder=0;notice();refreshSuggestions();
}
text.addEventListener('input',invalidate);
text.addEventListener('pointerdown',invalidate);
text.addEventListener('keydown',event=>{
  if (event.key!=='Shift' && event.key!=='Control' && event.key!=='Alt' && event.key!=='Meta') invalidate();
});
document.addEventListener('selectionchange',()=>{
  if (owner && !ownsWord()) {owner=null;refreshSuggestions();}
});
document.addEventListener('keydown',event=>{
  if (event.key==='Escape') invalidate();
});
window.addEventListener('blur',invalidate);
window.addEventListener('resize',cancelStroke);
demo.querySelector('.demo-keyboard')!.addEventListener('mousedown',event=>event.preventDefault());
layer.addEventListener('click',()=>{
  cancelStroke();
  board.hidden=!board.hidden;
  symbols.hidden=!board.hidden;
  layer.textContent=board.hidden?'ABC':'123';
  layer.setAttribute('aria-pressed',String(board.hidden));
  shift.disabled=board.hidden;
  setShift(false);
});
shift.addEventListener('click',()=>setShift(!shifted));
demo.querySelectorAll<HTMLButtonElement>('[data-char]').forEach(button=>
  button.addEventListener('click',()=>key(button.dataset.char!)));
demo.querySelector('#backspace')!.addEventListener('click',()=>key('Backspace'));

const replyTools = demo.querySelector<HTMLDetailsElement>('#reply-tools')!;
const draft = demo.querySelector<HTMLInputElement>('#reply-draft')!;
const insertReply = demo.querySelector<HTMLButtonElement>('#insert-reply')!;
const saveReply = demo.querySelector<HTMLButtonElement>('#save-reply')!;
let savedReply = '';
function openLinkedTools() {
  if (location.hash === '#reply-tools') replyTools.open = true;
}
openLinkedTools();
window.addEventListener('hashchange', openLinkedTools);
draft.addEventListener('input', () => { saveReply.disabled = !draft.value.trim(); });
saveReply.addEventListener('click', () => {
  savedReply = draft.value;
  insertReply.disabled = false;
  notice('Reply saved for this visit.', '已儲存回覆，離開本頁後會清除。');
});
insertReply.addEventListener('click', () => {
  notice();
  edits.push({kind:'phrase', value:savedReply});
  drain();
  text.focus({preventScroll:true});
});
