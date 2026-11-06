// Интерфейс Proba: шапка при прокрутке, меню, появление секций, чтение текста, шаги, вкладки.
// Всё — прогрессивное улучшение: без JS контент виден целиком.
const root = document.documentElement;
root.classList.remove('no-js');
root.classList.add('js');
const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

// Шапка: прозрачная → фиксированная полоса с размытием.
const header = document.querySelector('.site-header');
const onScroll = () => header?.classList.toggle('is-scrolled', window.scrollY > 24);
onScroll();
window.addEventListener('scroll', onScroll, { passive: true });

// Мобильное меню.
const toggle = document.querySelector('.nav-toggle');
const nav = document.getElementById('site-nav');
toggle?.addEventListener('click', () => {
  const open = nav.classList.toggle('is-open');
  toggle.setAttribute('aria-expanded', String(open));
  toggle.textContent = open ? 'Закрыть' : 'Меню';
});

// Появление при прокрутке.
const revealEls = document.querySelectorAll('[data-reveal]');
if ('IntersectionObserver' in window && !reduce) {
  const io = new IntersectionObserver(
    (entries) => entries.forEach((e) => { if (e.isIntersecting) { e.target.classList.add('is-visible'); io.unobserve(e.target); } }),
    { rootMargin: '0px 0px -10% 0px' },
  );
  revealEls.forEach((el) => io.observe(el));
} else {
  revealEls.forEach((el) => el.classList.add('is-visible'));
}

// Editorial word reveal: прогресс прокрутки контейнера → индекс «прочитанного» слова.
document.querySelectorAll('[data-word-reveal]').forEach((el) => {
  const words = el.textContent.trim().split(/\s+/);
  el.setAttribute('aria-label', words.join(' '));
  el.textContent = '';
  const spans = words.map((w, i) => {
    const s = document.createElement('span');
    s.className = 'w';
    s.setAttribute('aria-hidden', 'true');
    s.textContent = w;
    el.append(s);
    if (i < words.length - 1) el.append(' ');
    return s;
  });
  if (reduce) { spans.forEach((s) => s.classList.add('is-on')); return; }
  let ticking = false;
  const update = () => {
    ticking = false;
    const r = el.getBoundingClientRect();
    const vh = window.innerHeight;
    const progress = Math.min(1, Math.max(0, (vh * 0.85 - r.top) / (r.height + vh * 0.35)));
    const n = Math.round(progress * spans.length);
    spans.forEach((s, i) => s.classList.toggle('is-on', i < n));
  };
  window.addEventListener('scroll', () => { if (!ticking) { ticking = true; requestAnimationFrame(update); } }, { passive: true });
  update();
});

// Шаги: раскрытие одного, остальные — 0.4.
document.querySelectorAll('[data-steps]').forEach((list) => {
  const steps = [...list.querySelectorAll('.step')];
  const activate = (step) => {
    steps.forEach((s) => {
      const on = s === step;
      s.classList.toggle('is-active', on);
      s.querySelector('.step__btn').setAttribute('aria-expanded', String(on));
    });
    list.classList.add('has-active');
    const card = document.querySelector('[data-step-label]');
    if (card) card.textContent = step.dataset.label;
  };
  steps.forEach((s) => s.querySelector('.step__btn').addEventListener('click', () => activate(s)));
  if (steps[0]) activate(steps[0]);
});

// Вкладки.
document.querySelectorAll('[data-tabs]').forEach((box) => {
  const tabs = [...box.querySelectorAll('[role="tab"]')];
  const panels = tabs.map((t) => document.getElementById(t.getAttribute('aria-controls')));
  const select = (i, focus = false) => {
    tabs.forEach((t, j) => { t.setAttribute('aria-selected', String(i === j)); t.tabIndex = i === j ? 0 : -1; });
    panels.forEach((p, j) => { p.hidden = i !== j; });
    if (focus) tabs[i].focus();
  };
  tabs.forEach((t, i) => {
    t.addEventListener('click', () => select(i));
    t.addEventListener('keydown', (e) => {
      if (e.key === 'ArrowRight') select((i + 1) % tabs.length, true);
      if (e.key === 'ArrowLeft') select((i - 1 + tabs.length) % tabs.length, true);
    });
  });
  select(0);
});
