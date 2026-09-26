/* Aba "Fichamentos": lê dados_fichamentos.js (cópia dos fichamentos do cofre, feita pelo
   Painel de Estudo) e mostra cada um formatado. Só leitura: editar é no Obsidian. */
(function () {
  'use strict';
  const box = document.getElementById('fiConteudo');
  if (!box) return;
  const D = window.DADOS_FICHAMENTOS || { fichamentos: [] };
  const lista = D.fichamentos;
  const esc = (t) => String(t ?? '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  const rot = (c) => (/^\d/.test(c) ? '#' + c : c);
  const badge = document.getElementById('fiCount');
  if (badge) badge.textContent = lista.length;

  // Obsidian → HTML: [[alvo|texto]] vira texto; callouts > [!tipo] Título viram caixas
  function preparar(md) {
    md = md.replace(/\[\[([^\]|]+)\|([^\]]+)\]\]/g, '$2').replace(/\[\[([^\]]+)\]\]/g, (_, a) => a.split('/').pop());
    return md.replace(/^> \[!(\w+)\][ \t]*(.*)$/gm, (_, tipo, tit) => `> <span class="fi-callout-tit fi-${tipo.toLowerCase()}">${esc(tit || tipo)}</span>\n>`);
  }
  function html(md) {
    if (window.marked) return window.marked.parse(preparar(md));
    return '<pre style="white-space:pre-wrap">' + esc(md) + '</pre>';
  }

  function indice() {
    if (!lista.length) { box.innerHTML = '<p>Nenhum fichamento publicado ainda.</p>'; return; }
    const card = (f) => `<button class="pn-tile fi-card" type="button" data-fi="${esc(f.arquivo)}">
        <strong>${esc(rot(f.codigo))} — ${esc(f.titulo)}</strong>
        <small>${f.nucleo ? 'Núcleo ' + esc(f.nucleo) + ' · ' : ''}${esc(f.paginas)}${f.data ? ' · fichado em ' + esc(f.data.split('-').reverse().join('/')) : ''}</small></button>`;
    box.innerHTML = `<p>Fichamentos escritos no cofre (${lista.length}). Clique para ler. Para editar, use o Obsidian; o site atualiza quando o painel publica. <small>Atualizado em ${esc((D.atualizado || '').replace('T', ' '))}.</small></p>
      <div class="pn-grid-3">${lista.map(card).join('')}</div>`;
  }

  function abrir(arquivo) {
    const f = lista.find((x) => x.arquivo === arquivo);
    if (!f) return indice();
    box.innerHTML = `<button class="pn-btn" type="button" id="fiVoltar">← Todos os fichamentos</button>
      <article class="content-card fi-texto">${html(f.md)}</article>`;
    box.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  box.addEventListener('click', (e) => {
    const c = e.target.closest('[data-fi]');
    if (c) return abrir(c.dataset.fi);
    if (e.target.id === 'fiVoltar') indice();
  });
  indice();
})();
