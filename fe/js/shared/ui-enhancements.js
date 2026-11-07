/**
 * UI enhancements — theme, skeletons, mobile sidebar
 */
(function (global) {
  const THEME_KEY = 'pk_theme';

  function getTheme() {
    return localStorage.getItem(THEME_KEY) || 'light';
  }

  function setTheme(theme) {
    const next = theme === 'dark' ? 'dark' : 'light';
    document.documentElement.setAttribute('data-theme', next);
    localStorage.setItem(THEME_KEY, next);
    document.querySelectorAll('[data-theme-toggle]').forEach((btn) => {
      const icon = btn.querySelector('i');
      if (icon) icon.className = next === 'dark' ? 'fas fa-sun' : 'fas fa-moon';
      btn.setAttribute('aria-label', next === 'dark' ? 'Bật sáng' : 'Bật tối');
    });
  }

  function toggleTheme() {
    setTheme(getTheme() === 'dark' ? 'light' : 'dark');
  }

  function themeToggleHtml() {
    return `<button type="button" class="theme-toggle-btn" data-theme-toggle aria-label="Bật tối" title="Giao diện sáng/tối">
      <i class="fas fa-moon"></i>
    </button>`;
  }

  function bindThemeToggles() {
    document.querySelectorAll('[data-theme-toggle]').forEach((btn) => {
      if (btn.dataset.bound) return;
      btn.dataset.bound = '1';
      btn.addEventListener('click', toggleTheme);
    });
  }

  function closeMobileSidebar() {
    document.querySelectorAll('.admin-sidebar.open, .role-sidebar-shell.open').forEach((s) => {
      s.classList.remove('open');
    });
    const backdrop = document.getElementById('sidebar-backdrop');
    if (backdrop) backdrop.classList.remove('visible');
    document.body.style.overflow = '';
  }

  function openMobileSidebar(sidebar) {
    let backdrop = document.getElementById('sidebar-backdrop');
    if (!backdrop) {
      backdrop = document.createElement('div');
      backdrop.id = 'sidebar-backdrop';
      backdrop.className = 'sidebar-backdrop';
      backdrop.setAttribute('aria-hidden', 'true');
      backdrop.addEventListener('click', closeMobileSidebar);
      document.body.appendChild(backdrop);
    }
    sidebar.classList.add('open');
    backdrop.classList.add('visible');
    document.body.style.overflow = 'hidden';
  }

  function bindMobileSidebar(toggleId, sidebarId) {
    const btn = document.getElementById(toggleId);
    const side = document.getElementById(sidebarId);
    if (!btn || !side || btn.dataset.shellBound) return;
    btn.dataset.shellBound = '1';
    btn.addEventListener('click', () => {
      if (side.classList.contains('open')) closeMobileSidebar();
      else openMobileSidebar(side);
    });
  }

  function statGridSkeleton(count) {
    const n = count || 4;
    let html = '<div class="skeleton-stat-grid">';
    for (let i = 0; i < n; i++) html += '<div class="skeleton skeleton-stat-card"></div>';
    return html + '</div>';
  }

  function tableSkeleton(rows) {
    const n = rows || 5;
    let html = '<div class="skeleton-table-wrap">';
    for (let i = 0; i < n; i++) html += '<div class="skeleton skeleton-table-row"></div>';
    return html + '</div>';
  }

  function init() {
    setTheme(getTheme());
    bindThemeToggles();
    if (!document.getElementById('sidebar-backdrop')) {
      const el = document.createElement('div');
      el.id = 'sidebar-backdrop';
      el.className = 'sidebar-backdrop';
      el.setAttribute('aria-hidden', 'true');
      el.addEventListener('click', closeMobileSidebar);
      document.body.appendChild(el);
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  /** YYYY-MM-DD theo giờ máy người dùng */
  function ngayHomNayYMD(d) {
    const dt = d instanceof Date ? d : new Date();
    const y = dt.getFullYear();
    const m = String(dt.getMonth() + 1).padStart(2, '0');
    const day = String(dt.getDate()).padStart(2, '0');
    return `${y}-${m}-${day}`;
  }

  /** Giá trị min cho input type="datetime-local" (không chọn quá khứ) */
  function datetimeLocalMinNow() {
    const now = new Date();
    now.setSeconds(0, 0);
    return new Date(now.getTime() - now.getTimezoneOffset() * 60000).toISOString().slice(0, 16);
  }

  function laNgayQuaKhu(ymd, homNay) {
    if (!ymd) return false;
    const today = homNay || ngayHomNayYMD();
    return String(ymd).slice(0, 10) < today;
  }

  global.UIEnhance = {
    getTheme,
    setTheme,
    toggleTheme,
    themeToggleHtml,
    bindThemeToggles,
    bindMobileSidebar,
    closeMobileSidebar,
    statGridSkeleton,
    tableSkeleton,
    ngayHomNayYMD,
    datetimeLocalMinNow,
    laNgayQuaKhu,
    init,
  };
})(window);
