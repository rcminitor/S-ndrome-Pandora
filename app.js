/* ==========================================================================
   Síndrome de Pandora — Tese de Doutorado (UFC)
   JavaScript Application Logic
   ========================================================================== */

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
  const data = window.DADOS_INVENTARIO || [];
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

  if (elTotal) elTotal.textContent = data.length || 64;
  if (elN1) elN1.textContent = n1Count;
  if (elN2) elN2.textContent = n2Count;
  if (elPriority) elPriority.textContent = priorityCount;
  if (elFichados) elFichados.textContent = fichadosCount;
}

function renderArticles() {
  const container = document.getElementById('articlesGrid');
  const countLabel = document.getElementById('resultCount');
  if (!container) return;

  const data = window.DADOS_INVENTARIO || [];

  const filtered = data.filter(item => {
    // 1. Text Search Match
    const searchMatch = !currentSearch ||
      (item.titulo || '').toLowerCase().includes(currentSearch) ||
      (item.codigo || '').toLowerCase().includes(currentSearch) ||
      (item.grupo || '').toLowerCase().includes(currentSearch) ||
      (item.ano || '').toLowerCase().includes(currentSearch) ||
      (item.referencia || '').toLowerCase().includes(currentSearch);

    if (!searchMatch) return false;

    // 2. Filter Pill Match
    if (currentFilter === 'all') return true;
    if (currentFilter === 'n1') return (item.nucleo || '').includes('Nucleo 1');
    if (currentFilter === 'n2') return (item.nucleo || '').includes('Nucleo 2');
    if (currentFilter === 'ler-primeiro') return (item.fase || '').toLowerCase().includes('ler primeiro');
    if (currentFilter === 'fichados') return (item.status || '').toLowerCase().includes('fichamento concluido');
    if (currentFilter === 'com-pdf') return item.arquivo && item.arquivo.trim() !== '' && !item.arquivo.includes('NAO CONFIRMADO');

    return true;
  });

  if (countLabel) {
    countLabel.textContent = `Exibindo ${filtered.length} de ${data.length} artigos catalogados`;
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

    return `
      <div class="article-card" data-code="${escapeHtml(item.codigo)}">
        <div>
          <div class="article-header">
            <span class="article-code">#${escapeHtml(item.codigo)}</span>
            <span class="article-year">${escapeHtml(item.ano || 'S/D')}</span>
          </div>
          <h3 class="article-title" title="${safeTitle}">${safeTitle}</h3>
          <div class="article-theme">${safeTheme}</div>
          <p class="article-why">${safeWhy}</p>
        </div>
        <div class="article-footer">
          <span class="status-badge ${statusClass}">${statusText}</span>
          <button class="btn-card-details" type="button">Ver detalhes</button>
        </div>
      </div>
    `;
  }).join('');

  // Attach click listener for drawer opening
  container.querySelectorAll('.article-card').forEach(card => {
    card.addEventListener('click', () => {
      const code = card.getAttribute('data-code');
      const article = (window.DADOS_INVENTARIO || []).find(a => String(a.codigo) === String(code));
      if (article) openDrawer(article);
    });
  });
}

// --------------------------------------------------------------------------
// 4. Modal / Detail Drawer
// --------------------------------------------------------------------------
function initDrawer() {
  const overlay = document.getElementById('drawerOverlay');
  const closeBtn = document.getElementById('drawerCloseBtn');

  if (closeBtn) {
    closeBtn.addEventListener('click', closeDrawer);
  }

  if (overlay) {
    overlay.addEventListener('click', (e) => {
      if (e.target === overlay) closeDrawer();
    });
  }

  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') closeDrawer();
  });
}

function openDrawer(article) {
  const overlay = document.getElementById('drawerOverlay');
  if (!overlay) return;

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
        copyBtn.textContent = 'Copiado para a área de transferência!';
        setTimeout(() => {
          copyBtn.textContent = 'Copiar Referência ABNT';
        }, 2000);
      });
    };
  }

  const fileBox = document.getElementById('drawerFile');
  fileBox.textContent = article.arquivo || 'Arquivo ainda não obtido';

  overlay.classList.add('open');
  document.body.style.overflow = 'hidden';
}

function closeDrawer() {
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
