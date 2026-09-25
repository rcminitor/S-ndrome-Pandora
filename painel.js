/* ==========================================================================
   Painel de acompanhamento — páginas, janelas, KPIs, gráfico e galeria
   Sem dependências externas: funciona abrindo o index.html direto do disco.
   ========================================================================== */
(function () {
  'use strict';

  const STORE_KEY = 'pandora.registros.v1';
  const METAS_KEY = 'pandora.metas.v4';
  const INVENTARIO = window.DADOS_INVENTARIO || [];

  const IMAGENS = [
    ['Mapas mentais', 'Imagens/Mapas-Mentais/Mapa_Mental_Sindrome_de_Pandora.webp', 'Mapa mental — Síndrome de Pandora'],
    ['Mapas mentais', 'Imagens/Mapas-Mentais/Mapa Mental Estudo da Tese.png', 'Mapa mental — estudo da tese'],
    ['Mapas mentais', 'Imagens/Mapas-Mentais/Mapa_de_Pesquisa_Tese.jpeg', 'Mapa de pesquisa da tese'],
    ['Mapas mentais', 'Imagens/Mapas-Mentais/Complemento_tese.jpeg', 'Complemento da tese'],
    ['Cronogramas', 'Imagens/Cronogramas/Calendário_Artigo.jpeg', 'Calendário do artigo'],
    ['Fichamentos', 'Imagens/Fichamentos/FICHEIRO SMALL ADRENAL GLANDS IN CATS WITH FELINE INTERSTITIAL.png', 'Ficheiro — Small adrenal glands (#50)'],
    ['Fichamentos', 'Imagens/Fichamentos/Ficheiro_Stress in owned cats_behavioural .png', 'Ficheiro — Stress in owned cats'],
    ['Projeto IoT', 'Imagens/Projeto-IoT/pagina-1.png', 'Projeto IoT — caixa de areia'],
    ['Projeto IoT', 'Imagens/Projeto-IoT/pagina-2.png', 'Projeto IoT — fonte de água'],
    ['Projeto IoT', 'Imagens/Projeto-IoT/pagina-3.png', 'Projeto IoT — lista de componentes'],
    ['Ferramentas e método', 'Imagens/Ferramentas-e-Metodo/Sensores_IOT.png', 'Sensores IoT'],
    ['Ferramentas e método', 'Imagens/Ferramentas-e-Metodo/FerramentasIA.jpeg', 'Ferramentas de IA'],
    ['Ferramentas e método', 'Imagens/Ferramentas-e-Metodo/Ferramentas.jpeg', 'Ferramentas'],
    ['Ferramentas e método', 'Imagens/Ferramentas-e-Metodo/Ferramentas de Apoio.jpeg', 'Ferramentas de apoio'],
    ['Ferramentas e método', 'Imagens/Ferramentas-e-Metodo/Mendeley.jpeg', 'Mendeley'],
  ];

  // Ordem obrigatória: IoT → qualificação (artigo) → defesa da tese.
  const METAS_PADRAO = {
    iot:    { nome: '1. Elaborar os projetos IoT', unidade: 'tarefas', total: 12, feitoBase: 0, prazo: '2026-12-31', campo: 'tarefasIot' },
    artigo: { nome: '2. Qualificação — escrever o artigo', unidade: 'páginas', total: 20, feitoBase: 0, prazo: '2027-05-31', campo: 'pagArtigo' },
    tese:   { nome: '3. Apresentar a tese', unidade: 'páginas', total: 150, feitoBase: 0, prazo: '2027-09-30', prazoLimite: '2028-05-31', campo: 'pagTese' },
  };

  // ------------------------------------------------------------------ util
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));
  const esc = (t) => String(t).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const fmt = (n, d = 1) => (n == null || isNaN(n) ? '—' : Number(n).toLocaleString('pt-BR', { maximumFractionDigits: d }));
  const hoje = () => { const d = new Date(); d.setHours(0, 0, 0, 0); return d; };
  const parseData = (s) => { const [y, m, d] = s.split('-').map(Number); return new Date(y, m - 1, d); };
  const dataBR = (s) => parseData(s).toLocaleDateString('pt-BR');
  const semanasEntre = (a, b) => (b - a) / (7 * 864e5);

  function ler(key, padrao) {
    try { const v = JSON.parse(localStorage.getItem(key)); return v ?? padrao; } catch (e) { return padrao; }
  }
  function gravar(key, v) { try { localStorage.setItem(key, JSON.stringify(v)); } catch (e) { /* modo privado */ } }

  let registros = ler(STORE_KEY, []);
  let metas = Object.assign({}, METAS_PADRAO, ler(METAS_KEY, {}));
  const salvarRegistros = () => { registros.sort((a, b) => a.semana.localeCompare(b.semana)); gravar(STORE_KEY, registros); renderTudo(); };

  const escrita = (r) => (+r.pagArtigo || 0) + (+r.pagTese || 0);
  const METRICAS = {
    leitura: { nome: 'Páginas lidas', f: (r) => +r.paginasLidas || 0, cor: 'var(--blue-light)' },
    escrita: { nome: 'Páginas escritas', f: escrita, cor: 'var(--orange-primary)' },
    horas:   { nome: 'Horas de estudo', f: (r) => +r.horas || 0, cor: 'var(--pink-primary)' },
    iot:     { nome: 'Tarefas IoT', f: (r) => +r.tarefasIot || 0, cor: '#22c55e' },
  };
  let metricaAtual = 'leitura';

  const media = (a) => (a.length ? a.reduce((s, x) => s + x, 0) / a.length : null);
  const desvio = (a) => { if (a.length < 2) return 0; const m = media(a); return Math.sqrt(a.reduce((s, x) => s + (x - m) ** 2, 0) / (a.length - 1)); };

  // Φ(x) — aproximação de Abramowitz & Stegun 26.2.17
  function phi(x) {
    const t = 1 / (1 + 0.2316419 * Math.abs(x));
    const d = 0.3989423 * Math.exp(-x * x / 2);
    const p = d * t * (0.3193815 + t * (-0.3565638 + t * (1.781478 + t * (-1.821256 + t * 1.330274))));
    return x > 0 ? 1 - p : p;
  }

  function progressoMeta(k, usarLimite) {
    const m = usarLimite && metas[k].prazoLimite ? { ...metas[k], prazo: metas[k].prazoLimite } : metas[k];
    const feito = (+m.feitoBase || 0) + registros.reduce((s, r) => s + (+r[m.campo] || 0), 0);
    const falta = Math.max(0, m.total - feito);
    const semanas = Math.max(0, semanasEntre(hoje(), parseData(m.prazo)));
    const serie = registros.map((r) => +r[m.campo] || 0);
    let prob = null;
    if (falta === 0) prob = 1;
    else if (semanas <= 0) prob = 0;
    else if (serie.length >= 2) {
      const mu = media(serie), sd = Math.max(desvio(serie), mu * 0.15, 0.5);
      prob = 1 - phi((falta - semanas * mu) / (Math.sqrt(semanas) * sd));
    }
    return { ...m, feito, falta, semanas, pct: Math.min(1, feito / (m.total || 1)), prob, ritmoNecessario: semanas > 0 ? falta / semanas : null, ritmo: media(serie) };
  }

  // ---------------------------------------------------- páginas (rotas)
  function irPara(id, inicial) {
    const btn = $(`.tab-btn[data-tab="${id}"]`);
    if (!btn) return;
    $$('.tab-btn').forEach((b) => { b.classList.toggle('active', b === btn); b.setAttribute('aria-selected', b === btn); });
    $$('.tab-pane').forEach((p) => p.classList.toggle('active', p.id === id));
    if (!inicial && location.hash !== '#' + id) history.replaceState(null, '', '#' + id);
    const nav = btn.parentElement; if (nav.scrollWidth > nav.clientWidth) nav.scrollTo({ left: btn.offsetLeft - nav.clientWidth / 2 + btn.offsetWidth / 2, behavior: 'smooth' });
  }
  function initRotas() {
    $$('.tab-btn').forEach((b) => b.addEventListener('click', () => irPara(b.dataset.tab)));
    document.addEventListener('click', (e) => {
      const g = e.target.closest('[data-goto]');
      if (g) { fecharModal(); irPara(g.dataset.goto); window.scrollTo({ top: $('.tab-nav-wrapper').offsetTop - 80, behavior: 'smooth' }); }
    });
    window.addEventListener('hashchange', () => irPara(location.hash.slice(1)));
    irPara(location.hash.slice(1) && $(`.tab-btn[data-tab="${location.hash.slice(1)}"]`) ? location.hash.slice(1) : 'tab-painel', true);
    if ('scrollRestoration' in history) history.scrollRestoration = 'manual';
    if (location.hash) window.scrollTo(0, 0);
  }

  // ------------------------------------------------------------ janelas
  let modalAberto = null, focoAnterior = null;
  function abrirModal(id) {
    const m = document.getElementById(id);
    if (!m) return;
    fecharModal();
    focoAnterior = document.activeElement;
    m.hidden = false;
    requestAnimationFrame(() => m.classList.add('open'));
    document.body.style.overflow = 'hidden';
    modalAberto = m;
    $('.pn-modal-close', m).focus();
  }
  function fecharModal() {
    if (!modalAberto) return;
    const m = modalAberto; modalAberto = null;
    m.classList.remove('open');
    setTimeout(() => { m.hidden = true; }, 200);
    document.body.style.overflow = '';
    if (focoAnterior) focoAnterior.focus();
  }
  function initModais() {
    document.addEventListener('click', (e) => {
      const t = e.target.closest('[data-modal]');
      if (t) { abrirModal(t.dataset.modal); return; }
      if (e.target.closest('.pn-modal-close') || e.target.classList.contains('pn-modal')) fecharModal();
    });
    document.addEventListener('keydown', (e) => {
      if (!modalAberto) return;
      if (e.key === 'Escape') { fecharModal(); return; }
      if (modalAberto.id === 'modalImg') { if (e.key === 'ArrowRight') navLb(1); if (e.key === 'ArrowLeft') navLb(-1); }
    });
  }

  // ------------------------------------------------------------ galeria
  let galFiltro = 'Todas', galVisiveis = [], lbIdx = 0;
  function renderGaleriaLista() { galVisiveis = IMAGENS.filter((i) => galFiltro === 'Todas' || i[0] === galFiltro); }
  function renderGaleria() {
    const cats = ['Todas', ...new Set(IMAGENS.map((i) => i[0]))];
    $('#galFiltros').innerHTML = cats.map((c) => `<button class="filter-pill ${c === galFiltro ? 'active' : ''}" data-gal="${esc(c)}" type="button">${esc(c)}</button>`).join('');
    galVisiveis = IMAGENS.filter((i) => galFiltro === 'Todas' || i[0] === galFiltro);
    $('#pnGallery').innerHTML = galVisiveis.map((i, n) => `
      <figure class="pn-thumb" data-idx="${n}" tabindex="0" role="button" aria-label="Ampliar ${esc(i[2])}">
        <img src="${encodeURI(i[1])}" alt="${esc(i[2])}" loading="lazy" onerror="this.closest('figure').classList.add('pn-missing')">
        <figcaption><span>${esc(i[0])}</span>${esc(i[2])}</figcaption>
      </figure>`).join('');
    $('#galeriaCount').textContent = IMAGENS.length;
  }
  function abrirLb(n) { $('#modalImg').classList.remove('zoom'); lbIdx = n; const i = galVisiveis[n]; $('#lbImg').src = encodeURI(i[1]); $('#lbImg').alt = i[2]; $('#lbCap').textContent = `${i[2]} · ${n + 1}/${galVisiveis.length}`; if (!modalAberto) abrirModal('modalImg'); }
  function navLb(d) { abrirLb((lbIdx + d + galVisiveis.length) % galVisiveis.length); }
  function abrirDestaque(f) {
    galVisiveis = $$(`.pn-open-img[data-grupo="${f.dataset.grupo}"]`).map((x) => ['', x.dataset.src, x.dataset.cap]);
    abrirLb($$(`.pn-open-img[data-grupo="${f.dataset.grupo}"]`).indexOf(f));
  }
  function initGaleria() {
    document.addEventListener('click', (e) => { const f = e.target.closest('.pn-open-img'); if (f) abrirDestaque(f); });
    document.addEventListener('keydown', (e) => { const f = e.target.closest && e.target.closest('.pn-open-img'); if (f && (e.key === 'Enter' || e.key === ' ')) { e.preventDefault(); abrirDestaque(f); } });
    $('#galFiltros').addEventListener('click', (e) => { const b = e.target.closest('[data-gal]'); if (b) { galFiltro = b.dataset.gal; renderGaleria(); } });
    $('#pnGallery').addEventListener('click', (e) => { const f = e.target.closest('.pn-thumb'); if (f) { renderGaleriaLista(); abrirLb(+f.dataset.idx); } });
    $('#pnGallery').addEventListener('keydown', (e) => { const f = e.target.closest('.pn-thumb'); if (f && (e.key === 'Enter' || e.key === ' ')) { e.preventDefault(); abrirLb(+f.dataset.idx); } });
    $('#lbImg').addEventListener('click', () => $('#modalImg').classList.toggle('zoom'));
    $('.pn-lb-prev').addEventListener('click', () => navLb(-1));
    $('.pn-lb-next').addEventListener('click', () => navLb(1));
  }

  // --------------------------------------------------------------- KPIs
  function kpi(icone, valor, rotulo, detalhe, tendencia) {
    const t = tendencia == null ? '' : `<span class="pn-trend ${tendencia >= 0 ? 'up' : 'down'}">${tendencia >= 0 ? '▲' : '▼'} ${fmt(Math.abs(tendencia), 0)}%</span>`;
    return `<div class="pn-kpi">${icone ? `<img class="pn-kpi-img" src="${encodeURI(icone)}" alt="" loading="lazy">` : ''}<div class="pn-kpi-top">${t}</div><div class="pn-kpi-val">${valor}</div><div class="pn-kpi-lbl">${rotulo}</div><div class="pn-kpi-det">${detalhe}</div></div>`;
  }
  function tendencia(f) {
    if (registros.length < 2) return null;
    const ult = f(registros[registros.length - 1]);
    const ant = media(registros.slice(-5, -1).map(f));
    return ant ? ((ult - ant) / ant) * 100 : null;
  }
  function renderKpis() {
    const u4 = registros.slice(-4);
    const fichInv = INVENTARIO.filter((a) => /fichamento concluido/i.test(a.status || '')).length;
    const fichReg = registros.reduce((s, r) => s + (+r.fichamentos || 0), 0);
    const prazo = metas.tese.prazo;
    const dias = Math.round((parseData(prazo) - hoje()) / 864e5);
    let constancia = null;
    if (registros.length) {
      const total = Math.floor(semanasEntre(parseData(registros[0].semana), hoje())) + 1;
      constancia = Math.min(1, registros.length / Math.max(1, total));
    }
    const probs = Object.keys(metas).map(progressoMeta);
    const pq = probs.every((p) => p.prob != null) ? probs.reduce((s, p) => s * p.prob, 1) : null;
    $('#pnKpis').innerHTML = [
      kpi('Imagens/Mapas-Mentais/Mapa_de_Pesquisa_Tese.jpeg', fmt(media(u4.map(METRICAS.leitura.f))), 'Leitura · pág./semana', 'média das últimas 4 semanas', tendencia(METRICAS.leitura.f)),
      kpi('Imagens/Mapas-Mentais/Mapa Mental Estudo da Tese.png', fmt(media(u4.map(escrita))), 'Escrita · pág./semana', 'artigo + tese', tendencia(escrita)),
      kpi('Imagens/Fichamentos/FICHEIRO SMALL ADRENAL GLANDS IN CATS WITH FELINE INTERSTITIAL.png', fichInv + fichReg, 'Fichamentos', `${fichInv} no inventário + ${fichReg} registrados aqui`),
      kpi('Imagens/Mapas-Mentais/Complemento_tese.jpeg', constancia == null ? '—' : fmt(constancia * 100, 0) + '%', 'Constância', `${registros.length} semana(s) registrada(s)`),
      kpi('Imagens/Cronogramas/Calendário_Artigo.jpeg', dias >= 0 ? dias : 'vencido', 'Dias até a defesa', `prazo: ${dataBR(prazo)}`),
      kpi('Imagens/Projeto-IoT/pagina-1.png', pq == null ? '—' : fmt(pq * 100, 0) + '%', 'Probabilidade de qualificar', pq == null ? 'registre ao menos 2 semanas' : 'IoT × qualificação × tese'),
    ].join('');
  }

  // ------------------------------------------------------------ gráfico
  function renderGrafico() {
    const M = METRICAS[metricaAtual];
    const box = $('#pnChart');
    const dados = registros.slice(-16);
    if (!dados.length) {
      box.innerHTML = `<div class="pn-empty">Nenhuma semana registrada ainda.<br><button class="pn-btn pn-btn-primary" data-goto="tab-registro" type="button">Registrar a primeira semana</button></div>`;
      $('#pnChartLegend').textContent = '';
      return;
    }
    const W = 640, H = 260, pl = 40, pr = 12, pt = 16, pb = 34;
    const vals = dados.map(M.f);
    let alvo = null;
    if (metricaAtual === 'escrita') alvo = (progressoMeta('artigo').ritmoNecessario || 0) + (progressoMeta('tese').ritmoNecessario || 0);
    if (metricaAtual === 'iot') alvo = progressoMeta('iot').ritmoNecessario;
    const max = Math.max(1, ...vals, alvo || 0) * 1.1;
    const bw = (W - pl - pr) / dados.length;
    const y = (v) => pt + (H - pt - pb) * (1 - v / max);
    const mm = vals.map((_, i) => media(vals.slice(Math.max(0, i - 3), i + 1)));
    let svg = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${M.nome} por semana">`;
    for (let g = 0; g <= 4; g++) { const v = (max / 4) * g; svg += `<line x1="${pl}" x2="${W - pr}" y1="${y(v)}" y2="${y(v)}" class="pn-grid"/><text x="${pl - 6}" y="${y(v) + 4}" text-anchor="end" class="pn-axis">${fmt(v, 0)}</text>`; }
    dados.forEach((r, i) => {
      const x = pl + i * bw + bw * 0.18, w = bw * 0.64;
      svg += `<rect x="${x}" y="${y(vals[i])}" width="${w}" height="${Math.max(0, y(0) - y(vals[i]))}" rx="4" fill="${M.cor}"><title>${dataBR(r.semana)}: ${fmt(vals[i])}</title></rect>`;
      if (dados.length <= 10 || i % 2 === 0) svg += `<text x="${x + w / 2}" y="${H - 12}" text-anchor="middle" class="pn-axis">${dataBR(r.semana).slice(0, 5)}</text>`;
    });
    svg += `<polyline fill="none" stroke="var(--text-main)" stroke-width="2" stroke-dasharray="1 0" points="${mm.map((v, i) => `${pl + i * bw + bw / 2},${y(v)}`).join(' ')}"/>`;
    if (alvo) svg += `<line x1="${pl}" x2="${W - pr}" y1="${y(alvo)}" y2="${y(alvo)}" stroke="var(--pink-primary)" stroke-width="2" stroke-dasharray="6 4"/><text x="${W - pr}" y="${y(alvo) - 6}" text-anchor="end" class="pn-axis" fill="var(--pink-primary)">ritmo necessário ${fmt(alvo)}</text>`;
    box.innerHTML = svg + '</svg>';
    $('#pnChartLegend').innerHTML = `Barras: ${M.nome.toLowerCase()} · linha clara: média móvel de 4 semanas${alvo ? ' · tracejado rosa: ritmo necessário para cumprir o prazo' : ''}.`;
  }

  // ------------------------------------------------------ probabilidade
  function corProb(p) { return p >= 0.7 ? 'var(--ok, #22c55e)' : p >= 0.4 ? 'var(--orange-primary)' : '#ef4444'; }
  function renderProb() {
    const ps = Object.keys(metas).map(progressoMeta);
    $('#pnProb').innerHTML = ps.map((p) => `
      <div class="pn-prob-row">
        <div class="pn-prob-head"><strong>${esc(p.nome)}</strong><span style="color:${p.prob == null ? 'var(--text-dim)' : corProb(p.prob)}">${p.prob == null ? 'dados insuficientes' : fmt(p.prob * 100, 0) + '%'}</span></div>
        <div class="pn-bar"><div style="width:${p.pct * 100}%"></div></div>
        <small>${fmt(p.feito)} de ${fmt(p.total)} ${p.unidade} · faltam ${fmt(p.falta)} em ${fmt(p.semanas)} semana(s) · ritmo atual ${fmt(p.ritmo)} / necessário ${p.ritmoNecessario == null ? '—' : fmt(p.ritmoNecessario)} por semana</small>
        ${p.prazoLimite ? `<small>Prazo limite ${dataBR(p.prazoLimite)}: ${(() => { const q = progressoMeta('tese', true).prob; return q == null ? 'dados insuficientes' : fmt(q * 100, 0) + '%'; })()}</small>` : ''}
      </div>`).join('') + ordemAviso() +
      (ps.some((p) => p.semanas <= 1 && p.falta > 0) ? `<p class="pn-warn">Algum prazo vence em menos de uma semana. Revise as datas em <a href="#tab-metas">Metas</a>.</p>` : '');
  }

  function ordemAviso() {
    const { iot, artigo, tese } = metas;
    return iot.prazo < artigo.prazo && artigo.prazo < tese.prazo ? ''
      : '<p class="pn-warn">Prazos fora da ordem: os projetos IoT precisam terminar antes da qualificação (artigo), e a qualificação antes da tese. Revise em <a href="#tab-metas">Metas</a>.</p>';
  }

  // ----------------------------------------------------- acervo e uso
  function barras(itens) {
    const max = Math.max(1, ...itens.map((i) => i[1]));
    return `<div class="pn-hbars">${itens.map(([n, v, c]) => `<div class="pn-hbar"><span>${esc(n)}</span><div><i style="width:${(v / max) * 100}%;background:${c}"></i></div><b>${v}</b></div>`).join('')}</div>`;
  }
  function renderAcervo() {
    const c = (f) => INVENTARIO.filter(f).length;
    $('#pnAcervo').innerHTML = barras([
      ['Registros', INVENTARIO.length, 'var(--blue-light)'],
      ['Núcleo 1', c((a) => /nucleo 1/i.test(a.nucleo)), 'var(--blue-soft)'],
      ['Núcleo 2', c((a) => /nucleo 2/i.test(a.nucleo)), 'var(--pink-soft)'],
      ['Ler primeiro', c((a) => a.fase === 'Ler primeiro'), 'var(--orange-primary)'],
      ['Com arquivo', c((a) => a.arquivo), '#22c55e'],
      ['Fichados', c((a) => /fichamento concluido/i.test(a.status)), '#16a34a'],
      ['Não obtidos', c((a) => /nao obtido/i.test(a.status)), 'var(--gray-subtle)'],
    ]) + `<p class="pn-muted">Fonte: <code>dados_inventario.js</code> (inventário de 64 registros). Agrupamento por núcleo é proposto, não declarado por autor.</p>`;
  }
  function renderUso() {
    if (!registros.length) { $('#pnUso').innerHTML = '<p class="pn-muted">Sem registros ainda.</p>'; return; }
    const soma = (f) => registros.reduce((s, r) => s + f(r), 0);
    const horas = soma(METRICAS.horas.f), lidas = soma(METRICAS.leitura.f), escritas = soma(escrita);
    $('#pnUso').innerHTML = barras([
      ['Horas totais', horas, 'var(--pink-primary)'],
      ['Páginas lidas', lidas, 'var(--blue-light)'],
      ['Páginas escritas', escritas, 'var(--orange-primary)'],
      ['Artigos lidos', soma((r) => +r.artigosLidos || 0), 'var(--blue-soft)'],
      ['Tarefas IoT', soma(METRICAS.iot.f), '#22c55e'],
    ]) + `<p class="pn-muted">Produtividade: ${fmt(horas ? lidas / horas : null)} pág. lidas/h · ${fmt(horas ? escritas / horas : null)} pág. escritas/h · razão leitura:escrita ${escritas ? fmt(lidas / escritas) + ':1' : '—'}.</p>`;
  }

  // ----------------------------------------------------------- registro
  function renderTabela() {
    const t = $('#pnTabela');
    if (!registros.length) { t.innerHTML = '<tbody><tr><td>Nenhuma semana registrada.</td></tr></tbody>'; return; }
    t.innerHTML = `<thead><tr><th>Semana</th><th>Pág. lidas</th><th>Artigos</th><th>Fichamentos</th><th>Artigo (pág.)</th><th>Tese (pág.)</th><th>IoT</th><th>Horas</th><th>Obs.</th><th></th></tr></thead><tbody>` +
      registros.slice().reverse().map((r) => `<tr><td>${dataBR(r.semana)}</td><td>${fmt(r.paginasLidas)}</td><td>${fmt(r.artigosLidos)}</td><td>${fmt(r.fichamentos)}</td><td>${fmt(r.pagArtigo)}</td><td>${fmt(r.pagTese)}</td><td>${fmt(r.tarefasIot)}</td><td>${fmt(r.horas)}</td><td>${esc(r.obs || '')}</td><td><button class="pn-btn pn-btn-sm" data-edit="${r.semana}" type="button">Editar</button> <button class="pn-btn pn-btn-sm pn-btn-danger" data-del="${r.semana}" type="button">Excluir</button></td></tr>`).join('') + '</tbody>';
  }
  function segundaDe(d) { const x = new Date(d); const dia = (x.getDay() + 6) % 7; x.setDate(x.getDate() - dia); return x.toISOString().slice(0, 10); }
  function initRegistro() {
    const f = $('#pnForm');
    f.semana.value = segundaDe(hoje());
    f.addEventListener('submit', (e) => {
      e.preventDefault();
      const r = Object.fromEntries(new FormData(f));
      r.semana = segundaDe(parseData(r.semana));
      ['paginasLidas', 'artigosLidos', 'fichamentos', 'pagArtigo', 'pagTese', 'tarefasIot', 'horas'].forEach((k) => { r[k] = Math.max(0, +r[k] || 0); });
      registros = registros.filter((x) => x.semana !== r.semana).concat(r);
      salvarRegistros();
      toast(`Semana de ${dataBR(r.semana)} salva.`);
    });
    f.addEventListener('reset', () => setTimeout(() => { f.semana.value = segundaDe(hoje()); }));
    $('#pnTabela').addEventListener('click', (e) => {
      const d = e.target.closest('[data-del]'), ed = e.target.closest('[data-edit]');
      if (d && confirm(`Apagar a semana de ${dataBR(d.dataset.del)}?`)) { registros = registros.filter((x) => x.semana !== d.dataset.del); salvarRegistros(); }
      if (ed) { const r = registros.find((x) => x.semana === ed.dataset.edit); Object.keys(r).forEach((k) => { if (f[k]) f[k].value = r[k]; }); f.scrollIntoView({ behavior: 'smooth' }); }
    });
    $('#pnExport').addEventListener('click', () => {
      const blob = new Blob([JSON.stringify({ exportado: new Date().toISOString(), metas, registros }, null, 2)], { type: 'application/json' });
      const a = Object.assign(document.createElement('a'), { href: URL.createObjectURL(blob), download: 'acompanhamento_semanal.json' });
      a.click(); URL.revokeObjectURL(a.href);
    });
    $('#pnImport').addEventListener('change', async (e) => {
      const file = e.target.files[0]; if (!file) return;
      try {
        const j = JSON.parse(await file.text());
        if (!Array.isArray(j.registros)) throw new Error('formato');
        registros = j.registros; if (j.metas) { metas = Object.assign({}, METAS_PADRAO, j.metas); gravar(METAS_KEY, metas); renderMetasForm(); }
        salvarRegistros(); toast(`${registros.length} semana(s) importada(s).`);
      } catch (err) { toast('Arquivo inválido.'); }
      e.target.value = '';
    });
    $('#pnClear').addEventListener('click', () => { if (confirm('Apagar todos os registros semanais deste navegador? Exporte antes se quiser guardar.')) { registros = []; salvarRegistros(); } });
  }

  // -------------------------------------------------------------- metas
  function renderMetasForm() {
    $('#pnMetasForm').innerHTML = Object.entries(metas).map(([k, m]) => `
      <fieldset class="pn-fieldset"><legend>${esc(m.nome)}</legend>
        <label>Meta total (${m.unidade})<input type="number" min="1" step="1" data-k="${k}" data-f="total" value="${m.total}"></label>
        <label>Já feito antes dos registros<input type="number" min="0" step="0.5" data-k="${k}" data-f="feitoBase" value="${m.feitoBase}"></label>
        <label>Prazo<input type="date" data-k="${k}" data-f="prazo" value="${m.prazo}"></label>
        ${m.prazoLimite ? `<label>Prazo limite<input type="date" data-k="${k}" data-f="prazoLimite" value="${m.prazoLimite}"></label>` : ''}
      </fieldset>`).join('') + `<p class="pn-muted pn-span3">Os valores iniciais são apenas exemplos editáveis — ajuste-os à sua realidade e às normas do programa.</p>`;
  }
  function renderTimeline() {
    $('#pnTimeline').innerHTML = Object.keys(metas).map((k, i) => {
      const p = progressoMeta(k);
      return `<div class="pn-tl-item"><div class="pn-tl-dot">${i + 1}</div><div class="pn-tl-body">
        <div class="pn-prob-head"><strong>${esc(p.nome)}</strong><span>${dataBR(p.prazo)}${p.prazoLimite ? ' (limite ' + dataBR(p.prazoLimite) + ')' : ''}</span></div>
        <div class="pn-bar"><div style="width:${p.pct * 100}%"></div></div>
        <small>${fmt(p.pct * 100, 0)}% concluído · ${p.prob == null ? 'probabilidade: dados insuficientes' : 'probabilidade: ' + fmt(p.prob * 100, 0) + '%'}</small></div></div>`;
    }).join('') + ordemAviso();
  }
  function initMetas() {
    renderMetasForm();
    $('#pnMetasForm').addEventListener('change', (e) => {
      const i = e.target; if (!i.dataset.k) return;
      metas[i.dataset.k] = { ...metas[i.dataset.k], [i.dataset.f]: i.type === 'number' ? Math.max(0, +i.value || 0) : i.value };
      gravar(METAS_KEY, metas); renderTudo();
    });
  }

  // -------------------------------------------------------------- toast
  function toast(msg) {
    let t = $('#pnToast');
    if (!t) { t = Object.assign(document.createElement('div'), { id: 'pnToast', className: 'pn-toast' }); t.setAttribute('role', 'status'); document.body.appendChild(t); }
    t.textContent = msg; t.classList.add('show'); clearTimeout(t._h); t._h = setTimeout(() => t.classList.remove('show'), 2600);
  }

  function renderIotCusto() {
    const el = $('#pnIotChart'); if (!el) return;
    const itens = [['ESP32-S3-CAM', 120], ['INMP441', 57.8], ['DS3231 (opcional)', 47.98], ['AHT10', 23.8], ['Célula 5 kg', 22.9], ['Célula 20 kg', 21.9], ['HX711', 11.8]];
    el.innerHTML = '<p class="pn-muted" style="margin-bottom:8px">Participação de cada componente no custo total (R$ 306,18)</p><div class="pn-hbars">' +
      itens.map(([n, v]) => `<div class="pn-hbar"><span>${n}</span><div><i style="width:${(v / 120) * 100}%;background:var(--pink-primary)"></i></div><b>${fmt((v / 306.18) * 100, 0)}%</b></div>`).join('') + '</div>';
  }

  // ------------------------------------------------------------- PDFs
  const PDFS = window.DADOS_PDFS || [];
  let pdfPasta = 'Todas', pdfTexto = '';
  function renderPdfs() {
    const pastas = ['Todas', ...new Set(PDFS.map((d) => d.pasta))];
    $('#pdfFiltros').innerHTML = pastas.map((c) => `<button class="filter-pill ${c === pdfPasta ? 'active' : ''}" data-pasta="${esc(c)}" type="button">${esc(c.replace(/^PDF\//, ''))}</button>`).join('');
    const t = pdfTexto.toLowerCase();
    const lista = PDFS.filter((d) => (pdfPasta === 'Todas' || d.pasta === pdfPasta) && (d.nome + ' ' + d.pasta).toLowerCase().includes(t));
    const grupos = {};
    lista.forEach((d) => (grupos[d.pasta] = grupos[d.pasta] || []).push(d));
    $('#pdfLista').innerHTML = Object.entries(grupos).map(([g, itens]) => `
      <div class="content-card"><h3 class="card-title">${esc(g)} <small class="pn-muted">(${itens.length})</small></h3>
      <div class="pn-pdfs">${itens.map((d) => `<div class="pn-pdf"><span class="pn-pdf-ico">PDF</span><div><strong>${esc(d.nome)}</strong><small>${fmt(d.kb / 1024)} MB</small></div>
        ${d.publico === false ? '<span class="pn-muted" style="font-size:.75rem">Disponível só no cofre</span>' : `<div class="pn-actions"><button class="pn-btn pn-btn-sm" data-pdf="${esc(d.arquivo)}" data-nome="${esc(d.nome)}" type="button">Ler aqui</button><a class="pn-btn pn-btn-sm" href="${encodeURI(d.arquivo)}" target="_blank" rel="noopener">Nova aba ↗</a></div>`}</div>`).join('')}</div></div>`).join('') || '<p class="pn-muted">Nenhum PDF encontrado.</p>';
    $('#pdfContagem').textContent = `${lista.length} de ${PDFS.length} PDFs`;
    $('#pdfBadge').textContent = PDFS.length;
  }
  function initPdfs() {
    if (!$('#pdfLista')) return;
    $('#pdfFiltros').addEventListener('click', (e) => { const b = e.target.closest('[data-pasta]'); if (b) { pdfPasta = b.dataset.pasta; renderPdfs(); } });
    $('#pdfBusca').addEventListener('input', (e) => { pdfTexto = e.target.value; renderPdfs(); });
    document.addEventListener('click', (e) => {
      const b = e.target.closest('[data-pdf]'); if (!b) return;
      const url = encodeURI(b.dataset.pdf);
      $('#pdfTitulo').textContent = b.dataset.nome; $('#pdfFrame').src = url; $('#pdfNovaAba').href = url;
      abrirModal('modalPdf');
    });
    renderPdfs();
  }

  // --------------------------------------------------------- Pomodoro
  function initPomodoro() {
    const el = $('#pomoTempo'); if (!el) return;
    let resta = 25 * 60, timer = null, modo = 'foco';
    const hojeK = 'pandora.pomo.' + new Date().toISOString().slice(0, 10);
    let ciclos = +ler(hojeK, 0);
    const pinta = () => {
      el.textContent = String(Math.floor(resta / 60)).padStart(2, '0') + ':' + String(resta % 60).padStart(2, '0');
      $('#pomoCiclos').textContent = ciclos + ' bloco(s) concluído(s) hoje';
    };
    const para = () => { clearInterval(timer); timer = null; $('#pomoIniciar').textContent = 'Continuar'; };
    const tick = () => {
      if (--resta > 0) return pinta();
      para();
      if (modo === 'foco') { ciclos++; gravar(hojeK, ciclos); toast('Bloco concluído. Faça uma pausa.'); }
      else toast('Pausa encerrada. Hora de voltar.');
      modo = 'foco'; resta = 25 * 60; $('#pomoIniciar').textContent = 'Iniciar'; pinta();
    };
    $('#pomoIniciar').addEventListener('click', () => { if (timer) return para(); timer = setInterval(tick, 1000); $('#pomoIniciar').textContent = 'Pausar'; });
    $('#pomoPausa').addEventListener('click', () => { para(); modo = 'pausa'; resta = 5 * 60; $('#pomoIniciar').textContent = 'Iniciar pausa'; pinta(); });
    $('#pomoZerar').addEventListener('click', () => { para(); modo = 'foco'; resta = 25 * 60; $('#pomoIniciar').textContent = 'Iniciar'; pinta(); });
    pinta();
  }

  function renderTudo() { renderKpis(); renderGrafico(); renderProb(); renderAcervo(); renderUso(); renderTabela(); renderTimeline(); }

  document.addEventListener('DOMContentLoaded', () => {
    initRotas(); initModais(); renderIotCusto(); initPdfs(); initPomodoro(); initGaleria(); renderGaleria(); initRegistro(); initMetas();
    $$('.pn-seg-btn').forEach((b) => b.addEventListener('click', () => {
      $$('.pn-seg-btn').forEach((x) => x.classList.toggle('active', x === b)); metricaAtual = b.dataset.metric; renderGrafico();
    }));
    renderTudo();
  });
})();
