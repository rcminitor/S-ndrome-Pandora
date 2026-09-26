/* ==========================================================================
   Aba "Estatísticas" — desenha dados_estatisticas.js (gerado em Python).
   SVG puro, sem bibliotecas: funciona abrindo o index.html direto do disco.
   ========================================================================== */
(function () {
  'use strict';
  const D = window.DADOS_ESTATISTICAS;
  const box = document.getElementById('estConteudo');
  if (!box) return;
  if (!D) {
    box.innerHTML = '<div class="pn-empty">Rode <code>python analise/estatisticas.py</code> para gerar <code>dados_estatisticas.js</code>.</div>';
    return;
  }

  const COR = { 'Núcleo 1': '#3b82f6', 'Núcleo 2': '#ec4899' };
  const esc = (t) => String(t).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const num = (v, d = 0) => Number(v).toLocaleString('pt-BR', { minimumFractionDigits: d, maximumFractionDigits: d });
  const pFmt = (p) => (p < 0.001 ? '< 0,001' : num(p, 3));
  const legenda = () => `<div class="est-legenda">${Object.entries(COR).map(([n, c]) => `<span><i style="background:${c}"></i>${n}</span>`).join('')}</div>`;

  function tiles() {
    const k = D.kpis;
    const t = (v, r, s) => `<div class="est-tile"><b>${v}</b><span>${r}</span><small>${s}</small></div>`;
    return `<div class="est-tiles">
      ${t(D.total, 'Registros no inventário', 'fonte: dados_inventario.js')}
      ${t(k.com_arquivo, 'Com arquivo', `${num(k.com_arquivo / D.total * 100, 0)}% do acervo`)}
      ${t(k.fichados, 'Fichados', `${num(k.pct_fichados, 1)}% do acervo`)}
      ${t(k.procedencia_confirmada, 'Referências confirmadas', 'conferidas no PDF')}
    </div>`;
  }

  function colunasAno() {
    const { anos, series, sem_ano } = D.anos;
    const W = 680, H = 260, pl = 32, pr = 8, pt = 12, pb = 30;
    const tot = anos.map((_, i) => series['Núcleo 1'][i] + series['Núcleo 2'][i]);
    const passo = Math.max(1, Math.ceil(Math.max(...tot) / 4));
    const max = passo * 4;
    const bw = (W - pl - pr) / anos.length;
    const y = (v) => pt + (H - pt - pb) * (1 - v / max);
    let s = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Fontes por ano de publicação e núcleo">`;
    for (let g = 0; g <= 4; g++) { const v = passo * g; s += `<line x1="${pl}" x2="${W - pr}" y1="${y(v)}" y2="${y(v)}" class="pn-grid"/><text x="${pl - 6}" y="${y(v) + 4}" text-anchor="end" class="pn-axis">${v}</text>`; }
    anos.forEach((a, i) => {
      const x = pl + i * bw + bw * 0.2, w = bw * 0.6;
      let base = 0;
      ['Núcleo 1', 'Núcleo 2'].forEach((n) => {
        const v = series[n][i];
        if (!v) return;
        const y0 = y(base), y1 = y(base + v);
        s += `<rect x="${x}" y="${y1 + 1}" width="${w}" height="${Math.max(0, y0 - y1 - 2)}" rx="3" fill="${COR[n]}"><title>${a} · ${n}: ${v}</title></rect>`;
        base += v;
      });
      if (anos.length <= 12 || i % 2 === 0 || i === anos.length - 1) s += `<text x="${x + w / 2}" y="${H - 10}" text-anchor="middle" class="pn-axis">${String(a).slice(2)}</text>`;
    });
    s += '</svg>';
    return `${legenda()}<div class="pn-chart">${s}</div>
      <p class="pn-muted">Eixo x: ano (’03 = 2003). ${sem_ano} registro(s) sem ano confirmado ficaram de fora. Passe o mouse nas barras para ver os valores.</p>
      <details class="est-tabela"><summary>Ver como tabela</summary><table class="week-table"><thead><tr><th>Ano</th><th>Núcleo 1</th><th>Núcleo 2</th></tr></thead><tbody>${anos.map((a, i) => (series['Núcleo 1'][i] + series['Núcleo 2'][i]) ? `<tr><td>${a}</td><td>${series['Núcleo 1'][i]}</td><td>${series['Núcleo 2'][i]}</td></tr>` : '').join('')}</tbody></table></details>`;
  }

  function hbars(itens, cor) {
    const max = Math.max(1, ...itens.map((i) => i.n));
    return `<div class="pn-hbars">${itens.map((i) => `<div class="pn-hbar"><span>${esc(i.rotulo)}</span><div><i style="width:${i.n / max * 100}%;background:${cor}"></i></div><b>${i.n}</b></div>`).join('')}</div>`;
  }

  function funil() {
    return Object.entries(D.funil_por_nucleo).map(([n, itens]) => `<h4 class="est-sub"><i style="background:${COR[n]}"></i>${n}</h4>${hbars(itens, COR[n])}`).join('');
  }

  function resumoAno() {
    return `<table class="week-table"><thead><tr><th>Núcleo</th><th>n</th><th>Mediana</th><th>Q1–Q3</th><th>Mín–máx</th><th>Últimos 3 anos</th></tr></thead><tbody>${D.resumo_ano.map((r) => `<tr><td>${r.nucleo}</td><td>${r.n}</td><td>${r.mediana}</td><td>${Math.round(r.q1)}–${Math.round(r.q3)}</td><td>${r.min}–${r.max}</td><td>${num(r.pct_ultimos_3_anos, 1)}%</td></tr>`).join('')}</tbody></table>
    <p class="pn-muted">Mediana: ano do meio da lista. Q1–Q3: faixa onde estão os 50% centrais.</p>`;
  }

  function testes() {
    return D.testes.map((t) => {
      const sig = t.p < 0.05;
      const tabela = t.tabela ? `<table class="week-table"><thead><tr><th></th>${t.tabela.colunas.map((c) => `<th>${esc(c)}</th>`).join('')}</tr></thead><tbody>${t.tabela.linhas.map((l, i) => `<tr><td>${esc(l)}</td>${t.tabela.valores[i].map((v) => `<td>${v}</td>`).join('')}</tr>`).join('')}</tbody></table>` : '';
      return `<div class="content-card est-teste">
        <h3 class="card-title">${esc(t.pergunta)}</h3>
        <p class="pn-muted">${esc(t.nome)}</p>
        ${tabela}
        <div class="est-numeros">
          <span>p = <b>${pFmt(t.p)}</b></span>
          <span>${esc(t.efeito_nome)} = <b>${num(t.efeito, 2)}</b></span>
          <span class="est-selo ${sig ? 'sim' : 'nao'}">${sig ? '✓ diferença detectada (p < 0,05)' : '— sem evidência de diferença'}</span>
        </div>
        <p>${esc(t.leitura)}</p>
        ${t.aviso ? `<p class="pn-warn">${esc(t.aviso)}</p>` : ''}
      </div>`;
    }).join('');
  }

  box.innerHTML = `
    ${tiles()}
    <div class="content-card"><h3 class="card-title">Fontes por ano de publicação</h3>${colunasAno()}</div>
    <div class="pn-grid-2">
      <div class="content-card"><h3 class="card-title">Funil de leitura por núcleo</h3>${funil()}</div>
      <div class="content-card"><h3 class="card-title">Procedência das referências</h3>${hbars(D.procedencia, '#64748b')}
        <p class="pn-muted">“A conferir” = referência montada a partir do .bib, ainda não vista no PDF.</p>
        <h3 class="card-title" style="margin-top:18px">Idade do acervo</h3>${resumoAno()}</div>
    </div>
    <h3 class="card-title" style="margin:8px 0 12px">Testes estatísticos — para aprender com os próprios dados</h3>
    <div class="pn-grid-2">${testes()}</div>
    <p class="pn-warn">${esc(D.aviso_geral)}</p>
    <p class="pn-muted">Gerado em ${D.gerado_em.split('-').reverse().join('/')} por <code>analise/estatisticas.py</code>.</p>`;
})();
