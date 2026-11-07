/**
 * Chat BN <-> BS: backend get-or-create theo cap (benh_nhan_id, bac_si_id) — khong can tao phong thu cong.
 */
const PageChatBenhNhan = {
  _hostElementId: 'benh-nhan-main-content',
  _role: '',
  _benhNhanId: null,
  _bacSiId: null,
  _activeRoom: null,
  _phong: null,
  _rooms: [],

  _userRaw() {
    try {
      return JSON.parse(localStorage.getItem('user_info') || '{}');
    } catch {
      return {};
    }
  },

  _esc(s) {
    return String(s || '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  },

  async render(options = {}) {
    this._hostElementId = options?.hostElementId || this._hostElementId;
    const raw = this._userRaw();
    this._role = (raw.vai_tro || '').toUpperCase();

    this._bacSiId = options?.bacSiId || raw.bac_si_id || null;
    this._benhNhanId = options?.benhNhanId || raw.benh_nhan_id || null;

    if (this._role === 'BENH_NHAN' && raw.role_data && raw.role_data.id) {
      this._benhNhanId = this._benhNhanId || raw.role_data.id;
    }
    if (this._role === 'BAC_SI' && raw.role_data && raw.role_data.id) {
      this._bacSiId = this._bacSiId || raw.role_data.id;
    }

    if (this._role === 'BAC_SI') {
      this._benhNhanId = options?.benhNhanId || this._benhNhanId;
    }

    const title = this._role === 'BAC_SI' ? 'Chat voi benh nhan' : 'Chat voi bac si';

    UI.render(this._hostElementId, `
      <div class="card">
        <div class="card-header" style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px">
          <div class="card-title">${this._esc(title)}</div>
        </div>
        <div class="card-body" style="display:grid;grid-template-columns:minmax(260px,320px) 1fr;gap:12px;min-height:520px">
          <div style="border:1px solid #e2e8f0;border-radius:10px;overflow:hidden;display:flex;flex-direction:column">
            <div style="padding:10px;border-bottom:1px solid #e2e8f0;background:#f8fafc">
              ${this._role === 'BENH_NHAN' ? `
                <label class="small text-muted">Chon bac si</label>
                <select id="chat-bac-si-select" class="form-control form-control-sm mb-2"></select>
                <button type="button" class="btn btn-primary btn-sm w-100" onclick="PageChatBenhNhan.moKenhTheoCap()">Vao chat</button>
              ` : `
                <label class="small text-muted">UUID benh nhan</label>
                <input id="chat-benh-nhan-id" class="form-control form-control-sm mb-2" placeholder="Benh nhan id"
                  value="${this._esc(this._benhNhanId || '')}"/>
                <button type="button" class="btn btn-primary btn-sm w-100 mb-2" onclick="PageChatBenhNhan.moKenhTheoCap()">Vao chat</button>
                <div class="small text-muted">Hoi thoai gan day</div>
              `}
            </div>
            <div id="bn-chat-rooms" style="flex:1;overflow:auto"></div>
          </div>
          <div style="border:1px solid #e2e8f0;border-radius:10px;display:flex;flex-direction:column;min-width:0">
            <div id="bn-chat-header" style="padding:10px 12px;border-bottom:1px solid #e2e8f0;color:#64748b;font-weight:600">
              Chon doi tac hoac hoi thoai de bat dau
            </div>
            <div id="bn-chat-messages" style="flex:1;padding:10px;overflow:auto;background:#f8fafc"></div>
            <div style="padding:10px;border-top:1px solid #e2e8f0;display:flex;gap:8px">
              <input id="bn-chat-input" class="form-control" placeholder="Nhap tin nhan..." ${this._role ? '' : 'disabled'}>
              <button type="button" class="btn btn-primary" onclick="PageChatBenhNhan.guiTinNhan()"><i class="fas fa-paper-plane"></i></button>
            </div>
          </div>
        </div>
      </div>
    `);

    document.getElementById('bn-chat-input')?.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') this.guiTinNhan();
    });

    if (this._role === 'BENH_NHAN') {
      await this._napDanhSachBacSi();
    }

    await this.taiDanhSachPhong();

    if (this._role === 'BENH_NHAN' && this._bacSiId) {
      const sel = document.getElementById('chat-bac-si-select');
      if (sel) sel.value = this._bacSiId;
    }

    if (this._role === 'BAC_SI' && this._benhNhanId) {
      await this.moKenhTheoCap();
    } else if (this._role === 'BENH_NHAN' && this._bacSiId) {
      await this.moKenhTheoCap();
    }
  },

  async _napDanhSachBacSi() {
    const sel = document.getElementById('chat-bac-si-select');
    if (!sel) return;
    const res = await Http.layDanhSach('/bac-si/?limit=200');
    const arr = Array.isArray(res?.data) ? res.data : res?.data?.results || [];
    sel.innerHTML =
      '<option value="">-- Chon bac si --</option>' +
      arr
        .map(
          (b) =>
            `<option value="${this._esc(b.id)}">${this._esc(b.ho_ten || b.ma_bac_si || b.id)}</option>`
        )
        .join('');
  },

  /** Mo hoac lay phong 1-1 theo cap (POST lay-hoac-tao). */
  async moKenhTheoCap() {
    const body = {};
    if (this._role === 'BENH_NHAN') {
      const id = document.getElementById('chat-bac-si-select')?.value?.trim();
      if (!id) return Toast.canh('Chua chon bac si', 'Vui long chon bac si');
      body.bac_si_id = id;
    } else if (this._role === 'BAC_SI') {
      const id = document.getElementById('chat-benh-nhan-id')?.value?.trim() || this._benhNhanId;
      if (!id) return Toast.canh('Thieu benh nhan', 'Nhap UUID benh nhan');
      body.benh_nhan_id = id;
      this._benhNhanId = id;
    } else {
      return Toast.loi('Khong ho tro', 'Vai tro khong duoc phep chat');
    }

    const res = await Http.tao('/tro-chuyen/phong-chat/lay-hoac-tao/', body);
    if (!res?.ok) {
      const err = res?.data?.error || res?.data?.detail || JSON.stringify(res?.data || {});
      return Toast.loi('Khong mo duoc kenh chat', err);
    }
    this._phong = res.data;
    this._activeRoom = res.data.id;
    this._capNhatTieuDe();
    await this.taiDanhSachPhong();
    await this.taiTinNhan();
    this._ketNoiWebSocket();
  },

  _capNhatTieuDe() {
    const el = document.getElementById('bn-chat-header');
    if (!el || !this._phong) return;
    let text = '';
    if (this._role === 'BAC_SI') {
      text = this._phong.benh_nhan?.ho_ten || this._phong.ten_phong || 'Benh nhan';
    } else {
      text = this._phong.bac_si?.ho_ten || this._phong.ten_phong || 'Bac si';
    }
    el.textContent = `Dang chat: ${text}`;
  },

  async taiDanhSachPhong() {
    const res = await Http.layDanhSach('/tro-chuyen/phong-chat/?ordering=-ngay_cap_nhat');
    this._rooms = Array.isArray(res?.data) ? res.data : res?.data?.results || [];
    const host = document.getElementById('bn-chat-rooms');
    if (!host) return;
    if (!this._rooms.length) {
      host.innerHTML =
        '<div style="padding:12px;color:#64748b;font-size:13px">Chua co hoi thoai. Dung form ben tren de vao chat.</div>';
      return;
    }
    host.innerHTML = this._rooms
      .map(
        (r) => `
      <button type="button" onclick="PageChatBenhNhan.chonPhong('${r.id}')"
        style="display:block;width:100%;text-align:left;padding:10px;border:0;border-bottom:1px solid #f1f5f9;background:${this._activeRoom === r.id ? '#eff6ff' : '#fff'}">
        <div style="font-weight:700">${this._esc(this._tenHienThiPhong(r))}</div>
        <div style="font-size:12px;color:#64748b">${this._esc(r.tin_nhan_cuoi?.noi_dung || 'Chua co tin nhan')}</div>
      </button>`
      )
      .join('');
  },

  _tenHienThiPhong(r) {
    if (this._role === 'BAC_SI') {
      return r.benh_nhan?.ho_ten || r.ten_phong || r.ma_phong || 'Phong';
    }
    return r.bac_si?.ho_ten || r.ten_phong || r.ma_phong || 'Phong';
  },

  async chonPhong(roomId) {
    this._activeRoom = roomId;
    this._phong = this._rooms.find((r) => String(r.id) === String(roomId)) || null;
    this._capNhatTieuDe();
    await this.taiDanhSachPhong();
    await this.taiTinNhan();
    this._ketNoiWebSocket();
  },

  async taiTinNhan() {
    if (!this._activeRoom) return;
    const res = await Http.layDanhSach(
      `/tro-chuyen/phong-chat/${this._activeRoom}/tin-nhan/?page=1&limit=50`
    );
    const list = res?.data?.data || [];
    UI.render(
      'bn-chat-messages',
      list
        .slice()
        .reverse()
        .map(
          (m) => `
      <div style="margin-bottom:8px;display:flex;justify-content:${this._isMe(m) ? 'flex-end' : 'flex-start'}">
        <div style="max-width:75%;padding:8px 10px;border-radius:10px;background:${this._isMe(m) ? '#dbeafe' : '#fff'};border:1px solid #e2e8f0">
          <div style="font-size:11px;color:#64748b">${this._esc(m.nguoi_gui || '')}</div>
          <div>${this._esc(m.noi_dung || '')}</div>
        </div>
      </div>`
        )
        .join('')
    );
    const box = document.getElementById('bn-chat-messages');
    if (box) box.scrollTop = box.scrollHeight;
  },

  async guiTinNhan() {
    if (!this._activeRoom)
      return Toast.canh('Chua co kenh chat', 'Chon bac si / nhap benh nhan roi bam Vao chat');
    const input = document.getElementById('bn-chat-input');
    const msg = (input?.value || '').trim();
    if (!msg) return;
    const res = await Http.tao(`/tro-chuyen/phong-chat/${this._activeRoom}/gui-tin-nhan/`, {
      noi_dung: msg,
      loai: 'TEXT',
    });
    if (!res?.ok) return Toast.loi('Gui that bai', res?.data?.error || JSON.stringify(res?.data || {}));
    if (input) input.value = '';
    await this.taiTinNhan();
  },

  _ketNoiWebSocket() {
    if (!this._activeRoom || !window.WsManager?.mo) return;
    WsManager.mo(`chat-${this._activeRoom}`, `/ws/chat/${this._activeRoom}/`, {
      onMessage: () => this.taiTinNhan(),
    });
  },

  _isMe(msg) {
    const me = this._userRaw();
    return String(msg.nguoi_gui || '').includes(String(me.ho_ten || ''));
  },
};

window.PageChatBenhNhan = PageChatBenhNhan;
