/* Aba "Fichamentos" e Editor Completo de Fichamentos:
   - Lê dados_fichamentos.js do cofre
   - Permite criar, editar e corrigir fichamentos diretamente no navegador
   - Persiste edições no localStorage (pandora_fich_*)
   - Suporta cópia de Markdown, download de arquivo .md e integração com o servidor local
*/
(function () {
  'use strict';

  const box = document.getElementById('fiConteudo');
  const D = window.DADOS_FICHAMENTOS || { fichamentos: [] };
  const baseLista = Array.isArray(D.fichamentos) ? D.fichamentos : [];
  const codigosNoAcervo = new Set((window.DADOS_INVENTARIO || []).map((a) => String(a.codigo)));

  const esc = (t) => String(t ?? '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  const rot = (c) => (/^\d/.test(c) ? '#' + c : c);

  // Markdown do cofre → HTML com callouts do Obsidian
  function preparar(md) {
    if (!md) return '';
    md = md.replace(/\[\[([^\]|]+)\|([^\]]+)\]\]/g, '$2').replace(/\[\[([^\]]+)\]\]/g, (_, a) => a.split('/').pop());
    return md.replace(/^> \[!(\w+)\][ \t]*(.*)$/gm, (_, tipo, tit) => `> <span class="fi-callout-tit fi-${tipo.toLowerCase()}">${esc(tit || tipo)}</span>\n>`);
  }

  function renderHtml(md) {
    if (window.marked) return window.marked.parse(preparar(md));
    return '<pre style="white-space:pre-wrap">' + esc(md) + '</pre>';
  }

  // Obter lista consolidada (cofre + localStorage)
  function getConsolidatedFichamentos() {
    const list = baseLista.map((f) => {
      const localMd = localStorage.getItem('pandora_fich_' + f.codigo);
      if (localMd) {
        return { ...f, md: localMd, isEdited: true };
      }
      return { ...f, isEdited: false };
    });

    // Fichamentos criados inteiramente pelo usuário no localStorage
    for (let i = 0; i < localStorage.length; i++) {
      const k = localStorage.key(i);
      if (k && k.startsWith('pandora_fich_')) {
        const cod = k.replace('pandora_fich_', '');
        if (!list.some((x) => String(x.codigo) === String(cod))) {
          const rawMd = localStorage.getItem(k) || '';
          // Tentar extrair título da primeira linha ou frontmatter
          let tit = `Fichamento #${cod}`;
          const matchTit = rawMd.match(/^#\s*Fichamento\s*—\s*(.*)$/m);
          if (matchTit) tit = matchTit[1].trim();
          list.push({
            codigo: cod,
            titulo: tit,
            arquivo: `${cod} — Fichamento — ${tit.replace(/[\\/:*?"<>|]/g, '')}.md`,
            data: new Date().toISOString().slice(0, 10),
            paginas: '',
            nucleo: rawMd.includes('nucleo/1') ? '1' : (rawMd.includes('nucleo/2') ? '2' : ''),
            md: rawMd,
            isEdited: true,
            isUserCreated: true,
          });
        }
      }
    }

    return list;
  }

  // Expõe busca de fichamento para o app.js
  window.obterFichamentoArtigo = function (codigo) {
    const todos = getConsolidatedFichamentos();
    return todos.find((x) => String(x.codigo) === String(codigo)) || null;
  };

  // Renderiza índice de cards
  function renderIndice() {
    if (!box) return;
    const lista = getConsolidatedFichamentos();
    const badge = document.getElementById('fiCount');
    if (badge) badge.textContent = lista.length;

    if (!lista.length) {
      box.innerHTML = `
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:18px; flex-wrap:wrap; gap:10px;">
          <p class="pn-muted" style="margin:0">Nenhum fichamento disponível ainda.</p>
          <button class="pn-btn pn-btn-primary" id="btnNovoFichamentoTop" type="button">➕ Fazer Novo Fichamento</button>
        </div>`;
      return;
    }

    const card = (f) => {
      const semPdfNoAcervo = !codigosNoAcervo.has(String(f.codigo));
      return `
      <div class="pn-tile fi-card" style="display:flex; flex-direction:column; justify-content:space-between; text-align:left; cursor:pointer;" data-fi="${esc(f.arquivo)}">
        <div>
          <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:6px;">
            <strong style="font-size:0.95rem; color:var(--text-main);">${esc(rot(f.codigo))} — ${esc(f.titulo)}</strong>
            ${f.isEdited ? '<span style="font-size:0.7rem; color:var(--accent); font-weight:700; background:rgba(236,72,153,0.1); padding:2px 6px; border-radius:4px; margin-left:6px; flex-shrink:0;">● Editado</span>' : ''}
            ${semPdfNoAcervo ? '<span style="font-size:0.7rem; color:var(--orange-primary); font-weight:700; margin-left:6px; flex-shrink:0;">Sem PDF no acervo</span>' : ''}
          </div>
          <small class="pn-muted" style="display:block; margin-bottom:12px;">
            ${f.nucleo ? 'Núcleo ' + esc(f.nucleo) + ' · ' : ''}${f.paginas ? esc(f.paginas) + ' págs. · ' : ''}${f.data ? 'fichado em ' + esc(f.data.split('-').reverse().join('/')) : ''}
          </small>
        </div>
        <div style="display:flex; gap:6px; margin-top:8px;">
          <button class="pn-btn pn-btn-sm" type="button" data-fi-ler="${esc(f.arquivo)}">Ler</button>
          <button class="pn-btn pn-btn-sm" type="button" data-fi-edit="${esc(f.codigo)}" style="background:var(--blue-surface); color:var(--blue-soft);">Editar</button>
        </div>
      </div>`;
    };

    const vinculados = lista.filter((f) => codigosNoAcervo.has(String(f.codigo))).length;
    const rastreabilidade = lista.length - vinculados;

    box.innerHTML = `
      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:18px; flex-wrap:wrap; gap:12px;">
        <div>
          <p style="margin:0; font-size:0.95rem;">
            <strong>${lista.length} fichamentos disponíveis.</strong> ${vinculados} vinculados a fontes com PDF${rastreabilidade ? ` · ${rastreabilidade} preservado para rastreabilidade, sem PDF no acervo` : ''}.
            <small class="pn-muted" style="display:block">Edições feitas no navegador são salvas automaticamente no localStorage e podem ser baixadas em .md para o cofre.</small>
          </p>
        </div>
        <button class="pn-btn pn-btn-primary" id="btnNovoFichamentoTop" type="button">➕ Fazer Novo Fichamento</button>
      </div>
      <div class="pn-grid-3">${lista.map(card).join('')}</div>`;
  }

  // Renderiza leitura do fichamento
  function abrir(arquivo) {
    if (!box) return;
    const lista = getConsolidatedFichamentos();
    const f = lista.find((x) => x.arquivo === arquivo);
    if (!f) return renderIndice();

    box.innerHTML = `
      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:16px; flex-wrap:wrap; gap:10px;">
        <button class="pn-btn" type="button" id="fiVoltar">← Todos os fichamentos</button>
        <div style="display:flex; gap:8px; align-items:center;">
          ${f.isEdited ? '<span style="font-size:0.75rem; color:var(--accent); font-weight:700;">● Editado localmente</span>' : ''}
          <button class="pn-btn pn-btn-primary" type="button" id="fiEditarAtual" data-codigo="${esc(f.codigo)}">✏️ Editar Fichamento</button>
          <button class="pn-btn" type="button" id="fiCopiarAtual" data-codigo="${esc(f.codigo)}">📋 Copiar</button>
          <button class="pn-btn" type="button" id="fiBaixarAtual" data-codigo="${esc(f.codigo)}" data-arquivo="${esc(f.arquivo)}">⬇️ Baixar .md</button>
        </div>
      </div>
      <article class="content-card fi-texto">${renderHtml(f.md)}</article>`;

    box.scrollIntoView({ behavior: 'smooth', block: 'start' });

    // Botões da barra de leitura
    document.getElementById('fiEditarAtual').onclick = () => window.abrirEditorFichamento(f.codigo, f.titulo);
    document.getElementById('fiCopiarAtual').onclick = (e) => {
      navigator.clipboard.writeText(f.md).then(() => {
        const btn = e.target;
        const old = btn.textContent;
        btn.textContent = 'Copiado!';
        setTimeout(() => { btn.textContent = old; }, 2000);
      });
    };
    document.getElementById('fiBaixarAtual').onclick = () => baixarArquivoMd(f.arquivo, f.md);
  }

  // Função utilitária para download de .md
  function baixarArquivoMd(nomeArquivo, conteudo) {
    const blob = new Blob([conteudo], { type: 'text/markdown;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = nomeArquivo.endsWith('.md') ? nomeArquivo : nomeArquivo + '.md';
    document.body.appendChild(a);
    a.click();
    setTimeout(() => {
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    }, 150);
  }

  // Gera template padrão para um artigo
  function gerarTemplateFichamento(artigo) {
    const hoje = new Date();
    const hojeISO = hoje.toISOString().slice(0, 10);
    const hojeBR = hoje.toLocaleDateString('pt-BR');
    const cod = artigo.codigo || '00';
    const tit = artigo.titulo || 'Título do Artigo';
    const nucleoTag = artigo.nucleo && artigo.nucleo.includes('1') ? 'nucleo/1' : 'nucleo/2';
    const ref = artigo.referencia && artigo.referencia !== 'NAO CONFIRMADO' ? artigo.referencia : '[Inserir referência ABNT conferida]';

    return `---
tipo: fichamento
codigo: "${cod}"
fonte: "${tit}"
data_do_fichamento: ${hojeISO}
paginas_lidas: ""
tags:
  - fichamento
  - ${nucleoTag}
---

# Fichamento — ${tit}

**Fonte:** [[Fontes/${cod} ${tit.slice(0, 35)}]] · **Código na triagem:** ${cod} · **Lido em:** ${hojeBR}

> [!warning] Regra do acervo
> Nenhum número, página, resultado ou referência entra aqui sem estar aberto no PDF. O que for leitura minha vai marcado como tal.

## 1. Referência (ABNT) — conferida no artigo

> ${ref}

*Procedência:* ✔️ **confirmada na fonte** · 🟡 **parcialmente confirmada** · ⚠️ **A CONFERIR no artigo**

## 2. Problema e objetivo declarados pelo autor

${artigo.porQueLer && artigo.porQueLer !== 'NÃO CONFIRMADO' ? artigo.porQueLer : ''}

## 3. Método

- Delineamento: ${artigo.tipoEstudo && artigo.tipoEstudo !== 'NÃO CONFIRMADO' ? artigo.tipoEstudo : ''}
- Amostra (n, espécie, procedência):
- Desfechos medidos:
- Análise:

## 4. Resultados — com página

| Achado | Valor | Página |
|---|---|---|
|  |  |  |

## 5. Conclusão dos autores

> 

## 6. Citações diretas que quero usar

> [!quote] p. 
> 

## 7. Limitações apontadas pelos próprios autores

${artigo.cautelas && artigo.cautelas !== 'NÃO CONFIRMADO' ? artigo.cautelas : ''}

## 8. Minha leitura

> [!note] Interpretação minha — não está no artigo
> 

## 9. Onde entra na tese

- Núcleo: ${artigo.nucleo || 'Núcleo 1 / Núcleo 2'}
- Seção: 
- Argumento que sustenta: ${artigo.comoUsar && artigo.comoUsar !== 'NÃO CONFIRMADO' ? artigo.comoUsar : ''}

## 10. A conferir / pendências

- [ ] 

## 11. Fontes citadas por este artigo que preciso buscar

- 
`;
  }

  // --------------------------------------------------------------------------
  // Editor Modal de Fichamentos
  // --------------------------------------------------------------------------
  let editorCodigoAtual = null;
  let editorArquivoAtual = null;
  let modoEditor = 'editor'; // 'editor' ou 'preview'

  window.abrirEditorFichamento = function (codigo, tituloOpt, artigoOpt) {
    const lista = getConsolidatedFichamentos();
    let f = lista.find((x) => String(x.codigo) === String(codigo));
    let artigo = artigoOpt;

    if (!artigo && window.DADOS_INVENTARIO) {
      artigo = window.DADOS_INVENTARIO.find((x) => String(x.codigo) === String(codigo));
    }

    editorCodigoAtual = String(codigo);
    const titulo = tituloOpt || (artigo && artigo.titulo) || (f && f.titulo) || `Artigo #${codigo}`;
    editorArquivoAtual = (f && f.arquivo) || `${codigo} — Fichamento — ${titulo.replace(/[\\/:*?"<>|]/g, '').slice(0, 45)}.md`;

    // Carregar conteúdo
    let conteudoMd = '';
    const localMd = localStorage.getItem('pandora_fich_' + codigo);
    if (localMd) {
      conteudoMd = localMd;
    } else if (f && f.md) {
      conteudoMd = f.md;
    } else if (artigo) {
      conteudoMd = gerarTemplateFichamento(artigo);
    } else {
      conteudoMd = gerarTemplateFichamento({ codigo, titulo });
    }

    // Configurar modal
    const modal = document.getElementById('modalFichamento');
    const badge = document.getElementById('fichModalBadge');
    const tituloEl = document.getElementById('fichModalTitulo');
    const textarea = document.getElementById('fichEditorTextarea');
    const statusEl = document.getElementById('fichEditorStatus');
    const btnRestaurar = document.getElementById('btnFichRestaurar');

    if (badge) badge.textContent = `#${codigo}`;
    if (tituloEl) tituloEl.textContent = `Fichamento — ${titulo}`;
    if (textarea) textarea.value = conteudoMd;

    // Verificar se tem original no cofre para permitir restaurar
    const temOriginalNoCofre = baseLista.some((x) => String(x.codigo) === String(codigo));
    if (btnRestaurar) {
      btnRestaurar.style.display = localMd && temOriginalNoCofre ? 'inline-flex' : 'none';
    }

    if (statusEl) {
      statusEl.textContent = localMd ? '● Editado localmente' : (f ? '✔️ Original do acervo' : '➕ Novo fichamento');
      statusEl.style.color = localMd ? 'var(--accent)' : 'var(--text-muted)';
    }

    // Resetar para modo editor
    setModoEditor('editor');

    // Abrir modal
    if (window.abrirModal) {
      window.abrirModal('modalFichamento');
    } else {
      modal.hidden = false;
      modal.classList.add('open');
    }
  };

  function setModoEditor(modo) {
    modoEditor = modo;
    const paneEdit = document.getElementById('paneFichEditor');
    const panePrev = document.getElementById('paneFichPreview');
    const btnToggle = document.getElementById('btnFichToggleModo');
    const textarea = document.getElementById('fichEditorTextarea');
    const prevHtml = document.getElementById('fichEditorPreviewHtml');

    if (modo === 'preview') {
      if (prevHtml && textarea) prevHtml.innerHTML = renderHtml(textarea.value);
      if (paneEdit) paneEdit.style.display = 'none';
      if (panePrev) panePrev.style.display = 'block';
      if (btnToggle) btnToggle.textContent = '✏️ Voltar ao Editor';
    } else {
      if (paneEdit) paneEdit.style.display = 'block';
      if (panePrev) panePrev.style.display = 'none';
      if (btnToggle) btnToggle.textContent = '👁️ Alternar Prévia / Editor';
    }
  }

  // Inicializar eventos do modal editor
  function initEditorEvents() {
    const btnSalvar = document.getElementById('btnFichSalvar');
    const btnToggle = document.getElementById('btnFichToggleModo');
    const btnCopiar = document.getElementById('btnFichCopiar');
    const btnBaixar = document.getElementById('btnFichBaixar');
    const btnRestaurar = document.getElementById('btnFichRestaurar');
    const textarea = document.getElementById('fichEditorTextarea');
    const statusEl = document.getElementById('fichEditorStatus');

    if (btnToggle) {
      btnToggle.onclick = () => {
        setModoEditor(modoEditor === 'editor' ? 'preview' : 'editor');
      };
    }

    if (btnCopiar && textarea) {
      btnCopiar.onclick = () => {
        navigator.clipboard.writeText(textarea.value).then(() => {
          const old = btnCopiar.textContent;
          btnCopiar.textContent = 'Copiado!';
          setTimeout(() => { btnCopiar.textContent = old; }, 2000);
        });
      };
    }

    if (btnBaixar && textarea) {
      btnBaixar.onclick = () => {
        baixarArquivoMd(editorArquivoAtual || `${editorCodigoAtual} — Fichamento.md`, textarea.value);
      };
    }

    if (btnSalvar && textarea) {
      btnSalvar.onclick = async () => {
        if (!editorCodigoAtual) return;
        const texto = textarea.value;
        localStorage.setItem('pandora_fich_' + editorCodigoAtual, texto);

        if (statusEl) {
          statusEl.textContent = '● Salvo localmente!';
          statusEl.style.color = 'var(--accent)';
        }

        // Tentar enviar para o servidor local Python (se estiver em execução na porta 8765)
        try {
          const resp = await fetch('/api/fichamento', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              codigo: editorCodigoAtual,
              arquivo: editorArquivoAtual,
              texto: texto
            })
          });
          if (resp.ok) {
            if (statusEl) statusEl.textContent = '✅ Salvo no cofre e no navegador!';
          }
        } catch (_) {
          // Servidor local não ativo (ex: rodando no GitHub Pages) — salvamento local garantido
        }

        // Atualizar lista e drawer
        renderIndice();
        if (window.renderArticles) window.renderArticles();
        if (window.drawerArticle && String(window.drawerArticle.codigo) === String(editorCodigoAtual)) {
          if (window.renderDrawerView) window.renderDrawerView(window.drawerArticle);
        }

        const oldBtn = btnSalvar.textContent;
        btnSalvar.textContent = '✓ Fichamento Salvo!';
        setTimeout(() => { btnSalvar.textContent = oldBtn; }, 2000);
      };
    }

    if (btnRestaurar) {
      btnRestaurar.onclick = () => {
        if (!editorCodigoAtual) return;
        if (confirm('Deseja descartar as alterações locais e restaurar a versão original do cofre?')) {
          localStorage.removeItem('pandora_fich_' + editorCodigoAtual);
          const orig = baseLista.find((x) => String(x.codigo) === String(editorCodigoAtual));
          if (orig && textarea) textarea.value = orig.md;
          btnRestaurar.style.display = 'none';
          if (statusEl) {
            statusEl.textContent = '✔️ Original do acervo restaurado';
            statusEl.style.color = 'var(--text-muted)';
          }
          renderIndice();
        }
      };
    }
  }

  // Abrir diretamente por código (vindo do drawer)
  window.abrirFichamentoPorCodigo = function (codigo) {
    const lista = getConsolidatedFichamentos();
    const f = lista.find((x) => String(x.codigo) === String(codigo));
    if (f) {
      abrir(f.arquivo);
    } else {
      window.abrirEditorFichamento(codigo);
    }
  };

  // Delegar cliques no box de fichamentos
  if (box) {
    box.addEventListener('click', (e) => {
      const card = e.target.closest('[data-fi]');
      const btnLer = e.target.closest('[data-fi-ler]');
      const btnEdit = e.target.closest('[data-fi-edit]');
      const btnNovo = e.target.closest('#btnNovoFichamentoTop');

      if (btnEdit) {
        e.stopPropagation();
        window.abrirEditorFichamento(btnEdit.dataset.fiEdit);
        return;
      }

      if (btnLer) {
        e.stopPropagation();
        abrir(btnLer.dataset.fiLer);
        return;
      }

      if (card) {
        abrir(card.dataset.fi);
        return;
      }

      if (btnNovo) {
        // Modal de seleção de artigo ou criar avulso
        const cod = prompt('Digite o código da fonte para fichar (ex: 26, 32, N01):');
        if (cod) window.abrirEditorFichamento(cod.trim());
        return;
      }

      if (e.target.id === 'fiVoltar') renderIndice();
    });
  }

  initEditorEvents();
  renderIndice();
})();
