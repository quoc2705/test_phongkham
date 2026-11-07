/**
 * Chuông thông báo dùng chung — API /api/thong-bao/ (nguoidung.ThongBao)
 */
const ThongBaoBell = {
  _poll: null,
  _open: false,
  _items: [],
  _badgeId: 'pk-noti-badge',

  htmlButton() {
    const id = this._badgeId;
    return `
      <button type="button" class="notification-bell" onclick="ThongBaoBell.togglePopup(event)"
        title="Thông báo" aria-label="Thông báo">
        <i class="fas fa-bell"></i>
        <span id="${id}" class="badge" style="display:none">0</span>
      </button>`;
  },

  init(opts = {}) {
    if (opts.badgeId) this._badgeId = opts.badgeId;
    this.taiThongBao();
    if (this._poll) clearInterval(this._poll);
    this._poll = setInterval(() => this.taiThongBao(false), 20000);
  },

  destroy() {
    if (this._poll) clearInterval(this._poll);
    this._poll = null;
    this._open = false;
    const panel = document.getElementById('pk-noti-popup');
    if (panel) panel.remove();
  },

  async taiThongBao(showToast = false) {
    const res = await Http.layDanhSach('/thong-bao/?page=1&page_size=20');
    const list = Array.isArray(res?.data) ? res.data : (res?.data?.results || []);
    const oldUnread = this._items.filter((i) => !this._daDoc(i)).length;
    this._items = list;
    const unread = list.filter((i) => !this._daDoc(i)).length;
    const badge = document.getElementById(this._badgeId);
    if (badge) {
      badge.textContent = unread > 99 ? '99+' : String(unread);
      badge.style.display = unread > 0 ? 'inline-block' : 'none';
    }
    if (showToast && unread > oldUnread) {
      Toast.hien('Thông báo mới', 'Bạn có thông báo mới từ hệ thống', 'info');
    }
    if (this._open) this.renderPopup();
  },

  _daDoc(item) {
    return !!(item.da_xem || item.da_doc || item.da_doc_luc);
  },

  togglePopup(event) {
    if (event) event.stopPropagation();
    this._open = !this._open;
    this.renderPopup();
  },

  renderPopup() {
    let panel = document.getElementById('pk-noti-popup');
    if (!this._open) {
      if (panel) panel.remove();
      return;
    }
    if (!panel) {
      panel = document.createElement('div');
      panel.id = 'pk-noti-popup';
      panel.className = 'pk-noti-popup';
      document.body.appendChild(panel);
      setTimeout(() => {
        document.addEventListener('click', (e) => {
          if (!document.getElementById('pk-noti-popup')) return;
          if (
            !e.target.closest('#pk-noti-popup') &&
            !e.target.closest(`#${this._badgeId}`) &&
            !e.target.closest('.notification-bell')
          ) {
            this._open = false;
            this.renderPopup();
          }
        }, { once: true });
      }, 0);
    }
    const rows = this._items.length
      ? this._items
          .map((i) => {
            const read = this._daDoc(i);
            const loai = i.loai_display || i.loai_thong_bao_display || i.loai || '';
            const time = i.created_at || i.ngay_tao || '';
            const timeLbl = time ? this._formatTime(time) : '';
            return `<article class="pk-noti-item ${read ? 'is-read' : ''}" onclick="ThongBaoBell.danhDau('${i.id}')">
              <div class="pk-noti-item-title">${this._esc(i.tieu_de || 'Thông báo')}</div>
              ${loai ? `<span class="pk-noti-item-loai">${this._esc(loai)}</span>` : ''}
              <div class="pk-noti-item-body">${this._esc(i.noi_dung || '')}</div>
              ${timeLbl ? `<div class="pk-noti-item-time">${this._esc(timeLbl)}</div>` : ''}
            </article>`;
          })
          .join('')
      : '<p class="text-muted pk-noti-empty">Không có thông báo</p>';

    panel.innerHTML = `
      <div class="pk-noti-popup-head">
        <strong><i class="fas fa-bell"></i> Thông báo</strong>
        <button type="button" class="btn btn-outline btn-sm" onclick="ThongBaoBell.danhDauTatCa()">Đã đọc tất cả</button>
      </div>
      <div class="pk-noti-popup-list">${rows}</div>`;
  },

  _formatTime(iso) {
    try {
      const d = new Date(iso);
      if (Number.isNaN(d.getTime())) return String(iso).slice(0, 16);
      return d.toLocaleString('vi-VN', { hour: '2-digit', minute: '2-digit', day: '2-digit', month: '2-digit' });
    } catch {
      return String(iso).slice(0, 16);
    }
  },

  async danhDau(id) {
    await Http.tao(`/thong-bao/${id}/mark_as_read/`, {});
    await this.taiThongBao();
  },

  async danhDauTatCa() {
    await Http.tao('/thong-bao/mark_all_as_read/', {});
    await this.taiThongBao();
  },

  _esc(s) {
    if (s == null) return '';
    return String(s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  },
};

window.ThongBaoBell = ThongBaoBell;
