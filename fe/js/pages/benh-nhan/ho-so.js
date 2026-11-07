const PageHoSoBenhNhan = {
  _benhNhanId: null,
  _hostElementId: 'benh-nhan-main-content',

  async render(options = {}) {
    this._benhNhanId = options?.benhNhanId || this._benhNhanId;
    this._hostElementId = options?.hostElementId || this._hostElementId;

    const meRes = await Http.layDanhSach('/users/me/');
    const me = meRes?.data || {};
    const bn = me?.benh_nhan || {};

    UI.render(this._hostElementId, `
      <div class="card">
        <div class="card-header"><div class="card-title">Hồ sơ cá nhân</div></div>
        <div class="card-body">
          <div class="grid-2">
            <div>
              <div class="form-group"><label>Họ tên *</label><input id="bn-hs-ho-ten" class="form-control" value="${this._esc(me.ho_ten || '')}"></div>
              <div class="form-group"><label>Email</label><input id="bn-hs-email" class="form-control" value="${this._esc(me.email || '')}"></div>
              <div class="form-group"><label>Số điện thoại *</label><input id="bn-hs-sdt" class="form-control" value="${this._esc(me.so_dien_thoai || '')}"></div>
              <div class="form-group"><label>Địa chỉ</label><textarea id="bn-hs-dia-chi" class="form-control" rows="2">${this._esc(me.dia_chi || '')}</textarea></div>
              <div class="form-row">
                <div class="form-group"><label>Ngày sinh</label><input type="date" id="bn-hs-ngay-sinh" class="form-control" value="${(me.ngay_sinh || '').slice(0, 10)}"></div>
                <div class="form-group">
                  <label>Giới tính</label>
                  <select id="bn-hs-gioi-tinh" class="form-control">
                    <option value="">-- Chọn --</option>
                    <option value="NAM" ${(me.gioi_tinh || '') === 'NAM' ? 'selected' : ''}>Nam</option>
                    <option value="NU" ${(me.gioi_tinh || '') === 'NU' ? 'selected' : ''}>Nữ</option>
                    <option value="KHAC" ${(me.gioi_tinh || '') === 'KHAC' ? 'selected' : ''}>Khác</option>
                  </select>
                </div>
              </div>
            </div>
            <div>
              <div class="form-group"><label>Mã bệnh nhân</label><input class="form-control" value="${this._esc(bn.ma_benh_nhan || '')}" readonly></div>
              <div class="form-group"><label>Số bảo hiểm</label><input id="bn-hs-bh" class="form-control" value="${this._esc(bn.so_bao_hiem || '')}"></div>
              <div class="form-group"><label>Họ tên người thân</label><input id="bn-hs-nt-ten" class="form-control" value="${this._esc(bn.ho_ten_nguoi_than || '')}"></div>
              <div class="form-group"><label>Quan hệ người thân</label><input id="bn-hs-nt-qh" class="form-control" value="${this._esc(bn.quan_he_nguoi_than || '')}"></div>
              <div class="form-group"><label>SĐT người thân</label><input id="bn-hs-nt-sdt" class="form-control" value="${this._esc(bn.sdt_nguoi_than || '')}"></div>
            </div>
          </div>
          <div style="display:flex;justify-content:flex-end;margin-top:10px">
            <button class="btn btn-primary" onclick="PageHoSoBenhNhan.luu()"><i class="fas fa-save"></i> Lưu hồ sơ</button>
          </div>
        </div>
      </div>
    `);
  },

  async luu() {
    const nguoi_dung = {
      ho_ten: (document.getElementById('bn-hs-ho-ten')?.value || '').trim(),
      email: (document.getElementById('bn-hs-email')?.value || '').trim(),
      so_dien_thoai: (document.getElementById('bn-hs-sdt')?.value || '').trim(),
      dia_chi: (document.getElementById('bn-hs-dia-chi')?.value || '').trim(),
      ngay_sinh: document.getElementById('bn-hs-ngay-sinh')?.value || null,
      gioi_tinh: document.getElementById('bn-hs-gioi-tinh')?.value || ''
    };
    const payload = {
      nguoi_dung,
      so_bao_hiem: (document.getElementById('bn-hs-bh')?.value || '').trim(),
      ho_ten_nguoi_than: (document.getElementById('bn-hs-nt-ten')?.value || '').trim(),
      quan_he_nguoi_than: (document.getElementById('bn-hs-nt-qh')?.value || '').trim(),
      sdt_nguoi_than: (document.getElementById('bn-hs-nt-sdt')?.value || '').trim()
    };
    if (!nguoi_dung.ho_ten || !nguoi_dung.so_dien_thoai) {
      return Toast.loi('Thiếu thông tin', 'Họ tên và số điện thoại là bắt buộc');
    }
    const res = await Http.suaCuc('/benh-nhan/cap_nhat_ho_so_cua_toi/', payload);
    if (!res?.ok) return Toast.loi('Cập nhật thất bại', (res?.data?.error || 'Vui lòng kiểm tra dữ liệu'));
    Toast.ok('Đã cập nhật', 'Hồ sơ cá nhân đã được lưu');
    await this.render({ hostElementId: this._hostElementId, benhNhanId: this._benhNhanId });
  },

  _esc(s) { return String(s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#39;'); }
};

window.PageHoSoBenhNhan = PageHoSoBenhNhan;
