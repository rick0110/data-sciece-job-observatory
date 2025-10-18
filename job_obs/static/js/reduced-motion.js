

(function(){
  const prefersReduced = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  if (prefersReduced) return;

  const fmtBRL = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' });
  const fmtInt = new Intl.NumberFormat('pt-BR');

  function easeOutCubic(t){ return 1 - Math.pow(1 - t, 3); }

  function animateValue(el, start, end, duration, isCurrency){
    const startTime = performance.now();
    function step(now){
      const elapsed = now - startTime;
      const t = Math.min(1, elapsed / duration);
      const v = start + (end - start) * easeOutCubic(t);
      if (isCurrency){
        el.textContent = fmtBRL.format(v);
      } else {
        el.textContent = fmtInt.format(Math.round(v));
      }
      if (t < 1) requestAnimationFrame(step);
    }
    requestAnimationFrame(step);
  }

  function parseNumber(value){
    if (value === null || value === undefined || value === '') return 0;
    if (typeof value === 'number') return value;
    const n = Number(String(value).replace(',', '.'));
    return isNaN(n) ? 0 : n;
  }

  const elems = Array.from(document.querySelectorAll('.count-up'));
  if(!elems.length) return;

  const observer = new IntersectionObserver((entries, obs) => {
    entries.forEach(entry => {
      if (!entry.isIntersecting) return;
      const el = entry.target;
      // prevent double-start
      if (el.dataset.animated) return;
      el.dataset.animated = '1';

      const raw = el.getAttribute('data-value');
      const value = parseNumber(raw);
      const isCurrency = el.classList.contains('currency');
      const duration = isCurrency ? 3600 : 2400;
      const start = 0;
      animateValue(el, start, value, duration, isCurrency);

      obs.unobserve(el);
    });
  }, { threshold: 0.5 });

  elems.forEach(el => observer.observe(el));
})();