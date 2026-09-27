/* ==========================================================================
   Painel de acompanhamento — páginas, janelas, KPIs, gráfico e galeria
   Sem dependências externas: funciona abrindo o index.html direto do disco.
   ========================================================================== */
(function () {
  'use strict';

  const STORE_KEY = 'pandora.registros.v1';
  const METAS_KEY = 'pandora.metas.v4';
  const INVENTARIO = Array.isArray(window.DADOS_INVENTARIO) ? window.DADOS_INVENTARIO : [];

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
    const CRONOGRAMA_KEY = 'pandora.cronograma.v1';
  const CRONOGRAMA_PADRAO = [
    {
      id: 'crono-1',
      nome: 'Revisão Bibliográfica Sistemática & Fichamentos',
      cat: 'pesquisa',
      catNome: 'Pesquisa',
      prazo: '2026-10-31',
      obs: 'Núcleo 1 (Fisiologia/HHA) e Núcleo 2 (Tecnologia/Comportamento), atingindo as 34 fontes prioritárias.',
      concluido: true,
      dataConclusao: '2026-09-25'
    },
    {
      id: 'crono-2',
      nome: 'Especificação e Arquitetura de Sensores IoT',
      cat: 'iot',
      catNome: 'Projeto IoT',
      prazo: '2026-11-30',
      obs: 'Dimensionamento de células de carga, microfone INMP441, AHT10 e placa ESP32-S3-CAM.',
      concluido: false,
      dataConclusao: null
    },
    {
      id: 'crono-3',
      nome: 'Montagem e Calibração dos Dispositivos (Bancada IoT)',
      cat: 'iot',
      catNome: 'Projeto IoT',
      prazo: '2026-12-31',
      obs: 'Prototipagem da caixa de areia instrumentada e da fonte de água com pesagem contínua.',
      concluido: false,
      dataConclusao: null
    },
    {
      id: 'crono-4',
      nome: 'Redação da Seção Teórica e Metodologia do Artigo',
      cat: 'artigo',
      catNome: 'Artigo Científico',
      prazo: '2027-02-28',
      obs: 'Fundamentação: ruptura conceitual de FUS à Síndrome de Pandora e lacuna de sensoriamento contínuo.',
      concluido: false,
      dataConclusao: null
    },
    {
      id: 'crono-5',
      nome: 'Coleta Experimental de Dados Comportamentais',
      cat: 'pesquisa',
      catNome: 'Experimentos',
      prazo: '2027-04-15',
      obs: 'Registro contínuo de frequência de uso, tempo de permanência, peso e eventos externos.',
      concluido: false,
      dataConclusao: null
    },
    {
      id: 'crono-6',
      nome: 'Exame de Qualificação de Doutorado (UFC)',
      cat: 'artigo',
      catNome: 'Qualificação',
      prazo: '2027-05-31',
      obs: 'Apresentação do artigo submetido e qualificação formal do projeto de pesquisa perante a banca.',
      concluido: false,
      dataConclusao: null
    },
    {
      id: 'crono-7',
      nome: 'Desenvolvimento do Pipeline de IA e Análise de Padrões',
      cat: 'ia',
      catNome: 'Inteligência Artificial',
      prazo: '2027-07-31',
      obs: 'Modelos para classificação de eventos e detecção precoce de "sickness behaviors" em felinos.',
      concluido: false,
      dataConclusao: null
    },
    {
      id: 'crono-8',
      nome: 'Redação Completa da Tese de Doutorado',
      cat: 'tese',
      catNome: 'Tese',
      prazo: '2027-08-31',
      obs: 'Consolidação de todos os capítulos: introdução, revisão, metodologia experimental, resultados e discussão.',
      concluido: false,
      dataConclusao: null
    },
    {
      id: 'crono-9',
      nome: 'Depósito e Defesa da Tese de Doutorado',
      cat: 'tese',
      catNome: 'Defesa',
      prazo: '2027-09-30',
      prazoLimite: '2028-05-31',
      obs: 'Homologação final e defesa pública perante a comissão examinadora do Programa na UFC.',
      concluido: false,
      dataConclusao: null
    }
  ];

  let cronograma = lerArray(CRONOGRAMA_KEY, CRONOGRAMA_PADRAO)
    .filter((item) => item && typeof item === 'object' && item.id && item.nome && item.prazo);
  if (!cronograma.length) cronograma = JSON.parse(JSON.stringify(CRONOGRAMA_PADRAO));
  let filtroCronoAtual = 'todos';

  // Gantt helpers (module-level so initGantt can read after each renderGantt)
  let gCS = null, gTotalMs = 0;
  const CAT_C = { pesquisa: '#6366f1', iot: '#f59e0b', artigo: '#10b981', ia: '#8b5cf6', tese: '#ef4444', geral: '#64748b' };
  function gMs(iso) { return new Date(iso + 'T12:00:00').getTime(); }
  function gIni(e, i) {
    if (e.inicio) return e.inicio;
    const d = new Date(e.prazo + 'T12:00:00');
    d.setDate(1);
    d.setMonth(d.getMonth() - 1);
    return d.toISOString().slice(0, 10);
  }

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
  function lerArray(key, padrao) {
    const v = ler(key, padrao);
    return Array.isArray(v) ? v : JSON.parse(JSON.stringify(padrao));
  }
  function lerObjeto(key) {
    const v = ler(key, {});
    return v && typeof v === 'object' && !Array.isArray(v) ? v : {};
  }
  function gravar(key, v) { try { localStorage.setItem(key, JSON.stringify(v)); } catch (e) { /* modo privado */ } }

  // Semanas: derivadas dos dados do cofre + automáticas (dados_progresso.js) + complemento manual.
  // Fichamentos e artigos lidos são calculados dos dados_fichamentos.js e dados_leituras.js.
  // Um valor digitado (> 0) prevalece sobre o automático; horas, IoT e páginas são só manuais.
  const CAMPOS = ['paginasLidas', 'artigosLidos', 'fichamentos', 'pagArtigo', 'pagTese', 'tarefasIot', 'horas'];
  const autoBruto = window.DADOS_PROGRESSO && window.DADOS_PROGRESSO.semanas;
  const AUTO = Array.isArray(autoBruto) ? autoBruto : [];
  let manuais = lerArray(STORE_KEY, [])
    .filter((item) => item && typeof item === 'object' && typeof item.semana === 'string');
  let registros = [];
  function getMondayISO(iso) {
    const d = new Date(iso.slice(0, 10) + 'T12:00:00');
    const offset = (d.getDay() + 6) % 7;
    d.setDate(d.getDate() - offset);
    return d.toISOString().slice(0, 10);
  }
  function derivarDosDados() {
    const fichMap = {}, leitMap = {};
    const fichamentosBrutos = window.DADOS_FICHAMENTOS && window.DADOS_FICHAMENTOS.fichamentos;
    const fichamentos = Array.isArray(fichamentosBrutos) ? fichamentosBrutos : [];
    const leituras = Array.isArray(window.DADOS_LEITURAS) ? window.DADOS_LEITURAS : [];
    fichamentos.forEach((f) => {
      if (!f.data) return;
      const s = getMondayISO(f.data);
      fichMap[s] = (fichMap[s] || 0) + 1;
    });
    leituras.forEach((l) => {
      if (!l.eu_li) return;
      const s = getMondayISO(l.eu_li);
      leitMap[s] = (leitMap[s] || 0) + 1;
    });
    return { fichMap, leitMap };
  }
  function mesclar() {
    const { fichMap, leitMap } = derivarDosDados();
    const mapa = {};
    AUTO.forEach((a) => {
      mapa[a.semana] = { semana: a.semana, obs: '', auto: a };
      CAMPOS.forEach((k) => { mapa[a.semana][k] = +a[k] || 0; });
    });
    const semanasDerivadas = new Set([...Object.keys(fichMap), ...Object.keys(leitMap)]);
    semanasDerivadas.forEach((s) => {
      if (!mapa[s]) { mapa[s] = { semana: s, obs: '' }; CAMPOS.forEach((k) => { mapa[s][k] = 0; }); }
      if (fichMap[s] != null) mapa[s].fichamentos = fichMap[s];
      if (leitMap[s] != null) mapa[s].artigosLidos = leitMap[s];
      mapa[s].derivado = true;
    });
    manuais.forEach((m) => {
      const r = mapa[m.semana] || (mapa[m.semana] = { semana: m.semana, obs: '' });
      CAMPOS.forEach((k) => { if (+m[k] > 0) r[k] = +m[k]; else if (r[k] == null) r[k] = 0; });
      if (m.obs) r.obs = m.obs;
      r.manual = true;
    });
    registros = Object.values(mapa).sort((a, b) => a.semana.localeCompare(b.semana));
  }
  mesclar();
  const metasSalvas = lerObjeto(METAS_KEY);
  let metas = Object.fromEntries(Object.entries(METAS_PADRAO).map(([k, padrao]) => {
    const salva = metasSalvas[k];
    return [k, { ...padrao, ...(salva && typeof salva === 'object' && !Array.isArray(salva) ? salva : {}) }];
  }));
  const salvarRegistros = () => { manuais.sort((a, b) => a.semana.localeCompare(b.semana)); gravar(STORE_KEY, manuais); mesclar(); renderTudo(); };

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
    if (falta === 0 || m.concluidoManual) prob = 1;
    else if (semanas <= 0) prob = 0;
    else if (serie.length >= 2) {
      const mu = media(serie), sd = Math.max(desvio(serie), mu * 0.15, 0.5);
      prob = 1 - phi((falta - semanas * mu) / (Math.sqrt(semanas) * sd));
    }
    const pct = m.concluidoManual ? 1 : Math.min(1, feito / (m.total || 1));
    return { ...m, feito, falta, semanas, pct, prob, ritmoNecessario: semanas > 0 ? falta / semanas : null, ritmo: media(serie) };
  }

  // ---------------------------------------------------- páginas (rotas)
  function irPara(id, inicial) {
    const pane = document.getElementById(id);
    const btn = $(`.tab-btn[data-tab="${id}"]`);
    if (!pane) return;
    $$('.tab-btn').forEach((b) => { b.classList.toggle('active', b === btn); b.setAttribute('aria-selected', b === btn); });
    $$('.tab-pane').forEach((p) => p.classList.toggle('active', p.id === id));
    if (!inicial && location.hash !== '#' + id) history.replaceState(null, '', '#' + id);
    if (btn) {
      const nav = btn.parentElement;
      if (nav && nav.scrollWidth > nav.clientWidth) nav.scrollTo({ left: btn.offsetLeft - nav.clientWidth / 2 + btn.offsetWidth / 2, behavior: 'smooth' });
    }
  }
  function initRotas() {
    $$('.tab-btn').forEach((b) => b.addEventListener('click', () => irPara(b.dataset.tab)));
    document.addEventListener('click', (e) => {
      const g = e.target.closest('[data-goto]');
      if (g) {
        fecharModal();
        irPara(g.dataset.goto);
        if (g.dataset.filterNucleo) {
          const pill = $(`.filter-pill[data-filter="${g.dataset.filterNucleo}"]`);
          if (pill) pill.click();
        }
        const nav = $('.tab-nav-wrapper');
        if (nav) window.scrollTo({ top: Math.max(0, nav.offsetTop - 80), behavior: 'smooth' });
      }
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
  window.abrirModal = abrirModal;
  window.fecharModal = fecharModal;
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
    if (!$('#galFiltros') || !$('#pnGallery')) return;
    const cats = ['Todas', ...new Set(IMAGENS.map((i) => i[0]))];
    $('#galFiltros').innerHTML = cats.map((c) => `<button class="filter-pill ${c === galFiltro ? 'active' : ''}" data-gal="${esc(c)}" type="button">${esc(c)}</button>`).join('');
    galVisiveis = IMAGENS.filter((i) => galFiltro === 'Todas' || i[0] === galFiltro);
    $('#pnGallery').innerHTML = galVisiveis.map((i, n) => `
      <figure class="pn-thumb" data-idx="${n}" tabindex="0" role="button" aria-label="Ampliar ${esc(i[2])}">
        <img src="${encodeURI(i[1])}" alt="${esc(i[2])}" loading="lazy" onerror="this.closest('figure').classList.add('pn-missing')">
        <figcaption><span>${esc(i[0])}</span>${esc(i[2])}</figcaption>
      </figure>`).join('');
    if ($('#galeriaCount')) $('#galeriaCount').textContent = IMAGENS.length;
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
    const filtros = $('#galFiltros'), galeria = $('#pnGallery'), imagem = $('#lbImg');
    if (filtros) filtros.addEventListener('click', (e) => { const b = e.target.closest('[data-gal]'); if (b) { galFiltro = b.dataset.gal; renderGaleria(); } });
    if (galeria) {
      galeria.addEventListener('click', (e) => { const f = e.target.closest('.pn-thumb'); if (f) { renderGaleriaLista(); abrirLb(+f.dataset.idx); } });
      galeria.addEventListener('keydown', (e) => { const f = e.target.closest('.pn-thumb'); if (f && (e.key === 'Enter' || e.key === ' ')) { e.preventDefault(); abrirLb(+f.dataset.idx); } });
    }
    if (imagem) imagem.addEventListener('click', () => $('#modalImg').classList.toggle('zoom'));
    if ($('.pn-lb-prev')) $('.pn-lb-prev').addEventListener('click', () => navLb(-1));
    if ($('.pn-lb-next')) $('.pn-lb-next').addEventListener('click', () => navLb(1));
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
    // os fichamentos automáticos vêm do cofre, que já conta no inventário: somar só os digitados aqui
    const fichReg = manuais.reduce((s, r) => s + (+r.fichamentos || 0), 0);
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
    t.innerHTML = `<thead><tr><th>Semana</th><th>Origem</th><th>Pág. lidas</th><th>Artigos</th><th>Fichamentos</th><th>Artigo (pág.)</th><th>Tese (pág.)</th><th>IoT</th><th>Horas</th><th>Obs.</th><th></th></tr></thead><tbody>` +
      registros.slice().reverse().map((r) => `<tr><td>${dataBR(r.semana)}</td><td title="${r.derivado ? 'Calculado dos dados do cofre' : ''}${r.auto ? ' · Painel de Estudo (progresso.py)' : ''}${r.manual ? ' · complemento manual' : ''}">${r.derivado ? '📊' : ''}${r.auto ? '🤖' : ''}${r.manual ? '✍️' : ''}</td><td>${fmt(r.paginasLidas)}</td><td>${fmt(r.artigosLidos)}</td><td>${fmt(r.fichamentos)}</td><td>${fmt(r.pagArtigo)}</td><td>${fmt(r.pagTese)}</td><td>${fmt(r.tarefasIot)}</td><td>${fmt(r.horas)}</td><td>${esc(r.obs || '')}</td><td><button class="pn-btn pn-btn-sm" data-edit="${r.semana}" type="button">${r.manual ? 'Editar' : 'Completar'}</button>${r.manual ? ` <button class="pn-btn pn-btn-sm pn-btn-danger" data-del="${r.semana}" type="button">Excluir manual</button>` : ''}</td></tr>`).join('') + '</tbody>' +
      `<caption class="pn-muted" style="caption-side:bottom;text-align:left;padding-top:8px">📊 = calculado dos dados do cofre (fichamentos e leituras) · 🤖 = Painel de Estudo (progresso.py) · ✍️ = complemento manual. Um valor digitado prevalece sobre o automático; horas, IoT e páginas são só manuais.${window.DADOS_PROGRESSO ? ` Painel atualizado em ${dataBR(window.DADOS_PROGRESSO.atualizado.slice(0, 10))}.` : ''}</caption>`;
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
      manuais = manuais.filter((x) => x.semana !== r.semana).concat(r);
      salvarRegistros();
      toast(`Semana de ${dataBR(r.semana)} salva.`);
    });
    f.addEventListener('reset', () => setTimeout(() => { f.semana.value = segundaDe(hoje()); }));
    $('#pnTabela').addEventListener('click', (e) => {
      const d = e.target.closest('[data-del]'), ed = e.target.closest('[data-edit]');
      if (d && confirm(`Apagar a semana de ${dataBR(d.dataset.del)}?`)) { manuais = manuais.filter((x) => x.semana !== d.dataset.del); salvarRegistros(); }
      if (ed) { const r = manuais.find((x) => x.semana === ed.dataset.edit) || { semana: ed.dataset.edit }; f.reset(); setTimeout(() => { Object.keys(r).forEach((k) => { if (f[k]) f[k].value = r[k]; }); f.semana.value = ed.dataset.edit; }); f.scrollIntoView({ behavior: 'smooth' }); toast(`Semana de ${dataBR(ed.dataset.edit)} carregada no formulário acima.`); }
    });
    $('#pnExport').addEventListener('click', () => {
      const blob = new Blob([JSON.stringify({ exportado: new Date().toISOString(), metas, registros: manuais }, null, 2)], { type: 'application/json' });
      const a = Object.assign(document.createElement('a'), { href: URL.createObjectURL(blob), download: 'acompanhamento_semanal.json' });
      a.click(); URL.revokeObjectURL(a.href);
    });
    $('#pnImport').addEventListener('change', async (e) => {
      const file = e.target.files[0]; if (!file) return;
      try {
        const j = JSON.parse(await file.text());
        if (!Array.isArray(j.registros)) throw new Error('formato');
        manuais = j.registros; if (j.metas) { metas = Object.assign({}, METAS_PADRAO, j.metas); gravar(METAS_KEY, metas); renderMetasForm(); }
        salvarRegistros(); toast(`${manuais.length} semana(s) importada(s).`);
      } catch (err) { toast('Arquivo inválido.'); }
      e.target.value = '';
    });
    $('#pnClear').addEventListener('click', () => { if (confirm('Apagar todos os registros semanais deste navegador? Exporte antes se quiser guardar.')) { manuais = []; salvarRegistros(); } });
  }

  // -------------------------------------------------------------- metas
  function renderMetasForm() {
    $('#pnMetasForm').innerHTML = Object.entries(metas).map(([k, m]) => `
      <fieldset class="pn-fieldset"><legend>${esc(m.nome)}</legend>
        <label>Meta total (${m.unidade})<input type="number" min="1" step="1" data-k="${k}" data-f="total" value="${m.total}"></label>
        <label>Já feito antes dos registros<input type="number" min="0" step="0.5" data-k="${k}" data-f="feitoBase" value="${m.feitoBase}"></label>
        <label>Prazo<input type="date" data-k="${k}" data-f="prazo" value="${m.prazo}"></label>
        ${m.prazoLimite ? `<label>Prazo limite<input type="date" data-k="${k}" data-f="prazoLimite" value="${m.prazoLimite}"></label>` : ''}
        <label style="display:flex; align-items:center; gap:8px; cursor:pointer; margin-top:6px;">
          <input type="checkbox" data-k="${k}" data-f="concluidoManual" ${m.concluidoManual ? 'checked' : ''} style="cursor:pointer; width:auto;">
          <span>Marco concluído</span>
        </label>
      </fieldset>`).join('') + `<p class="pn-muted pn-span3">Os valores iniciais são apenas exemplos editáveis — ajuste-os à sua realidade e às normas do programa.</p>`;
  }

  function renderGantt() {
    const el = $('#pnTimeline');
    if (!el) return;
    if (!cronograma.length) { el.innerHTML = '<p class="pn-muted">Nenhuma etapa no cronograma ainda.</p>'; return; }

    const starts = cronograma.map((e, i) => gMs(gIni(e, i)));
    const ends = cronograma.map((e) => gMs(e.prazo));
    const csDate = new Date(Math.min(...starts)); csDate.setDate(1);
    const ceDate = new Date(Math.max(...ends)); ceDate.setMonth(ceDate.getMonth() + 1, 0);
    gCS = csDate; gTotalMs = ceDate.getTime() - csDate.getTime();

    const pL = (ms) => ((ms - csDate.getTime()) / gTotalMs * 100).toFixed(2) + '%';
    const pW = (s, e) => (Math.max(0, e - s) / gTotalMs * 100).toFixed(2) + '%';

    const MESES = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez'];
    const months = []; const mIt = new Date(csDate);
    while (mIt <= ceDate) { months.push(new Date(mIt)); mIt.setMonth(mIt.getMonth() + 1); }

    const todayMs = new Date().setHours(12, 0, 0, 0);
    const todayL = todayMs >= csDate.getTime() && todayMs <= ceDate.getTime() ? pL(todayMs) : null;
    const minW = Math.max(680, months.length * 80);

    el.innerHTML = `
<div class="gantt-scroll">
  <div class="gantt-canvas" style="min-width:${minW}px">
    <div class="gantt-head">
      <div class="gantt-namecol" style="width:200px"></div>
      <div class="gantt-tlcol" style="height:28px">
        ${months.map((m) => `<div class="gantt-mlbl" style="left:${pL(m)}">${MESES[m.getMonth()]} ${m.getFullYear()}</div>`).join('')}
      </div>
    </div>
    ${cronograma.map((e, i) => {
      const ini = gIni(e, i);
      const color = CAT_C[e.cat] || CAT_C.geral;
      return `<div class="gantt-row" data-id="${e.id}">
        <div class="gantt-namecol" style="width:200px">
          <span class="gantt-dot" style="background:${color}"></span>
          <span class="gantt-lbl" title="${esc(e.nome)}">${esc(e.nome)}</span>
          <button type="button" class="gantt-delbtn" data-gdel="${e.id}" title="Excluir">×</button>
        </div>
        <div class="gantt-tlcol">
          ${months.map((m) => `<div class="gantt-gridln" style="left:${pL(m)}"></div>`).join('')}
          <div class="gantt-bar${e.concluido ? ' gantt-done' : ''}"
            data-gedit="${e.id}" data-ini="${ini}"
            style="left:${pL(gMs(ini))};width:${pW(gMs(ini), gMs(e.prazo))};background:${e.concluido ? '#10b981' : color}"
            title="${esc(e.nome)} — ${dataBR(ini)} → ${dataBR(e.prazo)}">
            <span>${esc(e.nome.length > 22 ? e.nome.slice(0, 20) + '…' : e.nome)}</span>
          </div>
        </div>
      </div>`;
    }).join('')}
    ${todayL ? `<div class="gantt-today" style="left:${todayL}"></div>` : ''}
  </div>
</div>
<div class="gantt-footer">
  <button type="button" class="pn-btn pn-btn-sm" id="btnGanttAdd">+ Nova etapa</button>
  <div class="gantt-leg">
    ${Object.entries(CAT_C).map(([k, c]) => `<span><i style="background:${c}"></i>${k}</span>`).join('')}
    <span><i style="background:#22c55e"></i>hoje</span>
  </div>
</div>`;
  }

  function initMetas() {
    renderMetasForm();
    $('#pnMetasForm').addEventListener('change', (e) => {
      const i = e.target; if (!i.dataset.k) return;
      const val = i.type === 'checkbox' ? i.checked : (i.type === 'number' ? Math.max(0, +i.value || 0) : i.value);
      metas[i.dataset.k] = { ...metas[i.dataset.k], [i.dataset.f]: val };
      gravar(METAS_KEY, metas); renderTudo();
    });
  }

  function initGantt() {
    const el = $('#pnTimeline');
    if (!el) return;
    const modal = $('#modalGanttEditar');

    // Abrir modal de edição ao clicar numa barra
    el.addEventListener('click', (ev) => {
      const del = ev.target.closest('[data-gdel]');
      const bar = ev.target.closest('[data-gedit]');
      const add = ev.target.closest('#btnGanttAdd');

      if (del) {
        const id = del.dataset.gdel;
        const item = cronograma.find((x) => x.id === id);
        if (item && confirm(`Excluir a etapa "${item.nome}"?`)) {
          cronograma = cronograma.filter((x) => x.id !== id);
          salvarCronograma();
          toast('Etapa removida do cronograma.');
        }
        return;
      }
      if (add) {
        const m = $('#formNovaEtapaModal');
        if (m) { m.removeAttribute('hidden'); m.classList.add('open'); }
        return;
      }
      if (bar && modal) {
        const id = bar.dataset.gedit;
        const item = cronograma.find((x) => x.id === id);
        if (!item) return;
        const idx = cronograma.indexOf(item);
        modal.querySelector('#geId').value = id;
        modal.querySelector('#geNome').value = item.nome;
        modal.querySelector('#geInicio').value = item.inicio || gIni(item, idx);
        modal.querySelector('#gePrazo').value = item.prazo;
        modal.querySelector('#geCat').value = item.cat || 'geral';
        modal.querySelector('#geObs').value = item.obs || '';
        modal.removeAttribute('hidden'); modal.classList.add('open');
      }
    });

    // Modal de edição — salvar / fechar
    if (modal) {
      const fecharModal = () => { modal.classList.remove('open'); modal.setAttribute('hidden', ''); };
      modal.querySelector('.pn-modal-close').addEventListener('click', fecharModal);
      modal.querySelector('#geCancelar').addEventListener('click', fecharModal);
      modal.addEventListener('click', (ev) => { if (ev.target === modal) fecharModal(); });
      modal.querySelector('#ganttEditForm').addEventListener('submit', (ev) => {
        ev.preventDefault();
        const id = modal.querySelector('#geId').value;
        const item = cronograma.find((x) => x.id === id);
        if (!item) return;
        const newIni = modal.querySelector('#geInicio').value;
        const newPrazo = modal.querySelector('#gePrazo').value;
        if (newIni >= newPrazo) { toast('O início deve ser anterior ao prazo.'); return; }
        item.nome = modal.querySelector('#geNome').value.trim();
        item.inicio = newIni;
        item.prazo = newPrazo;
        const catEl = modal.querySelector('#geCat');
        item.cat = catEl.value;
        item.catNome = catEl.selectedOptions[0]?.textContent || item.cat;
        item.obs = modal.querySelector('#geObs').value.trim();
        fecharModal();
        salvarCronograma();
        toast('Etapa atualizada.');
      });
    }

    // Arrastar barra para mover datas
    let drag = null;
    el.addEventListener('mousedown', (ev) => {
      const bar = ev.target.closest('[data-gedit]');
      if (!bar || !gCS) return;
      ev.preventDefault();
      const id = bar.dataset.gedit;
      const item = cronograma.find((x) => x.id === id);
      if (!item) return;
      const ini = item.inicio || gIni(item, cronograma.indexOf(item));
      const tlcol = bar.closest('.gantt-tlcol');
      drag = { bar, item, origIni: ini, origPrazo: item.prazo, startX: ev.clientX, tlW: tlcol.getBoundingClientRect().width };
      bar.classList.add('dragging');
    });
    document.addEventListener('mousemove', (ev) => {
      if (!drag || !gCS) return;
      const dx = ev.clientX - drag.startX;
      const delta = (dx / drag.tlW) * gTotalMs;
      const durMs = gMs(drag.origPrazo) - gMs(drag.origIni);
      const newIniMs = gMs(drag.origIni) + delta;
      drag.bar.style.left = ((newIniMs - gCS.getTime()) / gTotalMs * 100).toFixed(2) + '%';
      drag.previewIni = new Date(newIniMs).toISOString().slice(0, 10);
      drag.previewPrazo = new Date(newIniMs + durMs).toISOString().slice(0, 10);
    });
    document.addEventListener('mouseup', () => {
      if (!drag) return;
      if (drag.previewIni && drag.previewIni !== drag.origIni) {
        drag.item.inicio = drag.previewIni;
        drag.item.prazo = drag.previewPrazo;
        salvarCronograma();
        toast('Etapa movida.');
      }
      drag.bar.classList.remove('dragging');
      drag = null;
    });

    // Suporte a toque (mobile)
    el.addEventListener('touchstart', (ev) => {
      const bar = ev.target.closest('[data-gedit]');
      if (!bar || !gCS) return;
      const t = ev.touches[0];
      const id = bar.dataset.gedit;
      const item = cronograma.find((x) => x.id === id);
      if (!item) return;
      const ini = item.inicio || gIni(item, cronograma.indexOf(item));
      const tlcol = bar.closest('.gantt-tlcol');
      drag = { bar, item, origIni: ini, origPrazo: item.prazo, startX: t.clientX, tlW: tlcol.getBoundingClientRect().width };
    }, { passive: true });
    document.addEventListener('touchmove', (ev) => {
      if (!drag || !gCS) return;
      const dx = ev.touches[0].clientX - drag.startX;
      const delta = (dx / drag.tlW) * gTotalMs;
      const durMs = gMs(drag.origPrazo) - gMs(drag.origIni);
      const newIniMs = gMs(drag.origIni) + delta;
      drag.bar.style.left = ((newIniMs - gCS.getTime()) / gTotalMs * 100).toFixed(2) + '%';
      drag.previewIni = new Date(newIniMs).toISOString().slice(0, 10);
      drag.previewPrazo = new Date(newIniMs + durMs).toISOString().slice(0, 10);
    }, { passive: true });
    document.addEventListener('touchend', () => {
      if (!drag) return;
      if (drag.previewIni && drag.previewIni !== drag.origIni) {
        drag.item.inicio = drag.previewIni;
        drag.item.prazo = drag.previewPrazo;
        salvarCronograma();
        toast('Etapa movida.');
      }
      drag = null;
    });
  }

  // -------------------------------------------------------- cronograma
  function salvarCronograma() {
    gravar(CRONOGRAMA_KEY, cronograma);
    renderCronograma();
    renderGantt();
  }

  function renderCronograma() {
    const listEl = $('#pnCronogramaList');
    if (!listEl) return;

    const total = cronograma.length;
    const concluidos = cronograma.filter(e => e.concluido).length;
    const pct = total ? Math.round((concluidos / total) * 100) : 0;

    const txtEl = $('#cronoStatusTexto');
    if (txtEl) txtEl.textContent = `${concluidos} de ${total} etapas concluídas (${pct}%)`;

    const barEl = $('#cronoProgBar');
    if (barEl) barEl.style.width = `${pct}%`;

    let itens = cronograma;
    if (filtroCronoAtual === 'pendentes') itens = cronograma.filter(e => !e.concluido);
    else if (filtroCronoAtual === 'concluidos') itens = cronograma.filter(e => e.concluido);

    if (itens.length === 0) {
      listEl.innerHTML = `<div class="pn-empty" style="padding:24px 12px;"><p class="pn-muted">Nenhuma etapa encontrada neste filtro.</p></div>`;
      return;
    }

    const agora = hoje();
    listEl.innerHTML = itens.map(e => {
      const dPrazo = parseData(e.prazo);
      const atrasado = !e.concluido && dPrazo < agora;
      const statusClasse = e.concluido ? 'concluido' : (atrasado ? 'atrasado' : 'pendente');

      let badgePrazo = '';
      if (e.concluido) {
        badgePrazo = `<span class="crono-prazo-badge" title="Data de conclusão">✓ Concluído${e.dataConclusao ? ' em ' + dataBR(e.dataConclusao) : ''}</span>`;
      } else if (atrasado) {
        badgePrazo = `<span class="crono-prazo-badge" style="color:#ef4444; border-color:rgba(239,68,68,0.3); background:rgba(239,68,68,0.1);">Atrasado (${dataBR(e.prazo)})</span>`;
      } else {
        const dias = Math.ceil((dPrazo - agora) / (1000 * 60 * 60 * 24));
        badgePrazo = `<span class="crono-prazo-badge">Prazo: ${dataBR(e.prazo)} (${dias}d)</span>`;
      }

      return `
        <div class="crono-item ${statusClasse}" data-id="${esc(e.id)}">
          <div class="crono-left">
            <button type="button" class="crono-check-btn" data-action="toggle" title="${e.concluido ? 'Marcar como pendente' : 'Marcar como concluído'}" aria-label="${e.concluido ? 'Concluído' : 'Pendente'}">
              ${e.concluido ? '<svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor"><path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/></svg>' : ''}
            </button>
            <div class="crono-info">
              <div class="crono-title">
                <span class="text">${esc(e.nome)}</span>
                <span class="crono-cat-tag">${esc(e.catNome || e.cat)}</span>
              </div>
              ${e.obs ? `<div class="crono-desc">${esc(e.obs)}</div>` : ''}
            </div>
          </div>
          <div class="crono-right">
            ${badgePrazo}
            <button type="button" class="crono-del-btn" data-action="del" title="Excluir etapa" aria-label="Excluir">🗑</button>
          </div>
        </div>
      `;
    }).join('');
  }

  function initCronograma() {
    renderCronograma();

    const listEl = $('#pnCronogramaList');
    if (listEl) {
      listEl.addEventListener('click', (e) => {
        const btn = e.target.closest('button');
        if (!btn) return;
        const itemEl = btn.closest('.crono-item');
        if (!itemEl) return;
        const id = itemEl.dataset.id;
        const item = cronograma.find(x => x.id === id);
        if (!item) return;

        if (btn.dataset.action === 'toggle') {
          item.concluido = !item.concluido;
          item.dataConclusao = item.concluido ? new Date().toISOString().slice(0, 10) : null;
          salvarCronograma();
          toast(item.concluido ? `Etapa "${item.nome}" marcada como CONCLUÍDA!` : `Etapa "${item.nome}" marcada como pendente.`);
        } else if (btn.dataset.action === 'del') {
          if (confirm(`Deseja excluir a etapa "${item.nome}" do cronograma?`)) {
            cronograma = cronograma.filter(x => x.id !== id);
            salvarCronograma();
            toast('Etapa removida.');
          }
        }
      });
    }

    // Filtros
    $$('#cronoFiltros .pn-seg-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        $$('#cronoFiltros .pn-seg-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        filtroCronoAtual = btn.dataset.filtro;
        renderCronograma();
      });
    });

    // Reset para padrão
    const btnReset = $('#btnResetCrono');
    if (btnReset) {
      btnReset.addEventListener('click', () => {
        if (confirm('Deseja restaurar as etapas padrão do cronograma do doutorado?')) {
          cronograma = JSON.parse(JSON.stringify(CRONOGRAMA_PADRAO));
          salvarCronograma();
          toast('Cronograma restaurado com as etapas padrão.');
        }
      });
    }

    // Modal Nova Etapa
    const modal = $('#formNovaEtapaModal');
    const btnNova = $('#btnNovaEtapa');
    const fechar = $('#fecharNovaEtapa');
    const cancelar = $('#cancelarNovaEtapa');
    const form = $('#formNovaEtapa');

    const abreModal = () => { if (modal) { modal.removeAttribute('hidden'); modal.classList.add('open'); } };
    const fechaModal = () => { if (modal) { modal.classList.remove('open'); modal.setAttribute('hidden', ''); } };

    if (btnNova) btnNova.addEventListener('click', abreModal);
    if (fechar) fechar.addEventListener('click', fechaModal);
    if (cancelar) cancelar.addEventListener('click', fechaModal);

    if (form) {
      form.addEventListener('submit', (ev) => {
        ev.preventDefault();
        const nome = $('#novaEtapaNome').value.trim();
        const prazo = $('#novaEtapaPrazo').value;
        const catSelect = $('#novaEtapaCat');
        const cat = catSelect ? catSelect.value : 'geral';
        const catNome = catSelect && catSelect.selectedOptions[0] ? catSelect.selectedOptions[0].textContent : cat;
        const obs = $('#novaEtapaObs').value.trim();

        if (!nome || !prazo) return;

        const nova = {
          id: 'crono-' + Date.now(),
          nome,
          cat,
          catNome,
          prazo,
          obs,
          concluido: false,
          dataConclusao: null
        };

        cronograma.push(nova);
        cronograma.sort((a, b) => a.prazo.localeCompare(b.prazo));
        salvarCronograma();
        fechaModal();
        form.reset();
        toast('Nova etapa adicionada ao cronograma!');
      });
    }
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
  // PDFs hospedados no GitHub Pages — mesma raiz do site.
  const COFRE_FILE_BASE = 'https://rcminitor.github.io/S-ndrome-Pandora/';
  function cofreUrl(caminho) {
    if (!caminho) return '';
    return COFRE_FILE_BASE + caminho.replace(/\\/g, '/').split('/').map(encodeURIComponent).join('/');
  }

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
        ${d.publico === false ? '<span class="pn-muted" style="font-size:.75rem">Disponível só no cofre</span>' : `<div class="pn-actions"><button class="pn-btn pn-btn-sm" data-pdf="${esc(d.arquivo)}" data-nome="${esc(d.nome)}" type="button">Ler aqui</button><a class="pn-btn pn-btn-sm" href="${cofreUrl(d.arquivo)}" target="_blank" rel="noopener">Nova aba ↗</a></div>`}</div>`).join('')}</div></div>`).join('') || '<p class="pn-muted">Nenhum PDF encontrado.</p>';
    $('#pdfContagem').textContent = `${lista.length} de ${PDFS.length} PDFs`;
    if ($('#pdfBadge')) $('#pdfBadge').textContent = PDFS.length;
  }
  function initPdfs() {
    if (!$('#pdfLista')) return;
    $('#pdfFiltros').addEventListener('click', (e) => { const b = e.target.closest('[data-pasta]'); if (b) { pdfPasta = b.dataset.pasta; renderPdfs(); } });
    $('#pdfBusca').addEventListener('input', (e) => { pdfTexto = e.target.value; renderPdfs(); });
    document.addEventListener('click', (e) => {
      const b = e.target.closest('[data-pdf]'); if (!b) return;
      const url = cofreUrl(b.dataset.pdf);
      $('#pdfTitulo').textContent = b.dataset.nome;
      $('#pdfNovaAba').href = url;
      $('#pdfFrame').removeAttribute('srcdoc');
      $('#pdfFrame').src = url;
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

  const falhasPainel = new Set();
  function executarEtapa(nome, tarefa) {
    try {
      tarefa();
    } catch (erro) {
      console.error(`[Painel] Falha em ${nome}:`, erro);
      falhasPainel.add(nome);
      const painel = $('#tab-painel');
      if (painel && !$('#pnFalhaAviso')) {
        const aviso = document.createElement('div');
        aviso.id = 'pnFalhaAviso';
        aviso.className = 'scientific-alert pn-runtime-alert';
        aviso.innerHTML = '<div><strong>O painel carregou parcialmente.</strong> Um dado salvo no navegador não pôde ser lido. As demais funções continuam disponíveis; recarregue a página e, se necessário, exporte e refaça apenas o registro afetado.</div>';
        painel.prepend(aviso);
      }
    }
  }

  function renderTudo() {
    [
      ['indicadores', renderKpis], ['gráfico', renderGrafico], ['probabilidade', renderProb],
      ['acervo', renderAcervo], ['uso', renderUso], ['histórico', renderTabela],
      ['metas', renderGantt], ['cronograma', renderCronograma],
    ].forEach(([nome, tarefa]) => executarEtapa(nome, tarefa));
  }

  document.addEventListener('DOMContentLoaded', () => {
    [
      ['navegação', initRotas], ['janelas', initModais], ['IoT', renderIotCusto],
      ['PDFs', initPdfs], ['Pomodoro', initPomodoro], ['galeria', initGaleria],
      ['imagens', renderGaleria], ['registro semanal', initRegistro],
      ['configuração de metas', initMetas], ['cronograma interativo', initCronograma],
      ['gantt', initGantt],
    ].forEach(([nome, tarefa]) => executarEtapa(nome, tarefa));
    $$('.pn-seg-btn').forEach((b) => b.addEventListener('click', () => {
      $$('.pn-seg-btn').forEach((x) => x.classList.toggle('active', x === b)); metricaAtual = b.dataset.metric; renderGrafico();
    }));
    renderTudo();
  });
})();
