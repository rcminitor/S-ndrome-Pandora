/* ==========================================================================
   Síndrome de Pandora — Tese de Doutorado (UFC)
   JavaScript Application Logic
   ========================================================================== */

const LIDOS_KEY = 'pandora.lidos.v1';
const EDITS_KEY = 'pandora.edits.v1';

let lidos = {};
let edits = {};

try { lidos = JSON.parse(localStorage.getItem(LIDOS_KEY)) || {}; } catch (e) {}
try { edits = JSON.parse(localStorage.getItem(EDITS_KEY)) || {}; } catch (e) {}

function saveLidos() {
  try { localStorage.setItem(LIDOS_KEY, JSON.stringify(lidos)); } catch (e) {}
}

function saveEdits() {
  try { localStorage.setItem(EDITS_KEY, JSON.stringify(edits)); } catch (e) {}
}

function getMergedData() {
  return (window.DADOS_INVENTARIO || []).map(item => {
    const edit = edits[item.codigo];
    return edit ? { ...item, ...edit } : item;
  });
}

document.addEventListener('DOMContentLoaded', () => {
  initTheme();
  initTabs();
  initInventory();
  initDrawer();
});

// --------------------------------------------------------------------------
// 1. Theme Toggle (Dark / Light)
// --------------------------------------------------------------------------
function initTheme() {
  const themeBtn = document.getElementById('themeToggleBtn');
  const themeText = document.getElementById('themeText');
  let savedTheme = 'light';
  try { savedTheme = localStorage.getItem('pandora_tema') || 'light'; } catch (e) {}

  setTheme(savedTheme);

  if (themeBtn) {
    themeBtn.addEventListener('click', () => {
      const next = document.documentElement.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
      setTheme(next);
      try { localStorage.setItem('pandora_tema', next); } catch (e) {}
    });
  }

  function setTheme(mode) {
    if (mode === 'dark') {
      document.documentElement.setAttribute('data-theme', 'dark');
      if (themeText) themeText.textContent = 'Tema';
    } else {
      document.documentElement.removeAttribute('data-theme');
      if (themeText) themeText.textContent = 'Tema';
    }
  }
}

// --------------------------------------------------------------------------
// 2. Tabs Navigation
// --------------------------------------------------------------------------
function initTabs() {
  const tabBtns = document.querySelectorAll('.tab-btn');
  const tabPanes = document.querySelectorAll('.tab-pane');

  tabBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      const targetId = btn.getAttribute('data-tab');

      tabBtns.forEach(b => b.classList.remove('active'));
      tabPanes.forEach(p => p.classList.remove('active'));

      btn.classList.add('active');
      const targetPane = document.getElementById(targetId);
      if (targetPane) {
        targetPane.classList.add('active');
      }
    });
  });
}

// --------------------------------------------------------------------------
// 3. Inventory Dashboard (Search & Filters)
// --------------------------------------------------------------------------
let currentFilter = 'all';
let currentSearch = '';

function initInventory() {
  const data = getMergedData();
  updateKpis(data);

  const searchInput = document.getElementById('searchInput');
  const filterPills = document.querySelectorAll('.filter-pill');

  if (searchInput) {
    searchInput.addEventListener('input', (e) => {
      currentSearch = e.target.value.toLowerCase().trim();
      renderArticles();
    });
  }

  filterPills.forEach(pill => {
    pill.addEventListener('click', () => {
      filterPills.forEach(p => p.classList.remove('active'));
      pill.classList.add('active');
      currentFilter = pill.getAttribute('data-filter');
      renderArticles();
    });
  });

  renderArticles();
}

function updateKpis(data) {
  const n1Count = data.filter(d => (d.nucleo || '').includes('Nucleo 1')).length;
  const n2Count = data.filter(d => (d.nucleo || '').includes('Nucleo 2')).length;
  const priorityCount = data.filter(d => (d.fase || '').toLowerCase().includes('ler primeiro')).length;
  const fichadosCount = data.filter(d => (d.status || '').toLowerCase().includes('fichamento concluido')).length;

  const elTotal = document.getElementById('kpiTotal');
  const elN1 = document.getElementById('kpiN1');
  const elN2 = document.getElementById('kpiN2');
  const elPriority = document.getElementById('kpiPriority');
  const elFichados = document.getElementById('kpiFichados');
  const acervoBadge = document.getElementById('acervoBadge');

  if (elTotal) elTotal.textContent = data.length;
  if (elN1) elN1.textContent = n1Count;
  if (elN2) elN2.textContent = n2Count;
  if (elPriority) elPriority.textContent = priorityCount;
  if (elFichados) elFichados.textContent = fichadosCount;
  if (acervoBadge) acervoBadge.textContent = data.length;
}

function renderArticles() {
  const container = document.getElementById('articlesGrid');
  const countLabel = document.getElementById('resultCount');
  if (!container) return;

  const data = getMergedData();

  const filtered = data.filter(item => {
    const searchMatch = !currentSearch ||
      (item.titulo || '').toLowerCase().includes(currentSearch) ||
      (item.codigo || '').toLowerCase().includes(currentSearch) ||
      (item.grupo || '').toLowerCase().includes(currentSearch) ||
      (item.ano || '').toLowerCase().includes(currentSearch) ||
      (item.referencia || '').toLowerCase().includes(currentSearch);

    if (!searchMatch) return false;

    if (currentFilter === 'all') return true;
    if (currentFilter === 'n1') return (item.nucleo || '').includes('Nucleo 1');
    if (currentFilter === 'n2') return (item.nucleo || '').includes('Nucleo 2');
    if (currentFilter === 'ler-primeiro') return (item.fase || '').toLowerCase().includes('ler primeiro');
    if (currentFilter === 'fichados') return (item.status || '').toLowerCase().includes('fichamento concluido');
    if (currentFilter === 'com-pdf') return item.arquivo && item.arquivo.trim() !== '' && !item.arquivo.includes('NAO CONFIRMADO');
    if (currentFilter === 'lidos') return lidos[item.codigo] === true;

    return true;
  });

  if (countLabel) {
    const lidosCount = data.filter(d => lidos[d.codigo] === true).length;
    countLabel.textContent = `Exibindo ${filtered.length} de ${data.length} artigos — ${lidosCount} marcados como lidos`;
  }

  if (filtered.length === 0) {
    container.innerHTML = `
      <div style="grid-column: 1 / -1; padding: 48px; text-align: center; color: var(--text-dim);">
        <p style="font-size: 1.1rem; margin-bottom: 8px;">Nenhum artigo encontrado para os filtros selecionados.</p>
        <p style="font-size: 0.85rem;">Tente buscar por outro termo ou limpar os filtros.</p>
      </div>
    `;
    return;
  }

  container.innerHTML = filtered.map(item => {
    const isFichado = (item.status || '').toLowerCase().includes('fichamento concluido');
    const isLerPrimeiro = (item.fase || '').toLowerCase().includes('ler primeiro');
    const isLido = lidos[item.codigo] === true;
    const isEdited = !!edits[item.codigo];

    let statusClass = 'status-later';
    let statusText = item.fase || 'Classificar';

    if (isFichado) {
      statusClass = 'status-done';
      statusText = 'Fichado';
    } else if (isLerPrimeiro) {
      statusClass = 'status-priority';
      statusText = 'Ler primeiro';
    }

    const safeTitle = escapeHtml(item.titulo || 'Sem título');
    const safeTheme = escapeHtml(item.grupo || 'Tema geral');
    const safeWhy = escapeHtml(item.porQueLer || item.comoUsar || 'Sem descrição cadastrada.');
    const safeCode = escapeHtml(item.codigo);

    return `
      <div class="article-card${isLido ? ' card-lido' : ''}" data-code="${safeCode}">
        <div>
          <div class="article-header">
            <span class="article-code">#${safeCode}</span>
            <span class="article-year">${escapeHtml(item.ano || 'S/D')}</span>
            ${isEdited ? '<span style="font-size:0.7rem;color:var(--accent);font-weight:700;margin-left:4px" title="Editado localmente">✎</span>' : ''}
          </div>
          <h3 class="article-title" title="${safeTitle}">${safeTitle}</h3>
          <div class="article-theme">${safeTheme}</div>
          <p class="article-why">${safeWhy}</p>
        </div>
        <div class="article-footer">
          <span class="status-badge ${statusClass}">${statusText}</span>
          <div class="article-actions">
            <button class="btn-lido${isLido ? ' btn-lido-ativo' : ''}" type="button" data-lido-code="${safeCode}" title="${isLido ? 'Marcar como não lido' : 'Marcar como lido'}">
              ${isLido ? '✓ Lido' : 'Eu li'}
            </button>
            <button class="btn-card-details" type="button">Ver detalhes</button>
          </div>
        </div>
      </div>
    `;
  }).join('');

  container.querySelectorAll('.btn-lido').forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      const code = btn.getAttribute('data-lido-code');
      lidos[code] = !lidos[code];
      saveLidos();
      renderArticles();
    });
  });

  container.querySelectorAll('.article-card').forEach(card => {
    card.addEventListener('click', (e) => {
      if (e.target.classList.contains('btn-lido')) return;
      const code = card.getAttribute('data-code');
      const article = getMergedData().find(a => String(a.codigo) === String(code));
      if (article) openDrawer(article);
    });
  });
}

// --------------------------------------------------------------------------
// 4. Modal / Detail Drawer
// --------------------------------------------------------------------------
let drawerArticle = null;

function initDrawer() {
  const overlay = document.getElementById('drawerOverlay');
  const closeBtn = document.getElementById('drawerCloseBtn');

  if (closeBtn) closeBtn.addEventListener('click', closeDrawer);

  if (overlay) {
    overlay.addEventListener('click', (e) => {
      if (e.target === overlay) closeDrawer();
    });
  }

  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') closeDrawer();
  });

  const editBtn = document.getElementById('drawerEditBtn');
  const saveBtn = document.getElementById('drawerSaveBtn');
  const cancelBtn = document.getElementById('drawerCancelBtn');

  if (editBtn) editBtn.addEventListener('click', enterEditMode);
  if (saveBtn) saveBtn.addEventListener('click', saveEdit);
  if (cancelBtn) cancelBtn.addEventListener('click', exitEditMode);
}

function openDrawer(article) {
  drawerArticle = article;
  const overlay = document.getElementById('drawerOverlay');
  if (!overlay) return;

  exitEditMode();
  renderDrawerView(article);

  overlay.classList.add('open');
  document.body.style.overflow = 'hidden';
}

function renderDrawerView(article) {
  document.getElementById('drawerCode').textContent = `#${article.codigo} (${article.ano || 'Ano não confirmado'})`;
  document.getElementById('drawerTitle').textContent = article.titulo || 'Sem título';
  document.getElementById('drawerTheme').textContent = article.grupo || 'Geral';
  document.getElementById('drawerNucleo').textContent = article.nucleo || 'Não classificado';
  document.getElementById('drawerWhy').textContent = article.porQueLer || 'Não especificado';
  document.getElementById('drawerHowToUse').textContent = article.comoUsar || 'Não especificado';
  document.getElementById('drawerCaution').textContent = article.cautelas || 'Nenhuma cautela registrada';
  document.getElementById('drawerStudyType').textContent = article.tipoEstudo || 'Não especificado';

  const refBox = document.getElementById('drawerRef');
  const refText = article.referencia && article.referencia !== 'NAO CONFIRMADO'
    ? article.referencia
    : 'Referência ABNT ainda NÃO CONFIRMADA no artigo original.';
  refBox.textContent = refText;

  const copyBtn = document.getElementById('drawerCopyRefBtn');
  if (copyBtn) {
    copyBtn.onclick = () => {
      navigator.clipboard.writeText(refText).then(() => {
        copyBtn.textContent = 'Copiado!';
        setTimeout(() => { copyBtn.textContent = 'Copiar Referência ABNT'; }, 2000);
      });
    };
  }

  const fileBox = document.getElementById('drawerFile');
  fileBox.textContent = article.arquivo || 'Arquivo ainda não obtido';

  // Botão PDF
  const pdfBtn = document.getElementById('drawerPdfBtn');
  if (pdfBtn) {
    const hasFile = article.arquivo && article.arquivo.trim() !== '' &&
                    !article.arquivo.includes('NAO CONFIRMADO') &&
                    !article.arquivo.includes('NÃO CONFIRMADO');
    if (hasFile) {
      pdfBtn.style.display = 'inline-flex';
      pdfBtn.onclick = () => window.open(article.arquivo, '_blank');
    } else {
      pdfBtn.style.display = 'none';
    }
  }

  // Badge "editado localmente"
  const badge = document.getElementById('drawerEditBadge');
  if (badge) badge.style.display = edits[article.codigo] ? 'block' : 'none';

  // Botão "Eu li"
  const drawerLidoBtn = document.getElementById('drawerLidoBtn');
  if (drawerLidoBtn) {
    const isLido = lidos[article.codigo] === true;
    drawerLidoBtn.textContent = isLido ? '✓ Marcado como lido' : 'Marcar como lido';
    drawerLidoBtn.className = 'btn-drawer-lido' + (isLido ? ' btn-lido-ativo' : '');
    drawerLidoBtn.onclick = () => {
      lidos[article.codigo] = !lidos[article.codigo];
      saveLidos();
      const nowLido = lidos[article.codigo] === true;
      drawerLidoBtn.textContent = nowLido ? '✓ Marcado como lido' : 'Marcar como lido';
      drawerLidoBtn.className = 'btn-drawer-lido' + (nowLido ? ' btn-lido-ativo' : '');
      renderArticles();
    };
  }
}

// Campos editáveis: { elementId, dataKey, type }
const EDIT_FIELDS = [
  { id: 'drawerTitle',     key: 'titulo',     type: 'input'    },
  { id: 'drawerNucleo',    key: 'nucleo',     type: 'input'    },
  { id: 'drawerStudyType', key: 'tipoEstudo', type: 'input'    },
  { id: 'drawerWhy',       key: 'porQueLer',  type: 'textarea' },
  { id: 'drawerHowToUse',  key: 'comoUsar',   type: 'textarea' },
  { id: 'drawerCaution',   key: 'cautelas',   type: 'textarea' },
  { id: 'drawerRef',       key: 'referencia', type: 'textarea' },
];

function enterEditMode() {
  if (!drawerArticle) return;

  EDIT_FIELDS.forEach(({ id, key, type }) => {
    const el = document.getElementById(id);
    if (!el) return;
    const currentVal = drawerArticle[key] || '';
    const input = document.createElement(type);
    input.className = 'drawer-edit-input';
    input.value = currentVal;
    if (type === 'textarea') input.rows = 3;
    input.dataset.editKey = key;
    el.replaceWith(input);
    input.id = id; // manter o id
  });

  document.getElementById('drawerEditBtn').style.display = 'none';
  document.getElementById('drawerSaveBtn').style.display = 'inline-flex';
  document.getElementById('drawerCancelBtn').style.display = 'inline-flex';
  document.getElementById('drawerLidoBtn').style.display = 'none';
}

function saveEdit() {
  if (!drawerArticle) return;

  const patch = {};
  EDIT_FIELDS.forEach(({ id, key }) => {
    const el = document.getElementById(id);
    if (el && el.dataset.editKey) {
      patch[key] = el.value.trim();
    }
  });

  // Mesclar com edição anterior (se houver) e com dados base
  edits[drawerArticle.codigo] = { ...(edits[drawerArticle.codigo] || {}), ...patch };
  saveEdits();

  // Atualizar drawerArticle com os novos valores
  drawerArticle = { ...drawerArticle, ...patch };

  exitEditMode();
  renderDrawerView(drawerArticle);
  renderArticles();
  updateKpis(getMergedData());
}

function exitEditMode() {
  // Se estiver em modo edição, restaurar os elementos originais
  EDIT_FIELDS.forEach(({ id, type }) => {
    const el = document.getElementById(id);
    if (el && el.tagName.toLowerCase() === type && el.dataset.editKey) {
      const div = document.createElement(id === 'drawerTitle' ? 'h2' : 'div');
      div.id = id;
      if (id === 'drawerTitle') {
        div.style.cssText = 'font-size: 1.25rem; font-weight: 800; line-height: 1.4;';
      } else if (id === 'drawerRef') {
        div.className = 'drawer-code-block';
      } else {
        div.className = 'drawer-text';
      }
      el.replaceWith(div);
    }
  });

  const editBtn = document.getElementById('drawerEditBtn');
  const saveBtn = document.getElementById('drawerSaveBtn');
  const cancelBtn = document.getElementById('drawerCancelBtn');
  const lidoBtn = document.getElementById('drawerLidoBtn');

  if (editBtn) editBtn.style.display = 'inline-flex';
  if (saveBtn) saveBtn.style.display = 'none';
  if (cancelBtn) cancelBtn.style.display = 'none';
  if (lidoBtn) lidoBtn.style.display = 'inline-flex';
}

function closeDrawer() {
  exitEditMode();
  drawerArticle = null;
  const overlay = document.getElementById('drawerOverlay');
  if (overlay) overlay.classList.remove('open');
  document.body.style.overflow = '';
}

// --------------------------------------------------------------------------
// Utility
// --------------------------------------------------------------------------
function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}
