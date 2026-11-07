const PageDonThuocBenhNhan = {
  _benhNhanId: null,
  _hostElementId: 'benh-nhan-main-content',

  async render(options = {}) {
    this._benhNhanId = options?.benhNhanId || this._benhNhanId;
    this._hostElementId = options?.hostElementId || this._hostElementId;
    UI.render(this._hostElementId, `
      <div class="card">
        <div class="card-header"><div class="card-title">Đơn thuốc của tôi</div></div>
        <div class="card-body" id="bn-dt-list"><div class="page-loading"><div class="spinner"></div></div></div>
      </div>
    `);
    await this.taiDanhSach();
  },

  async taiDanhSach() {
    const res = await Http.layDanhSach('/benh-an/don-thuoc/?ordering=-ngay_tao&page_size=30');
    const list = Array.isArray(res?.data) ? res.data : (res?.data?.results || []);
    if (!list.length) return UI.render('bn-dt-list', '<p class="text-muted">Bạn chưa có đơn thuốc.</p>');
    UI.render('bn-dt-list', `
      <div class="table-wrap">
        <table class="table">
          <thead><tr><th>Mã đơn</th><th>Ngày tạo</th><th>Tổng tiền</th><th>Trạng thái</th><th>Thanh toán</th></tr></thead>
          <tbody>
            ${list.map(d => `
              <tr>
                <td>${this._esc(d.ma_don || '—')}</td>
                <td>${UI.formatNgay(d.ngay_tao)}</td>
                <td>${UI.formatTien(d.tong_tien || 0)}</td>
                <td>${UI.badge(d.trang_thai_display || d.trang_thai || '—')}</td>
                <td>${d.da_thanh_toan ? 'Đã thanh toán' : 'Chưa thanh toán'}</td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      </div>
    `);
  },

  _esc(s) { return String(s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#39;'); }
};

window.PageDonThuocBenhNhan = PageDonThuocBenhNhan;
