/**
 * Trang Chat — Realtime qua WebSocket (TCP/IP)
 */
const PageChat = {
  _phienHienTai: null,
  _danhSachPhien: [],

  async render() {
    UI.render('main-content', `
      <div style="background:white;border-radius:var(--radius-lg);box-shadow:var(--shadow-sm);
                  display:grid;grid-template-columns:300px 1fr;height:calc(100vh - 130px);overflow:hidden">

        <!-- DANH SÁCH LIÊN LẠC -->
        <div style="border-right:1px solid var(--c-border);display:flex;flex-direction:column">
          <div style="padding:16px 18px;border-bottom:1px solid var(--c-border)">
            <h3 style="color:var(--c-navy);margin-bottom:10px">💬 Tin nhắn</h3>
            <div style="position:relative">
              <i class="fas fa-search" style="position:absolute;left:10px;top:50%;transform:translateY(-50%);color:var(--c-placeholder);font-size:12px"></i>
              <input type="text" class="form-control" placeholder="Tìm cuộc trò chuyện..."
                     style="padding-left:30px;font-size:13px" oninput="PageChat.timKiem(this.value)">
            </div>
          </div>
          <div id="ds-lien-lac" style="flex:1;overflow-y:auto">
            <div class="page-loading"><div class="spinner"></div></div>
          </div>

          <!-- Tìm theo mã bệnh nhân (NV) -->
          <div id="tim-ma-bn" class="d-none" style="padding:12px;border-top:1px solid var(--c-border)">
            <div style="font-size:11px;font-weight:700;color:var(--c-muted);margin-bottom:6px;letter-spacing:.5px">
              TÌM THEO MÃ BỆNH NHÂN
            </div>
            <div style="display:flex;gap:6px">
              <input type="text" id="input-ma-bn" class="form-control" placeholder="VD: BN00001" style="font-size:13px">
              <button class="btn btn-primary btn-sm" onclick="PageChat.timBenhNhan()">Tìm</button>
            </div>
          </div>
        </div>

        <!-- VÙNG CHAT -->
        <div id="vung-chat" style="display:flex;flex-direction:column">
          <div style="display:flex;align-items:center;justify-content:center;height:100%;flex-direction:column;gap:12px;color:var(--c-muted)">
            <div style="font-size:56px;opacity:.15">💬</div>
            <h3 style="color:var(--c-muted)">Chọn cuộc trò chuyện</h3>
            <p style="font-size:13px">Chọn người cần chat từ danh sách bên trái</p>
          </div>
        </div>
      </div>

      <style>
        .lien-lac-item {
          display: flex; align-items: center; gap: 10px;
          padding: 13px 16px; cursor: pointer;
          border-bottom: 1px solid var(--c-border);
          transition: background var(--t-fast);
        }
        .lien-lac-item:hover, .lien-lac-item.active { background: var(--c-sky); }
        .lien-lac-unread .lien-lac-msg { font-weight: 700; color: var(--c-text); }
        .unread-badge {
          width: 18px; height: 18px;
          background: var(--c-navy-light); color: white;
          border-radius: 50%; font-size: 10px; font-weight: 700;
          display: flex; align-items: center; justify-content: center;
          flex-shrink: 0; margin-left: auto;
        }
        .ws-status { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
        .ws-online  { background: var(--c-success); }
        .ws-offline { background: var(--c-muted); }
      </style>
    `);

    const { vaiTro } = Auth.layThongTin();
    if (vaiTro === 'nhan_vien') {
      UI.hien('tim-ma-bn');
    }

    await this._loadDanhSachPhien();
  },

  async _loadDanhSachPhien() {
    const { data } = await Http.layDanhSach('/chat/phien/?page_size=30');
    this._danhSachPhien = data?.results || [];
    this._renderDanhSach(this._danhSachPhien);
  },

  _renderDanhSach(list) {
    if (!list || list.length === 0) {
      UI.render('ds-lien-lac', `
        <div class="page-empty" style="padding:32px 16px">
          <div style="font-size:32px;margin-bottom:8px">📭</div>
          <p class="text-muted" style="font-size:13px">Chưa có cuộc trò chuyện nào</p>
        </div>
      `);
      return;
    }

    UI.render('ds-lien-lac', list.map(p => `
      <div class="lien-lac-item ${p.chua_doc > 0 ? 'lien-lac-unread' : ''} ${this._phienHienTai === p.id ? 'active' : ''}"
           id="lien-lac-${p.id}" onclick="PageChat.moPhien(${p.id}, '${(p.ten_nguoi_lien_he || p.ten || '').replace(/'/g, "\\'")}', '${(p.vai_tro_nguoi_lien_he || '').replace(/'/g, "\\'")}')">
        <div class="avatar avatar-md" style="background:linear-gradient(135deg,var(--c-navy-mid),var(--c-navy-light))">
          ${UI.kyTuDau(p.ten_nguoi_lien_he || p.ten || '?')}
        </div>
        <div style="flex:1;min-width:0">
          <div style="font-size:13px;font-weight:700;color:var(--c-text)">${p.ten_nguoi_lien_he || p.ten || '—'}</div>
          <div class="lien-lac-msg" style="font-size:12px;color:var(--c-muted);white-space:nowrap;overflow:hidden;text-overflow:ellipsis">
            ${p.tin_nhan_cuoi || 'Bắt đầu trò chuyện'}
          </div>
        </div>
        <div style="text-align:right;flex-shrink:0">
          <div style="font-size:10px;color:var(--c-muted)">${p.thoi_gian_cuoi || ''}</div>
          ${p.chua_doc > 0 ? `<span class="unread-badge">${p.chua_doc}</span>` : ''}
        </div>
      </div>
    `).join(''));
  },

  timKiem(tuKhoa) {
    const loc = this._danhSachPhien.filter(p =>
      (p.ten_nguoi_lien_he || p.ten || '').toLowerCase().includes(tuKhoa.toLowerCase())
    );
    this._renderDanhSach(loc);
  },

  async timBenhNhan() {
    const ma = document.getElementById('input-ma-bn').value.trim();
    if (!ma) return;
    const { data } = await Http.layDanhSach(`/nguoi-dung/benh-nhan/?ma=${ma}`);
    const list = data?.results || [];
    if (list.length === 0) {
      Toast.canh('Không tìm thấy', `Không có bệnh nhân với mã ${ma}`);
      return;
    }
    const bn = list[0];
    const hs = bn.ho_so_benh_nhan;
    this.moPhienMoi(bn.id, hs?.ho_ten || bn.ten_tai_khoan, `Bệnh nhân ${hs?.ma_benh_nhan || ''}`);
  },

  async moPhienMoi(nguoiDungId, ten, vaiTro) {
    const { ok, data } = await Http.tao('/chat/phien/', { nguoi_dung_2: nguoiDungId });
    if (ok) {
      this.moPhien(data.id, ten, vaiTro);
      await this._loadDanhSachPhien();
    }
  },

  moPhien(phienId, ten, vaiTro) {
    this._phienHienTai = phienId;

    // Active trong danh sách
    document.querySelectorAll('.lien-lac-item').forEach(el => el.classList.remove('active'));
    const activeEl = document.getElementById(`lien-lac-${phienId}`);
    if (activeEl) activeEl.classList.add('active');

    // Đóng WS cũ nếu có
    WsManager.dong('chat');

    // Render khung chat
    const vungChat = document.getElementById('vung-chat');
    if (vungChat) {
      vungChat.innerHTML = `
        <div style="padding:14px 18px;border-bottom:1px solid var(--c-border);
                    display:flex;align-items:center;gap:10px">
          <div class="avatar avatar-md">${UI.kyTuDau(ten)}</div>
          <div style="flex:1">
            <div style="font-weight:700;font-size:14px;color:var(--c-navy)">${ten}</div>
            <div style="font-size:12px;color:var(--c-muted)">${vaiTro}</div>
          </div>
          <div style="display:flex;align-items:center;gap:6px;font-size:12px;color:var(--c-muted)">
            <div class="ws-status ws-offline" id="ws-dot"></div>
            <span id="ws-label">Đang kết nối...</span>
          </div>
        </div>

        <!-- Khu vực tin nhắn -->
        <div id="khu-tin-nhan" style="flex:1;overflow-y:auto;padding:16px;display:flex;flex-direction:column;gap:8px">
          <div class="page-loading"><div class="spinner"></div></div>
        </div>

        <!-- Nhập tin nhắn -->
        <div style="padding:12px 16px;border-top:1px solid var(--c-border);display:flex;gap:10px;align-items:center">
          <input type="text" id="input-tin-nhan" class="form-control"
                 placeholder="Nhập tin nhắn... (Enter để gửi)"
                 onkeydown="if(event.key==='Enter'&&!event.shiftKey){event.preventDefault();PageChat.guiTinNhan()}">
          <button class="btn btn-primary" style="width:42px;height:42px;padding:0;border-radius:50%;flex-shrink:0"
                  onclick="PageChat.guiTinNhan()">
            <i class="fas fa-paper-plane"></i>
          </button>
        </div>
      `;
    }

    // Kết nối WebSocket
    this._ketNoiWS(phienId);
  },

  _ketNoiWS(phienId) {
    const ws = WsManager.mo('chat', `/ws/chat/${phienId}/`, {
      onOpen: () => {
        const wsDot = document.getElementById('ws-dot');
        const wsLabel = document.getElementById('ws-label');
        if (wsDot) wsDot.classList.replace('ws-offline', 'ws-online');
        if (wsLabel) wsLabel.textContent = 'Đang kết nối';
      },
      onMessage: (data) => {
        if (data.loai === 'lich_su') {
          const container = document.getElementById('khu-tin-nhan');
          if (container) container.innerHTML = '';
          if (data.tin_nhan && data.tin_nhan.length) {
            data.tin_nhan.forEach(t => this._hienTinNhan(t));
          }
        } else if (data.loai === 'tin_nhan') {
          this._hienTinNhan(data);
        }
      },
      onClose: () => {
        const wsDot = document.getElementById('ws-dot');
        const wsLabel = document.getElementById('ws-label');
        if (wsDot) wsDot.classList.replace('ws-online', 'ws-offline');
        if (wsLabel) wsLabel.textContent = 'Mất kết nối';
      },
      onError: () => {
        // Fallback: load tin nhắn từ API HTTP
        this._loadLichSuHTTP(phienId);
      },
    });
  },

  async _loadLichSuHTTP(phienId) {
    const { data } = await Http.layDanhSach(`/chat/tin-nhan/?phien=${phienId}&page_size=50`);
    const list = data?.results || [];
    const container = document.getElementById('khu-tin-nhan');
    if (!container) return;
    container.innerHTML = '';

    if (list.length === 0) {
      container.innerHTML = `<p style="text-align:center;color:var(--c-muted);font-size:13px;padding:30px">Bắt đầu cuộc trò chuyện...</p>`;
      return;
    }
    list.forEach(t => this._hienTinNhan(t));
  },

  _hienTinNhan(t) {
    const container = document.getElementById('khu-tin-nhan');
    if (!container) return;

    const div = document.createElement('div');
    div.style.cssText = `display:flex;flex-direction:column;max-width:70%;align-self:${t.la_cua_minh ? 'flex-end' : 'flex-start'};align-items:${t.la_cua_minh ? 'flex-end' : 'flex-start'}`;

    if (!t.la_cua_minh) {
      div.insertAdjacentHTML('beforeend', `
        <div style="font-size:11px;font-weight:700;color:var(--c-muted);margin-bottom:3px">${t.ten_nguoi_gui || ''}</div>
      `);
    }

    div.insertAdjacentHTML('beforeend', `
      <div style="padding:10px 14px;border-radius:16px;font-size:14px;line-height:1.5;
           background:${t.la_cua_minh ? 'var(--c-navy-light)' : 'var(--c-bg)'};
           color:${t.la_cua_minh ? 'white' : 'var(--c-text)'};
           border-bottom-${t.la_cua_minh ? 'right' : 'left'}-radius:4px">
        ${t.noi_dung}
      </div>
      <div style="font-size:11px;color:var(--c-muted);margin-top:3px;padding:0 4px">${t.thoi_gian || ''}</div>
    `);

    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
  },

  guiTinNhan() {
    const input = document.getElementById('input-tin-nhan');
    if (!input) return;
    const noiDung = input.value.trim();
    if (!noiDung) return;

    // Thử gửi qua WS
    const guiWS = WsManager.gui('chat', { noi_dung: noiDung });

    if (!guiWS) {
      // Nếu WS không kết nối, hiện thông báo lỗi
      Toast.loi('Không thể gửi', 'Mất kết nối đến máy chủ');
    }

    input.value = '';
  },
};


// ══════════════════════════════════════════
// THÔNG BÁO
// ══════════════════════════════════════════
const PageThongBao = {
  async render() {
    UI.render('main-content', `
      <div class="card">
        <div class="card-header">
          <div class="card-title"><div class="card-title-icon" style="background:#EFF6FF">🔔</div>Tất cả thông báo</div>
          <button class="btn btn-ghost btn-sm" onclick="PageThongBao.docTatCa()">Đánh dấu đã đọc tất cả</button>
        </div>
        <div id="ds-thong-bao">
          <div class="page-loading"><div class="spinner"></div></div>
        </div>
      </div>
    `);
    await this._load();
  },

  async _load() {
    const { data } = await Http.layDanhSach('/thong-bao/?page_size=30');
    const list = data?.results || [];

    if (!list || list.length === 0) {
      UI.render('ds-thong-bao', `<div class="page-empty"><div class="page-empty-icon">🔕</div><h3>Chưa có thông báo</h3></div>`);
      return;
    }

    const icons = { lich_hen:'📅', don_thuoc:'💊', don_hang:'📦', tiem_chung:'💉', he_thong:'ℹ️' };

    UI.render('ds-thong-bao', list.map(tb => `
      <div style="display:flex;gap:14px;padding:16px 22px;border-bottom:1px solid var(--c-border);
                  ${!tb.da_doc ? 'background:#F8FBFF;' : ''}cursor:pointer"
           onclick="PageThongBao.docThongBao(${tb.id})">
        <div style="width:40px;height:40px;border-radius:10px;
                    background:${!tb.da_doc ? 'var(--c-sky)' : 'var(--c-bg)'};
                    display:flex;align-items:center;justify-content:center;font-size:18px;flex-shrink:0">
          ${icons[tb.loai] || '🔔'}
        </div>
        <div style="flex:1;min-width:0">
          <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:8px">
            <div style="font-weight:${!tb.da_doc ? '700' : '600'};font-size:14px;color:var(--c-text)">${tb.tieu_de}</div>
            <div style="font-size:11px;color:var(--c-muted);flex-shrink:0">${UI.formatNgayGio(tb.ngay_gui)}</div>
          </div>
          <div style="font-size:13px;color:var(--c-muted);margin-top:3px">${tb.noi_dung}</div>
        </div>
        ${!tb.da_doc ? `<div style="width:8px;height:8px;border-radius:50%;background:var(--c-navy-light);flex-shrink:0;margin-top:6px"></div>` : ''}
      </div>
    `).join(''));

    // Xóa dot header
    const notifDot = document.getElementById('notif-dot');
    if (notifDot) notifDot.classList.add('d-none');
  },

  async docThongBao(id) {
    const { ok } = await Http.suaCuc(`/thong-bao/${id}/`, { da_doc: true });
    if (ok) this._load();
  },

  async docTatCa() {
    const { ok } = await Http.goi('/thong-bao/doc-tat-ca/', 'POST');
    if (ok) {
      Toast.ok('Đã đọc tất cả thông báo');
      this._load();
    }
  },
};