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
        <p>Esta aba funciona no <b>seu PC</b>: é ele que lê os PDFs, baixa os artigos citados e roda o orientador. O site só mostra.</p>
        <ol class="ag-passos">
          <li><b>Primeira vez:</b> na pasta <code>C:\\Users\\rcmin\\Projetos\\S-ndrome-Pandora</code>, dê dois cliques em <b>Ligar painel automaticamente.bat</b>. A partir daí ele liga sozinho sempre que o Windows iniciar.</li>
          <li>Se o navegador perguntar se este site pode <b>acessar dispositivos da rede local</b>, clique em <b>Permitir</b>.</li>
          <li>Clique em <b>Tentar de novo</b>.</li>
        </ol>
        <div class="pn-actions">
          <button class="pn-btn pn-btn-primary" id="agTentar" type="button">Tentar de novo</button>
          <a class="pn-btn" href="${URL_PAINEL}" target="_blank" rel="noopener">Abrir o painel direto ↗</a>
        </div>
        <p class="pn-muted">Em outro computador ou no celular esta aba não funciona — os seus PDFs e o seu texto ficam só no seu PC.</p>
      </div>`;
    document.getElementById('agTentar').onclick = conectar;
  }

  function mostrar() {
    box.innerHTML = `
      <div class="pn-toolbar" style="margin-bottom:10px">
        <p class="pn-muted" style="margin:0">● Conectado ao painel do seu computador.</p>
        <a class="pn-btn" href="${URL_PAINEL}" target="_blank" rel="noopener">Abrir em tela cheia ↗</a>
      </div>
      <iframe class="ag-frame" src="${URL_PAINEL}/?embed=1" title="Painel de Estudo" allow="local-network-access"></iframe>`;
  }

  async function conectar() {
    box.innerHTML = '<p class="pn-muted">Procurando o painel no seu computador…</p>';
    ligado = await ping();
    ligado ? mostrar() : desligado();
  }

  btn.addEventListener('click', () => { if (!ligado) conectar(); });
  if (location.hash === '#agentes') { btn.click(); }
})();
