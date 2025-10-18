(function(){
   window.addEventListener('load', () => {
     setTimeout(() => {
       document.querySelectorAll('[data-skel="summary"]').forEach(el => el.remove());
       document.querySelectorAll('.hidden-until-ready').forEach(el => el.classList.remove('hidden-until-ready'));
       const skelRow = document.querySelector('[data-skel="table"]');
       if (skelRow) skelRow.remove();
     }, 50);
   });
 })();

(function(){
  const input = document.getElementById('jobs-search');
  const tbody = document.getElementById('jobs-tbody');
  if (!input || !tbody) return;
  const fmtBRL = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' });
  const originalRowsHTML = tbody.innerHTML;
  function formatCurrency(value) {
    value = 1000*value;
    if (value === null || typeof value === 'undefined') {
      return "—";
    }
      return new Intl.NumberFormat('pt-BR', {
        style: 'currency',
        currency: 'BRL'
        }).format(value);
  }
  function renderRows(rows){
    if (!rows || !rows.length){
      tbody.innerHTML = `<tr><td colspan="6" class="text-center text-muted">Nenhum resultado encontrado.</td></tr>`;
      return;
    }
    const html = rows.map(r => `
      <tr>
        <td>${r.cargo ?? '—'}</td>
        <td>${r.nivel ?? '—'}</td>
        <td>${r.estado ?? '—'}</td>
        <td>${r.modalidade_trabalho ?? '—'}</td>
        <td>${formatCurrency(r.salario_base)}</td>
        <td>${formatCurrency(r.remuneracao_total_mensal)}</td>
      </tr>`).join('');
    tbody.innerHTML = html;
  }
  let timer = null;
  async function performSearch(q){
    if (!q){
      tbody.innerHTML = originalRowsHTML;
      return;
    }
    tbody.innerHTML = `<tr><td colspan="6"><div class="skeleton skeleton-line skeleton-100"></div><div class="skeleton skeleton-line skeleton-80"></div></td></tr>`;
    try{
      const res = await fetch(`/api/search?q=${encodeURIComponent(q)}&k=20`);
      if (!res.ok) throw new Error('HTTP '+res.status);
      const json = await res.json();
      renderRows(json.results);
    }catch(err){
      console.error('Busca falhou', err);
      tbody.innerHTML = `<tr><td colspan="6" class="text-danger">Erro ao buscar vagas.</td></tr>`;
    }
  }
  input.addEventListener('input', () => {
    const q = input.value.trim();
    clearTimeout(timer);
    timer = setTimeout(() => performSearch(q), 280);
  });
})();