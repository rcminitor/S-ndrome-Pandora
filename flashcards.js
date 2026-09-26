/* Flashcards gerados pela equipe CrewAI (agentes_crewai/estudo_crew.py) */
(function () {
  'use strict';
  const box = document.getElementById('fcBox');
  if (!box) return;
  const cards = window.DADOS_FLASHCARDS || [];
  const esc = (t) => String(t).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  if (!cards.length) {
    box.innerHTML = '<h3 class="card-title">Flashcards dos agentes</h3><p class="pn-muted">Ainda não há flashcards. Rode <code>python agentes_crewai/estudo_crew.py "tema"</code> e eles aparecem aqui.</p>';
    return;
  }
  const temas = ['Todos', ...new Set(cards.map((c) => c.tema))];
  let tema = 'Todos', i = 0, virado = false;
  const lista = () => cards.filter((c) => tema === 'Todos' || c.tema === tema);
  function render() {
    const l = lista(); const c = l[i % l.length];
    box.innerHTML = `
      <div class="pn-card-head"><h3 class="card-title">Flashcards dos agentes</h3>
        <select id="fcTema" class="pn-btn" aria-label="Filtrar por tema">${temas.map((t) => `<option ${t === tema ? 'selected' : ''}>${esc(t)}</option>`).join('')}</select></div>
      <button type="button" class="fc-card" id="fcVirar" aria-live="polite">
        <small>${virado ? 'Resposta' : 'Pergunta'} ${i % l.length + 1}/${l.length} · ${esc(c.tema)}</small>
        <span>${esc(virado ? c.resposta : c.pergunta)}</span>
        ${virado ? `<em>Fonte: ${esc(c.fonte)}</em>` : '<em>clique para ver a resposta</em>'}
      </button>
      <div class="pn-actions" style="margin-top:10px">
        <button class="pn-btn" id="fcAnt" type="button">← Anterior</button>
        <button class="pn-btn pn-btn-primary" id="fcProx" type="button">Próximo →</button>
      </div>
      <p class="pn-muted">Gerados por IA a partir do inventário. Confira no PDF antes de usar na tese.</p>`;
    box.querySelector('#fcVirar').onclick = () => { virado = !virado; render(); };
    box.querySelector('#fcProx').onclick = () => { i++; virado = false; render(); };
    box.querySelector('#fcAnt').onclick = () => { i = (i - 1 + l.length) % l.length; virado = false; render(); };
    box.querySelector('#fcTema').onchange = (e) => { tema = e.target.value; i = 0; virado = false; render(); };
  }
  render();
})();
