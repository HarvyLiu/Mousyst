// A sequence of distinct scroll chapters, using the browser's native scroll.
const clamp = (x: number) => Math.min(1, Math.max(0, x));
const ease = (x: number) => { x = clamp(x); return x * x * (3 - 2 * x); };
const reduced = matchMedia('(prefers-reduced-motion: reduce)');
const intro = document.querySelector<HTMLElement>('.intro-scroll')!;
const problem = document.querySelector<HTMLElement>('.problem-chapter')!;
const solution = document.querySelector<HTMLElement>('.solution-chapter')!;
const features = document.querySelector<HTMLElement>('.features')!;
const closing = document.querySelector<HTMLElement>('.closing')!;
const progress = (el: HTMLElement) => clamp(-el.getBoundingClientRect().top / Math.max(1, el.offsetHeight - innerHeight));
let scheduled = false;
function render() {
  scheduled = false;
  const links = [...document.querySelectorAll<HTMLAnchorElement>('.chapter-nav a')];
  let current = links[0];
  links.forEach(link => { if (document.querySelector(link.hash)!.getBoundingClientRect().top <= innerHeight * .45) current = link; });
  links.forEach(link => { link.classList.toggle('active', link === current); if (link === current) link.setAttribute('aria-current', 'location'); else link.removeAttribute('aria-current'); });
  if (reduced.matches) return;
  const p = progress(intro);
  const title = intro.querySelector<HTMLElement>('h1')!;
  title.style.transform = `translateY(${p * -65}px) scale(${1 - ease(p / .7) * .5})`;
  title.style.opacity = String(1 - ease((p - .35) / .55) * .85);
  intro.querySelectorAll<HTMLElement>('.hero-top,.hero-bottom,.section-line').forEach(el => el.style.opacity = String(1 - ease(p / .25)));
  const keyboard = intro.querySelector<HTMLElement>('.hero-keyboard')!;
  keyboard.style.transform = `perspective(1200px) translateY(${-p * innerHeight * .35}px) rotateX(${24 + p * 25}deg) rotateY(${p * -65}deg) rotateZ(${-7 + p * 20}deg) scale(${1 - p * .35})`;
  keyboard.style.opacity = String(1 - ease((p - .65) / .3));
  intro.querySelectorAll<HTMLElement>('.montage-panel').forEach((card, i) => {
    const angle = p * Math.PI * 2 + i * Math.PI / 2;
    const radius = Math.min(innerWidth * .25, 420);
    const depth = Math.cos(angle);
    card.style.transform = `translate3d(${Math.sin(angle) * radius}px,${(i - 1.5) * 135 - ease(p) * innerHeight * .65}px,${depth * 200}px) rotateY(${-Math.sin(angle) * 55}deg) rotateZ(${Math.sin(angle) * 8}deg) scale(${.75 + (depth + 1) * .12})`;
    card.style.opacity = String(ease((p - .05) / .22) * (1 - ease((p - .78) / .22)));
    card.style.zIndex = String(Math.round((depth + 1) * 10));
  });
  const q = progress(problem);
  const statement = problem.querySelector<HTMLElement>('.problem-statement')!;
  statement.style.transform = `translateY(${-ease((q - .65) / .35) * innerHeight * .6}px) scale(${1 - ease(q / .3) * .12})`;
  statement.style.opacity = String(1 - ease((q - .73) / .25));
  const rail = problem.querySelector<HTMLElement>('.interruption-cards')!;
  const travel = Math.max(0, rail.scrollWidth - innerWidth * .78);
  rail.style.transform = `translateX(${-ease((q - .15) / .65) * travel}px)`;
  problem.querySelectorAll<HTMLElement>('.interruption-card').forEach((card, i) => {
    const arrival = ease((q - .06 - i * .06) / .22);
    const leave = ease((q - .67 - i * .07) / .2);
    card.style.transform = `translateY(${(1 - arrival) * innerHeight * .6 - leave * innerHeight * 1.1}px) rotate(${(1 - arrival) * (i - 1) * 7 - leave * 5}deg)`;
  });
  const r = progress(solution);
  const manifesto = solution.querySelector<HTMLElement>('.manifesto')!;
  manifesto.style.transform = `scale(${.70 + ease(r) * .55}) translateY(${-ease((r - .7) / .3) * 60}px)`;
  manifesto.querySelectorAll<HTMLElement>('span').forEach((line, i) => {
    const reveal = ease((r + .12 - i * .13) / .24);
    line.style.opacity = String(.12 + reveal * .88);
    line.style.transform = `translateX(${(1 - reveal) * (i % 2 ? 80 : -80)}px)`;
  });
  const f = progress(features);
  features.querySelector<HTMLElement>('h2')!.style.transform = `scale(${1 - f * .2})`;
  features.querySelector<HTMLElement>('h2')!.style.opacity = String(1 - ease((f - .55) / .4) * .7);
  features.querySelectorAll<HTMLElement>('.feature').forEach((card, i) => {
    const local = (f - i * .21) / .57;
    const mobile = innerWidth < 800;
    card.style.transform = `translate3d(${mobile ? (i % 2 ? 35 : -35) : (i - 1) * Math.min(350, innerWidth * .23)}px,${-local * (innerHeight + 470)}px,0) rotate(${(i - 1) * -8 + local * 8}deg)`;
  });
  const c = ease((innerHeight - closing.getBoundingClientRect().top) / innerHeight);
  closing.querySelector<HTMLElement>('h2')!.style.transform = `scale(${.8 + c * .2})`;
  closing.querySelectorAll<HTMLElement>('.pixel-field span').forEach((pixel, i) => {
    pixel.style.transform = `translateY(${-ease((c - (i % 9) * .025) / .8) * (innerHeight * (.16 + (i % 13) * .045))}px)`;
  });
}
const schedule = () => { if (!scheduled) { scheduled = true; requestAnimationFrame(render); } };
addEventListener('scroll', schedule, { passive: true });
addEventListener('resize', schedule);
reduced.addEventListener('change', () => location.reload());
document.fonts.ready.then(schedule);
render();
