const PageLichHenBenhNhan = {
  _benhNhanId: null,
  _hostElementId: 'benh-nhan-main-content',
  _vaccineList: [],

  async render(options = {}) {
    this._benhNhanId = options?.benhNhanId || this._benhNhanId;
    this._hostElementId = options?.hostElementId || this._hostElementId;
    await this._renderLayout();
    await this.taiDanhSach();
  },

  async _renderLayout() {
    UI.render(this._hostElementId, `
      <div class="grid-2">
        <div class="card">
          <div class="card-header"><div class="card-title">Đặt lịch khám/tiêm</div></div>
          <div class="card-body">
            <div class="form-row">
              <div class="form-group">
                <label>Loại lịch *</label>
                <select id="bn-lh-loai" class="form-control">
                  <option value="KHAM_BENH">Khám bệnh</option>
                  <option value="TIEM_CHUNG">Tiêm chủng</option>
                </select>
              </div>
              <div class="form-group">
                <label>Giờ khám *</label>
                <input type="datetime-local" id="bn-lh-ngay-gio" class="form-control">
                <p class="text-muted small mb-0 mt-1">Bác sĩ sẽ được phòng khám phân công sau khi xác nhận lịch.</p>
              </div>
            </div>
            <div class="form-row" id="bn-lh-vaccine-wrap" style="display:none;">
              <div class="form-group">
                <label>Vaccine sẽ tiêm *</label>
                <select id="bn-lh-vaccine" class="form-control">
                  <option value="">Đang tải danh sách vaccine...</option>
                </select>
              </div>
            </div>
            <div class="form-row">
              <div class="form-group"><label>SĐT liên hệ</label><input id="bn-lh-sdt" class="form-control"></div>
              <div class="form-group"><label>Email liên hệ</label><input id="bn-lh-email" class="form-control"></div>
            </div>
            <div class="form-group"><label>Ghi chú</label><textarea id="bn-lh-ghi-chu" class="form-control" rows="2"></textarea></div>
            <button class="btn btn-primary" onclick="PageLichHenBenhNhan.datLich()"><i class="fas fa-calendar-check"></i> Đặt lịch</button>
          </div>
        </div>
        <div class="card">
          <div class="card-header"><div class="card-title">Lịch sử lịch hẹn</div></div>
          <div class="card-body" id="bn-lh-list"><div class="page-loading"><div class="spinner"></div></div></div>
        </div>
      </div>
    `);

    const me = await Http.layDanhSach('/users/me/');
    document.getElementById('bn-lh-sdt').value = me?.data?.so_dien_thoai || '';
    document.getElementById('bn-lh-email').value = me?.data?.email || '';

    this._setDatetimeMinNow();
    this._ganKiemTraNgayGioHen();
    await this._taiDanhSachVaccine();
    this._ganSuKienLoaiLich();
    this._toggleVaccineInput();
  },

  async datLich() {
    this._setDatetimeMinNow();
    const loaiLich = document.getElementById('bn-lh-loai')?.value;
    const rawDate = document.getElementById('bn-lh-ngay-gio')?.value || '';
    if (!rawDate) return Toast.loi('Thiếu thông tin', 'Vui lòng chọn giờ khám');
    if (new Date(rawDate).getTime() < Date.now()) {
      return Toast.loi('Thời gian không hợp lệ', 'Không thể đặt lịch vào thời gian quá khứ');
    }

    const payload = {
      loai_lich: loaiLich,
      ngay_gio_hen: this._toIso(rawDate),
      so_dien_thoai_lien_he: (document.getElementById('bn-lh-sdt')?.value || '').trim(),
      email_lien_he: (document.getElementById('bn-lh-email')?.value || '').trim(),
      can_nhac_nho: true,
      ghi_chu: (document.getElementById('bn-lh-ghi-chu')?.value || '').trim()
    };

    if (loaiLich === 'TIEM_CHUNG') {
      const vaccineId = document.getElementById('bn-lh-vaccine')?.value || '';
      if (!vaccineId) return Toast.loi('Thiếu thông tin', 'Vui lòng chọn vaccine sẽ tiêm');
      payload.vaccine = vaccineId;
    }

    const res = await Http.tao('/lich-hen/lich-hen/', payload);
    if (!res?.ok) return Toast.loi('Đặt lịch thất bại', this._extractError(res));
    Toast.ok('Đặt lịch thành công', 'Lịch hẹn của bạn đã được tạo');
    await this.taiDanhSach();
  },

  async taiDanhSach() {
    const res = await Http.layDanhSach('/lich-hen/lich-hen/?ordering=-ngay_tao&page_size=20');
    const list = Array.isArray(res?.data) ? res.data : (res?.data?.results || []);
    if (!list.length) return UI.render('bn-lh-list', '<p class="text-muted">Bạn chưa có lịch hẹn.</p>');
    UI.render('bn-lh-list', `
      <div class="table-wrap"><table class="table">
        <thead><tr><th>Mã lịch</th><th>Loại</th><th>Ngày giờ</th><th>Trạng thái</th><th></th></tr></thead>
        <tbody>
          ${list.map(i => `
            <tr>
              <td>${this._esc(i.ma_lich_hen || '—')}</td>
              <td>${this._esc(i.loai_lich_display || i.loai_lich || '—')}</td>
              <td>${UI.formatNgay(i.ngay_gio_hen)}</td>
              <td>${UI.badge(i.trang_thai_display || i.trang_thai || '')}</td>
              <td>${['DA_DAT', 'DA_XAC_NHAN'].includes(i.trang_thai) ? `<button class="btn btn-danger btn-sm" onclick="PageLichHenBenhNhan.huy('${i.id}')">Hủy</button>` : ''}</td>
            </tr>
          `).join('')}
        </tbody>
      </table></div>
    `);
  },

  async huy(id) {
    const lyDo = prompt('Nhập lý do hủy lịch (tuỳ chọn):') || '';
    const res = await Http.tao(`/lich-hen/lich-hen/${id}/huy/`, { ly_do: lyDo });
    if (!res?.ok) return Toast.loi('Hủy lịch thất bại', res?.data?.error || 'Có lỗi xảy ra');
    Toast.ok('Đã hủy lịch', 'Lịch hẹn đã được hủy');
    await this.taiDanhSach();
  },

  _ganSuKienLoaiLich() {
    const loaiEl = document.getElementById('bn-lh-loai');
    if (!loaiEl) return;
    loaiEl.onchange = () => this._toggleVaccineInput();
  },

  _toggleVaccineInput() {
    const loai = document.getElementById('bn-lh-loai')?.value;
    const wrap = document.getElementById('bn-lh-vaccine-wrap');
    if (!wrap) return;
    wrap.style.display = loai === 'TIEM_CHUNG' ? '' : 'none';
  },

  async _taiDanhSachVaccine() {
    const select = document.getElementById('bn-lh-vaccine');
    if (!select) return;

    const res = await Http.layDanhSach('/thuoc/vaccine/?trang_thai=true&page_size=200');
    if (!res?.ok) {
      this._vaccineList = [];
      select.innerHTML = '<option value="">Không tải được danh sách vaccine</option>';
      return;
    }

    const list = Array.isArray(res?.data) ? res.data : (res?.data?.results || []);
    this._vaccineList = list;
    if (!list.length) {
      select.innerHTML = '<option value="">Hiện chưa có vaccine khả dụng</option>';
      return;
    }

    select.innerHTML = `
      <option value="">Chọn vaccine</option>
      ${list.map(v => `<option value="${this._esc(v.id)}">${this._esc(v.ten_vaccine || v.ma_vaccine || 'Vaccine')}</option>`).join('')}
    `;
  },

  _setDatetimeMinNow() {
    const el = document.getElementById('bn-lh-ngay-gio');
    if (!el) return;
    el.min = (window.UIEnhance && UIEnhance.datetimeLocalMinNow)
      ? UIEnhance.datetimeLocalMinNow()
      : this._datetimeLocalMinFallback();
    if (el.value && new Date(el.value).getTime() < Date.now()) {
      el.value = '';
    }
  },

  _datetimeLocalMinFallback() {
    const now = new Date();
    now.setSeconds(0, 0);
    return new Date(now.getTime() - now.getTimezoneOffset() * 60000).toISOString().slice(0, 16);
  },

  _ganKiemTraNgayGioHen() {
    const el = document.getElementById('bn-lh-ngay-gio');
    if (!el || el.dataset.minBound) return;
    el.dataset.minBound = '1';
    el.addEventListener('change', () => this._kiemTraNgayGioHen());
    el.addEventListener('focus', () => this._setDatetimeMinNow());
  },

  _kiemTraNgayGioHen() {
    const el = document.getElementById('bn-lh-ngay-gio');
    if (!el || !el.value) return;
    if (new Date(el.value).getTime() < Date.now()) {
      this._setDatetimeMinNow();
      Toast.loi('Thời gian không hợp lệ', 'Không thể chọn thời gian trong quá khứ');
    }
  },

  _extractError(res) {
    const d = res?.data;
    if (!d) return 'Vui lòng kiểm tra dữ liệu';
    if (typeof d === 'string') return d;
    if (d.error) return d.error;
    const firstKey = Object.keys(d)[0];
    const val = firstKey ? d[firstKey] : null;
    if (Array.isArray(val)) return String(val[0] || 'Vui lòng kiểm tra dữ liệu');
    if (typeof val === 'string') return val;
    return 'Vui lòng kiểm tra dữ liệu';
  },

  _toIso(v) { return v ? new Date(v).toISOString() : ''; },
  _esc(s) { return String(s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#39;'); }
};

window.PageLichHenBenhNhan = PageLichHenBenhNhan;
