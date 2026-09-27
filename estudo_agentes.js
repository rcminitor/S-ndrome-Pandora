/* Aba "Estudo com agentes": mostra o Painel de Estudo que roda no PC do Romulo.
   O site é só a vitrine; ler PDFs, baixar citados e conversar com o orientador
   acontece no computador (http://127.0.0.1:8765). Só procura o painel quando a
   aba é aberta, para não incomodar outros visitantes. */
(function () {
  'use strict';
  const URL_PAINEL = 'http://127.0.0.1:8765';
  const box = document.getElementById('agConteudo');
  const btn = document.querySelector('[data-tab="tab-agentes"]');
  if (!box || !btn) return;
  let ligado = false;

  async function ping() {
    const ctl = new AbortController();
    const t = setTimeout(() => ctl.abort(), 2500);
    try {
      const r = await fetch(URL_PAINEL + '/api/ping', { signal: ctl.signal, targetAddressSpace: 'loopback' });
      return r.ok;
    } catch (e) { return false; } finally { clearTimeout(t); }
  }

  function desligado() {
    box.innerHTML = `
      <div class="content-card">
        <h3 class="card-title">O painel do seu computador não respondeu</h3>
        <p style="margin-bottom:14px;color:var(--text-muted)">Esta aba funciona no <b>seu PC</b>: é ele que lê os PDFs, baixa os artigos citados e roda o orientador. O site só mostra.</p>
        <ol class="ag-passos">
          <li><b>Primeira vez:</b> na pasta <code>C:\\Users\\rcmin\\Projetos\\S-ndrome-Pandora</code>, dê dois cliques em <b>Ligar painel automaticamente.bat</b>. A partir daí ele liga sozinho sempre que o Windows iniciar.</li>
          <li>Se o navegador perguntar se este site pode <b>acessar dispositivos da rede local</b>, clique em <b>Permitir</b>.</li>
          <li>Clique em <b>Tentar de novo</b>.</li>
        </ol>
        <div class="pn-actions" style="margin-top:18px">
          <button class="pn-btn pn-btn-primary" id="agTentar" type="button">Tentar de novo</button>
          <a class="pn-btn" href="${URL_PAINEL}" target="_blank" rel="noopener">Abrir o painel direto ↗</a>
        </div>
        <p class="pn-muted" style="margin-top:14px">Em outro computador ou no celular esta aba não funciona — os seus PDFs e o seu texto ficam só no seu PC.</p>
      </div>`;
    document.getElementById('agTentar').onclick = conectar;
  }

  function mostrar() {
    box.innerHTML = `
      <div class="pn-toolbar" style="margin-bottom:14px;align-items:center">
        <span class="ag-status"><span class="ag-status-dot"></span>Conectado ao painel do seu computador</span>
        <a class="pn-btn pn-btn-primary" href="${URL_PAINEL}" target="_blank" rel="noopener">Abrir em tela cheia ↗</a>
      </div>
      <div class="ag-frame-wrap">
        <iframe class="ag-frame" src="${URL_PAINEL}/?embed=1" title="Painel de Estudo" allow="local-network-access"></iframe>
      </div>`;
  }

  function limparTitulo(t) {
    return String(t)
      .replace(/\.[a-z]{2,4}$/i, '')
      .replace(/[_\-]/g, ' ')
      .replace(/\s{2,}/g, ' ')
      .trim();
  }

  function blocoRevisao() {
    const R = window.DADOS_REVISAO;
    if (!R || !R.total) return '';
    const pct = (a) => a.total ? Math.round(100 * a.firmes / a.total) : 0;
    return `
      <div class="content-card" style="margin-bottom:18px">
        <div class="pn-card-head">
          <h3 class="card-title">Revisão espaçada</h3>
          <span class="pn-muted">atualizado em ${R.atualizado.slice(8, 10)}/${R.atualizado.slice(5, 7)} ${R.atualizado.slice(11, 16)}</span>
        </div>
        <div class="est-tiles">
          <div class="est-tile est-green">
            <b>${R.firmes}</b>
            <span>cartões firmes</span>
            <small>de ${R.total} no total</small>
          </div>
          <div class="est-tile est-blue">
            <b>${R.aprendendo}</b>
            <span>aprendendo</span>
            <small>${R.novos} ainda não revistos</small>
          </div>
          <div class="est-tile est-orange">
            <b>${R.acerto_7d == null ? '—' : R.acerto_7d + '%'}</b>
            <span>acerto em 7 dias</span>
            <small>${R.revisoes_7d} respostas</small>
          </div>
          <div class="est-tile est-pink">
            <b>${R.hoje}</b>
            <span>para revisar hoje</span>
            <small>no painel do PC</small>
          </div>
        </div>
        <div class="pn-hbars" style="margin-top:16px">
          ${R.por_artigo.slice(0, 8).map((a) => {
            const label = a.codigo ? '#' + a.codigo : limparTitulo(a.titulo).slice(0, 32);
            return `<div class="pn-hbar"><span title="${String(a.titulo).replace(/"/g, '&quot;')}">${label}</span><div><i style="width:${pct(a)}%;background:#16a34a"></i></div><b>${a.firmes}/${a.total}</b></div>`;
          }).join('')}
        </div>
        <p class="pn-muted" style="margin-top:10px">Barras: cartões firmes por artigo. Perguntas e respostas ficam no seu PC.</p>
      </div>`;
  }

  function blocoAtalhos() {
    return `
      <div class="content-card" style="margin-bottom:18px">
        <div class="pn-card-head">
          <h3 class="card-title">Acesso rápido</h3>
          <span class="pn-muted">seções do painel</span>
        </div>
        <div style="display:flex;gap:10px;flex-wrap:wrap;margin-top:10px">
          <button class="pn-btn" data-goto="tab-inventory" type="button">Acervo</button>
          <button class="pn-btn" data-goto="tab-galeria" type="button">Galeria</button>
          <button class="pn-btn" data-goto="tab-pdfs" type="button">PDFs</button>
          <button class="pn-btn" data-goto="tab-fichamentos" type="button">Fichamentos</button>
        </div>
      </div>`;
  }

  function registro() {
    const alvo = document.getElementById('agRegistro');
    const L = window.DADOS_LEITURAS || [];
    if (!alvo) return;
    if (!L.length) { alvo.innerHTML = blocoRevisao() + blocoAtalhos(); return; }
    const d = (iso) => iso ? iso.slice(8, 10) + '/' + iso.slice(5, 7) + '/' + iso.slice(0, 4) : '';
    const esc = (t) => String(t).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
    const ia = L.filter((x) => x.ia_status === 'ok').length, eu = L.filter((x) => x.eu_li).length;
    const lendo = L.filter((x) => x.ia_status === 'lendo').length;
    alvo.innerHTML = blocoRevisao() + blocoAtalhos() + `
      <div class="content-card" style="margin-bottom:18px">
        <div class="pn-card-head"><h3 class="card-title">Registro de leituras</h3>
          <span class="pn-muted">${ia} lido(s) pela IA · ${eu} lido(s) por você${lendo ? ` · ${lendo} em leitura agora` : ''}</span></div>
        <div class="pn-table-wrap"><table class="week-table">
          <thead><tr><th>Artigo</th><th>IA</th><th>Trechos relevantes</th><th>Citações seguidas</th><th>Baixados</th><th>Você</th></tr></thead>
          <tbody>${L.map((x) => `<tr>
            <td>${esc(x.titulo)}</td>
            <td>${x.ia_status === 'lendo' ? '⏳ lendo desde ' + d(x.ia_inicio) : x.ia_status === 'ok' ? '✓ ' + d(x.ia_fim) + (x.ia_vezes > 1 ? ` (${x.ia_vezes}×)` : '') : x.ia_status === 'erro' ? '⚠ erro ' + d(x.ia_fim) : '—'}</td>
            <td>${x.relevantes ?? '—'}</td><td>${x.citadas ?? '—'}</td><td>${x.baixadas ?? '—'}</td>
            <td>${x.eu_li ? '✓ ' + d(x.eu_li) : '—'}</td></tr>`).join('')}</tbody>
        </table></div>
        <p class="pn-muted">Atualizado sozinho pelo painel do computador. Só títulos, datas e contagens — traduções, PDFs e notas ficam no PC.</p>
      </div>`;
  }
  registro();

  btn.addEventListener('click', () => { if (!ligado) conectar(); });
  if (location.hash === '#agentes') { btn.click(); }

  async function conectar() {
    box.innerHTML = '<p class="pn-muted" style="padding:24px 0">Procurando o painel no seu computador…</p>';
    ligado = await ping();
    ligado ? mostrar() : desligado();
  }
})();
