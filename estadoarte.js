/* Aba "Estado da Arte": a Tabela 3 da fundamentação (9 critérios × fontes).
   Os dados vêm de dados_estadoarte.js. Quando o Painel de Estudo está ligado no PC
   (http://127.0.0.1:8765), aparece o formulário para incluir ou atualizar uma fonte:
   o painel grava no site e na nota do cofre e publica no GitHub. Só procura o painel
   quando a aba é aberta. */
(function () {
  'use strict';
  const URL_PAINEL = 'http://127.0.0.1:8765';
  const MARCAS = { '✅': 'ok', '◐': 'meio', '✗': 'nao', 'NC': 'nc' };
  const box = document.getElementById('eaConteudo');
  const btn = document.querySelector('[data-tab="tab-estadoarte"]');
  if (!box) return;
  let dados = window.ESTADO_ARTE || { criterios: [], fontes: [] };
  let ligado = false;

  const esc = (t) => String(t ?? '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  const rotulo = (c) => (/^\d/.test(c) ? '#' + c : c);
  const marca = (m) => `<span class="ea-m ea-${MARCAS[m] || 'nc'}">${esc(m)}</span>`;

  function tabela() {
    const f = dados.fontes, cr = dados.criterios;
    if (!f.length) return '<p>Nenhuma fonte na tabela ainda.</p>';
    return `<div style="overflow-x:auto"><table class="week-table ea-tabela">
      <thead><tr><th>Critério (foco da tese)</th>${f.map((x) => `<th title="${esc(x.titulo)}">${esc(rotulo(x.codigo))}</th>`).join('')}</tr></thead>
      <tbody>${cr.map((c) => `<tr><td><strong>${esc(c.id)}.</strong> ${esc(c.nome)}</td>${f.map((x) => {
        const m = x.marcas[c.id] || { m: 'NC', txt: '' };
        return `<td>${marca(m.m)} ${esc(m.txt)}</td>`;
      }).join('')}</tr>`).join('')}</tbody></table></div>
      <p><small>Fontes: ${f.map((x) => `<b>${esc(rotulo(x.codigo))}</b> ${esc(x.titulo)}`).join(' · ')}</small></p>`;
  }

  function formulario() {
    if (!ligado) {
      return `<div class="content-card" style="margin-top:24px"><h3 class="card-title">Incluir uma leitura na tabela</h3>
        <p>O formulário aparece quando o <b>Painel de Estudo</b> está ligado no seu PC (<code>Iniciar painel.bat</code>). Se o navegador pedir acesso à rede local, clique em <b>Permitir</b>.</p>
        <button class="pn-btn" type="button" id="eaTentar">Tentar de novo</button></div>`;
    }
    const opts = ['NC', '✗', '◐', '✅'].map((m) => `<option>${m}</option>`).join('');   // começa em NC: nada sem conferência
    return `<div class="content-card" style="margin-top:24px"><h3 class="card-title">Incluir ou atualizar uma leitura</h3>
      <p>Marque cada critério <b>depois de conferir no PDF</b>. ✅ e ◐ só são aceitos com a página na justificativa (ex.: <code>20 gatos com FIC (p. 68)</code>). Sem conferência, use <b>NC</b>. Para editar uma fonte que já está na tabela, escolha o código dela: os campos se preenchem.</p>
      <form id="eaForm">
        <div class="pn-grid-2">
          <label>Código do inventário <input name="codigo" list="eaCodigos" required placeholder="ex.: 50 ou S4"></label>
          <label>Título curto <input name="titulo" required placeholder="Autor (ano) — título"></label>
        </div>
        <datalist id="eaCodigos">${(window.DADOS_INVENTARIO || []).map((i) => `<option value="${esc(i.codigo)}">${esc(i.titulo || '')}</option>`).join('')}</datalist>
        <table class="week-table ea-tabela" style="margin-top:12px"><tbody>
        ${dados.criterios.map((c) => `<tr><td><strong>${esc(c.id)}.</strong> ${esc(c.nome)}</td>
          <td><select name="m_${c.id}">${opts}</select></td>
          <td style="width:60%"><input name="t_${c.id}" style="width:100%" placeholder="justificativa com página"></td></tr>`).join('')}
        </tbody></table>
        <div id="eaErros" class="pn-warn" hidden></div>
        <button class="pn-btn pn-btn-primary" type="submit">Salvar no site e no cofre</button>
        <span id="eaStatus"></span>
      </form></div>`;
  }

  function preencher(form, cod) {
    const f = dados.fontes.find((x) => x.codigo === cod);
    const inv = (window.DADOS_INVENTARIO || []).find((i) => i.codigo === cod);
    if (!form.titulo.value && inv) form.titulo.value = inv.titulo || '';
    if (!f) return;
    form.titulo.value = f.titulo;
    dados.criterios.forEach((c) => {
      form['m_' + c.id].value = f.marcas[c.id].m;
      form['t_' + c.id].value = f.marcas[c.id].txt;
    });
  }

  async function salvar(ev) {
    ev.preventDefault();
    const form = ev.target, st = document.getElementById('eaStatus'), er = document.getElementById('eaErros');
    const corpo = { codigo: form.codigo.value.trim().replace(/^#/, ''), titulo: form.titulo.value.trim(), marcas: {} };
    dados.criterios.forEach((c) => { corpo.marcas[c.id] = { m: form['m_' + c.id].value, txt: form['t_' + c.id].value.trim() }; });
    st.textContent = 'Salvando…'; er.hidden = true;
    try {
      const r = await fetch(URL_PAINEL + '/api/estadoarte', { method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(corpo), targetAddressSpace: 'loopback' });
      const j = await r.json();
      if (!j.ok) { er.innerHTML = (j.erros || ['Não salvou.']).map(esc).join('<br>'); er.hidden = false; st.textContent = ''; return; }
      dados = j.dados; render();
      document.getElementById('eaStatus').textContent = `Fonte ${rotulo(corpo.codigo)} salva no cofre. O site público atualiza em alguns minutos.`;
    } catch (e) { st.textContent = 'O painel não respondeu.'; }
  }

  async function ping() {
    const ctl = new AbortController();
    const t = setTimeout(() => ctl.abort(), 2500);
    try {
      const r = await fetch(URL_PAINEL + '/api/estadoarte', { signal: ctl.signal, targetAddressSpace: 'loopback' });
      if (!r.ok) return false;
      dados = await r.json();
      return true;
    } catch (e) { return false; } finally { clearTimeout(t); }
  }

  function render() {
    box.innerHTML = tabela() + formulario();
    const form = document.getElementById('eaForm');
    if (form) {
      form.addEventListener('submit', salvar);
      form.codigo.addEventListener('change', () => preencher(form, form.codigo.value.trim().replace(/^#/, '')));
    }
    const t = document.getElementById('eaTentar');
    if (t) t.addEventListener('click', verificar);
  }

  async function verificar() { ligado = await ping(); render(); }

  render();
  if (btn) btn.addEventListener('click', () => { if (!ligado) verificar(); });
  if (location.hash === '#tab-estadoarte') verificar();
})();
