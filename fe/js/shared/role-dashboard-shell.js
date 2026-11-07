/**
 * Layout dashboard vai trò — sidebar + header (styles: css/layout-shell.css)
 */
(function (global) {
  function esc(s) {
    if (s == null) return '';
    return String(s).replace(/[&<>"']/g, (c) =>
      ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c])
    );
  }

  function avatarText(name, explicit) {
    if (explicit) return esc(String(explicit).slice(0, 3).toUpperCase());
    if (global.UI && typeof global.UI.kyTuDau === 'function') return esc(global.UI.kyTuDau(name));
    const t = (name || '').trim().split(/\s+/).filter(Boolean);
    if (t.length >= 2) return esc((t[0][0] + t[t.length - 1][0]).toUpperCase());
    if (t.length === 1 && t[0].length) return esc(t[0].slice(0, 2).toUpperCase());
    return esc('?');
  }

  function themeBtn() {
    return global.UIEnhance && global.UIEnhance.themeToggleHtml
      ? global.UIEnhance.themeToggleHtml()
      : '';
  }

  function layoutHtml(o) {
    const brandAccent = o.brandAccent != null ? o.brandAccent : '';
    const icon = o.brandIcon || 'fa-hospital-user';
    const innerW = o.contentMaxWidth || '1280px';
    const extra = o.headerActionsExtra || '';
    const above = o.aboveMainContent || '';
    const av = avatarText(o.userName, o.avatarText);

    return `
      <div class="admin-dashboard role-shell-root">
        <aside class="admin-sidebar role-sidebar-shell" id="role-shell-sidebar">
          <div class="sidebar-header">
            <div class="logo">
              <i class="fas ${esc(icon)}"></i>
              <span>${esc(o.brandTitle || 'PhòngKhám+')}<span>${esc(brandAccent)}</span></span>
            </div>
          </div>
          <nav class="sidebar-nav" aria-label="Menu chính">${o.navHtml}</nav>
          <div class="sidebar-footer">
            <button type="button" class="btn-logout" onclick="App.logout()">
              <i class="fas fa-sign-out-alt"></i>
              <span>Đăng xuất</span>
            </button>
          </div>
        </aside>
        <main class="admin-main">
          <header class="admin-header">
            <button type="button" class="menu-toggle" id="role-shell-menu-toggle" aria-label="Mở menu">
              <i class="fas fa-bars"></i>
            </button>
            <div class="header-search-spacer" aria-hidden="true"></div>
            <div class="header-actions">
              ${themeBtn()}
              ${extra}
              <div class="user-menu">
                <div class="user-avatar" id="role-shell-user-avatar">${av}</div>
                <div class="user-info">
                  <div class="user-name" id="role-shell-user-name">${esc(o.userName || '')}</div>
                  <div class="user-role" id="role-shell-user-role">${esc(o.userRoleLabel || '')}</div>
                </div>
                <i class="fas fa-chevron-down" style="font-size:12px;color:var(--c-muted)" aria-hidden="true"></i>
              </div>
            </div>
          </header>
          <div class="admin-content">
            <div class="role-shell-inner" style="max-width:${esc(innerW)}">
              ${above}
              <div id="${esc(o.mainHostId)}"></div>
            </div>
          </div>
        </main>
      </div>`;
  }

  function bindShellControls() {
    if (global.UIEnhance && global.UIEnhance.bindMobileSidebar) {
      global.UIEnhance.bindMobileSidebar('role-shell-menu-toggle', 'role-shell-sidebar');
    } else {
      const btn = document.getElementById('role-shell-menu-toggle');
      const side = document.getElementById('role-shell-sidebar');
      if (btn && side) btn.addEventListener('click', () => side.classList.toggle('open'));
    }
    if (global.UIEnhance) global.UIEnhance.bindThemeToggles();
  }

  function mount(rootId, options) {
    const root = document.getElementById(rootId);
    if (!root) return;
    root.innerHTML = layoutHtml(options);
    bindShellControls();
  }

  global.RoleDashboardShell = { esc, layoutHtml, bindShellControls, mount };
})(window);
