// Scroll is the timeline. Key-local coordinates stay accurate under 3D transforms.
const clamp = (x: number, a = 0, b = 1) => Math.min(b, Math.max(a, x));
const mix = (a: number, b: number, t: number) => a + (b - a) * t;
const smooth = (t: number) => { t = clamp(t); return t * t * (3 - 2 * t); };
const reduced = matchMedia('(prefers-reduced-motion: reduce)');
type Point = { x: number; y: number };

function keyboardScene(board: HTMLElement) {
  const svg = board.querySelector<SVGSVGElement>('.trail')!;
  const segments = board.querySelector<SVGGElement>('.trail-segments')!;
  const pointer = board.querySelector<SVGGElement>('.swipe-pointer')!;
  const keys = [...board.querySelectorAll<HTMLElement>('[data-key]')];
  let points: Point[] = [], lengths: number[] = [], total = 0;
  const lines = Array.from({ length: 28 }, () => {
    const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
    segments.append(line); return line;
  });
  function center(key: HTMLElement): Point {
    let x = key.offsetWidth / 2, y = key.offsetHeight / 2;
    let element: HTMLElement | null = key;
    while (element && element !== board) {
      x += element.offsetLeft; y += element.offsetTop;
      element = element.offsetParent as HTMLElement | null;
    }
    return { x, y };
  }
  function measure() {
    svg.setAttribute('viewBox', `0 0 ${board.offsetWidth} ${board.offsetHeight}`);
    points = [...'world'].map(letter => center(keys.find(key => key.dataset.key === letter)!));
    lengths = [0]; total = 0;
    points.slice(1).forEach((p, i) => { total += Math.hypot(p.x - points[i].x, p.y - points[i].y); lengths.push(total); });
  }
  function pointAt(distance: number): Point {
    distance = clamp(distance, 0, total);
    const i = Math.min(points.length - 2, Math.max(0, lengths.findIndex((n, i) => i < lengths.length - 1 && lengths[i + 1] >= distance)));
    const t = (distance - lengths[i]) / (lengths[i + 1] - lengths[i] || 1);
    return { x: mix(points[i].x, points[i + 1].x, t), y: mix(points[i].y, points[i + 1].y, t) };
  }
  measure();
  return {
    measure,
    draw(progress: number, released = false, corrected = false, correction = 0) {
      const distance = clamp(progress) * total;
      const tail = Math.min(distance, board.offsetWidth * .30);
      const fade = released ? 1 - smooth((progress - 1) * 5) : 1;
      segments.style.visibility = progress < 0 ? 'hidden' : 'visible';
      lines.forEach((line, i) => {
        const a = pointAt(distance - tail + tail * i / lines.length);
        const b = pointAt(distance - tail + tail * (i + 1) / lines.length);
        line.setAttribute('x1', String(a.x)); line.setAttribute('y1', String(a.y));
        line.setAttribute('x2', String(b.x)); line.setAttribute('y2', String(b.y));
        line.setAttribute('opacity', String((i + 1) / lines.length * fade));
      });
      const p = pointAt(distance);
      pointer.setAttribute('transform', `translate(${p.x} ${p.y})`);
      pointer.style.opacity = progress >= 0 && !released ? '1' : '0';
      if (correction > 0) {
        // The wheel operates over the bar, without moving to the alternative.
        const chosen = board.querySelector<HTMLElement>('.suggestions .chosen')!;
        const c = center(chosen);
        pointer.setAttribute('transform', `translate(${mix(p.x, c.x, correction)} ${mix(p.y, c.y, correction)})`);
        pointer.style.opacity = '1';
        pointer.classList.toggle('wheel-active', corrected);
      } else pointer.classList.remove('wheel-active');
      keys.forEach(key => {
        const c = center(key);
        key.classList.toggle('is-hit', !released && progress >= 0 && Math.hypot(c.x - p.x, c.y - p.y) < key.offsetWidth * .45);
      });
      board.classList.toggle('has-result', released);
      board.classList.toggle('is-corrected', corrected);
    }
  };
}

const story = document.querySelector<HTMLElement>('.scroll-story')!;
const object = story.querySelector<HTMLElement>('.scene-object')!;
const scenes = [...story.querySelectorAll<HTMLElement>('.scene')];
const board = keyboardScene(object.querySelector('.keyboard')!);
const heroBoard = document.querySelector<HTMLElement>('.hero-keyboard')!;
const heroIllustration = keyboardScene(heroBoard.querySelector('.keyboard')!);
const output = document.querySelector('#demo-word')!;
let pending = false;

function render() {
  pending = false;
  const rect = story.getBoundingClientRect();
  const p = clamp(-rect.top / Math.max(1, rect.height - innerHeight));
  const staticMode = reduced.matches;
  const active = staticMode ? 2 : Math.min(3, Math.floor(p * 4));
  story.dataset.activeScene = String(active);
  scenes.forEach((scene, i) => {
    const local = (p * 4 - i);
    const visibility = staticMode ? (i === active ? 1 : 0) :
      (i === 0 ? 1 : smooth((local + .08) / .15)) *
      (i === 3 ? 1 : 1 - smooth((local - .88) / .20));
    scene.style.opacity = String(visibility);
    scene.style.visibility = visibility ? 'visible' : 'hidden';
    scene.style.transform = staticMode ? 'none' : `translateY(${mix(45, 0, smooth(local / .2)) - smooth((local - .86) / .2) * 45}px)`;
  });
  story.querySelector('.scene-counter')!.textContent = `0${active + 1} / 04`;
  (story.querySelector('.story-track span') as HTMLElement).style.transform = `scaleX(${p})`;
  const arrival = smooth(p / .2);
  const settle = smooth((p - .2) / .12);
  const exit = smooth((p - .88) / .12);
  object.style.transform = staticMode ? 'none' : `perspective(1400px) translate3d(${mix(140, 0, arrival)}px,${mix(170, 0, arrival) - exit * 35}px,0) rotateX(${mix(38, 0, settle)}deg) rotateY(${mix(-18, 0, settle)}deg) rotateZ(${mix(-13, 0, settle) + exit * 4}deg) scale(${mix(.65, 1, arrival) - exit * .04})`;
  object.style.opacity = staticMode ? '1' : String(mix(.15, 1, arrival));
  const swipe = (p - .30) / .17;
  const released = staticMode || p >= .50;
  const corrected = !staticMode && p >= .81;
  board.draw(staticMode ? 1.3 : swipe, released, corrected, staticMode ? 0 : smooth((p - .75) / .06));
  output.textContent = released ? (corrected ? 'word ' : 'world ') : '';
  const backdrop = story.querySelector<HTMLElement>('.scene-backdrop')!;
  backdrop.style.transform = staticMode ? 'none' : `translateX(${-15 + p * 30}%) scale(${1 + p * .2})`;
  backdrop.style.opacity = staticMode ? '.03' : String(.035 + Math.sin(p * Math.PI) * .035);
  heroIllustration.draw(-1);
}
const schedule = () => { if (!pending) { pending = true; requestAnimationFrame(render); } };
addEventListener('scroll', schedule, { passive: true });
new ResizeObserver(() => { board.measure(); heroIllustration.measure(); schedule(); }).observe(object);
addEventListener('resize', schedule);
reduced.addEventListener('change', schedule);
document.fonts.ready.then(() => { board.measure(); heroIllustration.measure(); schedule(); });
render();
