function isDarkModeActive() {
  try {
    const saved = localStorage.getItem('jobobs-dark-mode');
    if (saved === '1') return true;
    if (saved === '0') return false;
  } catch (e) {}
  return document.documentElement.classList.contains('dark') || (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches);
}
const plotDataElement = document.getElementById('visualizations-data');
let visualizations = [];
if (plotDataElement) {
  try {
    visualizations = JSON.parse(plotDataElement.textContent);
  } catch (error) {
    console.error('Não foi possível carregar os dados dos gráficos.', error);
  }
}
function addLoader(container){
  container.classList.remove('ready');
  const loader = container.querySelector('.chart-loader');
  if (loader) loader.style.display = 'flex';
}
function removeLoader(container){
  const loader = container.querySelector('.chart-loader');
  if (loader) loader.style.display = 'none';
  container.classList.add('ready');
}
const dark = isDarkModeActive();
visualizations.forEach((viz) => {
  const target = document.getElementById(viz.id);
  const wrapper = target && target.closest('.chart-wrapper');
  if (!target || !wrapper) return;
  addLoader(wrapper);
  const figObj = dark ? (viz.figure_dark || viz.figure || viz.figure_light) : (viz.figure_light || viz.figure || viz.figure_dark);
  if (!figObj) { removeLoader(wrapper); return; }
  const data = figObj.data || (figObj.figure && figObj.figure.data) || [];
  const layout = figObj.layout || (figObj.figure && figObj.figure.layout) || {};
  const config = { responsive: true, displaylogo: false };
  Promise.resolve(Plotly.newPlot(target, data, layout, config))
    .then(() => removeLoader(wrapper))
    .catch((err) => {
      console.error('Erro ao renderizar gráfico', viz.id, err);
      removeLoader(wrapper);
    });
});

     (function () {
        const KEY = 'jobobs-dark-mode';
        const switchElement = document.getElementById('darkModeSwitch');
        const htmlEl = document.documentElement;

        function applyDark(isDark) {
          htmlEl.classList.toggle('dark', !!isDark);
          if (switchElement) switchElement.checked = !!isDark;
        }

        try {
          const saved = localStorage.getItem(KEY);
          if (saved === '1' || saved === '0') {
            applyDark(saved === '1');
          } else if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
            applyDark(true);
          } else {
            applyDark(false);
          }
        } catch (e) {
        }

        if (switchElement) {
          switchElement.addEventListener('change', () => {
            const isDark = !!switchElement.checked;
            applyDark(isDark);
            try { localStorage.setItem(KEY, isDark ? '1' : '0'); } catch (e) {}
          });
        }
      })();