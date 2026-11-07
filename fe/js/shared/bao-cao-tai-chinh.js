/**
 * Báo cáo tài chính — lọc xem, xuất file (modal), biểu đồ.
 */
const BaoCaoTaiChinh = {
  _exportSourcePrefix: 'kt',

  NHOM_LABELS: {
    ngay: 'Theo ngày',
    thang: 'Theo tháng',
    nam: 'Theo năm',
    bac_si: 'Theo bác sĩ',
  },

  _esc(s) {
    if (s == null) return '';
    return String(s).replace(/[&<>"']/g, (c) =>
      ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c])
    );
  },

  _fmtMoney(n) {
    return `${Number(n || 0).toLocaleString('vi-VN')} đ`;
  },

  _fmtLocalYMD(d) {
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return `${y}-${m}-${day}`;
  },

  _today() {
    return this._fmtLocalYMD(new Date());
  },

  _firstDayOfMonth() {
    const d = new Date();
    return this._fmtLocalYMD(new Date(d.getFullYear(), d.getMonth(), 1));
  },

  _currentMonth() {
    const d = new Date();
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
  },

  _rowsForNhom(data, nhom) {
    if (!data || typeof data !== 'object') return [];
    if (nhom === 'thang') return data.theo_thang || [];
    if (nhom === 'nam') return data.theo_nam || [];
    if (nhom === 'bac_si') return data.theo_bac_si || [];
    return data.theo_ngay || [];
  },

  _labelKey(nhom) {
    if (nhom === 'thang') return 'thang';
    if (nhom === 'nam') return 'nam';
    if (nhom === 'bac_si') return 'ten_bac_si';
    return 'ngay';
  },

  _chartLabel(row, nhom, data) {
    if (nhom === 'ngay') {
      const ngay = String(row.ngay || '');
      const p = ngay.split('-');
      if (p.length >= 3) return `${p[2]}/${p[1]}`;
      return ngay.slice(-5);
    }
    if (nhom === 'thang') {
      const t = String(row.thang || '');
      const m = parseInt(t.slice(5, 7), 10);
      return Number.isFinite(m) ? `T${m}` : t;
    }
    if (nhom === 'nam') {
      return String(row.nam || row.nam || '');
    }
    return String(row[this._labelKey(nhom)] || row.ngay || '').slice(0, 14);
  },

  _chartSubtitle(nhom, data) {
    const d = data || {};
    if (nhom === 'ngay') {
      return `Các ngày trong tháng ${d.chart_thang || ''}`;
    }
    if (nhom === 'thang') {
      return `12 tháng trong năm ${d.chart_nam || ''}`;
    }
    if (nhom === 'nam') {
      const a = d.chart_nam_tu || '';
      const b = d.chart_nam_den || '';
      return a && b && a !== b ? `So sánh năm ${a} — ${b}` : `Năm ${b || a || ''}`;
    }
    return this.NHOM_LABELS[nhom] || '';
  },

  /** Thanh lọc xem trên màn hình + 1 nút mở hộp thoại xuất. */
  filterBarHtml(prefix, opts = {}) {
    const p = prefix || 'bc';
    const showViewBtn = opts.showViewBtn !== false;
    const tu = opts.tu || this._firstDayOfMonth();
    const den = opts.den || this._today();
    const viewFn = opts.onView || (p === 'kt' ? 'PageKeToanDashboard._fetchTomTat()' : 'AdminDashboard.loadDashboard()');

    return `
      <div class="bc-filter-bar" data-bc-prefix="${p}" style="margin-bottom:12px">
        <div class="form-row form-row--inline" style="flex-wrap:wrap;gap:8px;align-items:flex-end">
          <div class="form-group">
            <label class="form-label">Từ ngày</label>
            <input type="date" id="${p}-tu" class="form-control" value="${tu}"/>
          </div>
          <div class="form-group">
            <label class="form-label">Đến ngày</label>
            <input type="date" id="${p}-den" class="form-control" value="${den}"/>
          </div>
          ${showViewBtn ? `
          <div class="form-group">
            <label class="form-label form-label--spacer" aria-hidden="true">&nbsp;</label>
            <button type="button" class="btn btn-primary" onclick="${viewFn}"><i class="fas fa-search"></i> Xem</button>
          </div>` : ''}
          <div class="form-group">
            <label class="form-label form-label--spacer" aria-hidden="true">&nbsp;</label>
            <button type="button" class="btn btn-outline" onclick="BaoCaoTaiChinh.openExportDialog('${p}')">
              <i class="fas fa-file-export"></i> Xuất báo cáo
            </button>
          </div>
        </div>
      </div>`;
  },

  /** Tham số xem trên màn hình (khoảng ngày). */
  buildQueryParams(prefix) {
    const p = prefix || 'bc';
    const tu = document.getElementById(`${p}-tu`)?.value;
    const den = document.getElementById(`${p}-den`)?.value;
    if (!tu || !den) return { error: 'Chọn từ ngày và đến ngày.' };
    if (tu > den) return { error: 'Từ ngày không được lớn hơn đến ngày.' };
    return { ky_loai: 'khoang', tu, den, nhom: 'ngay' };
  },

  tomTatUrl(prefix) {
    const built = this.buildQueryParams(prefix);
    if (built.error) return built;
    const q = new URLSearchParams(built);
    return { url: `/thuoc/dashboard/ke-toan/tom-tat/?${q.toString()}`, params: built };
  },

  _ensureExportModal() {
    if (document.getElementById('bc-export-overlay')) return;
    const tu = this._firstDayOfMonth();
    const den = this._today();
    const thang = this._currentMonth();
    const nam = String(new Date().getFullYear());
    const html = `
      <div class="modal-overlay" id="bc-export-overlay" role="dialog" aria-modal="true" aria-labelledby="bc-export-title">
        <div class="modal modal-lg">
          <div class="modal-header">
            <div class="modal-title" id="bc-export-title"><i class="fas fa-file-export"></i> Xuất báo cáo tài chính</div>
            <button type="button" class="modal-close" onclick="BaoCaoTaiChinh.closeExportDialog()" aria-label="Đóng">&times;</button>
          </div>
          <div class="modal-body">
            <p class="text-muted small" style="margin-top:0">Biểu mẫu BM-BV-TC-01 — chọn kỳ và định dạng file trước khi tải.</p>
            <div class="form-group">
              <label class="form-label">Loại kỳ báo cáo</label>
              <select id="bc-exp-ky-loai" class="form-control" onchange="BaoCaoTaiChinh.onExportKyLoaiChange()">
                <option value="khoang">Khoảng ngày (từ — đến)</option>
                <option value="ngay">Một ngày cụ thể</option>
                <option value="thang">Một tháng cụ thể</option>
                <option value="nam">Một năm cụ thể</option>
              </select>
            </div>
            <div id="bc-exp-wrap-khoang" class="form-row form-row--inline" style="gap:8px;flex-wrap:wrap">
              <div class="form-group"><label class="form-label">Từ ngày</label><input type="date" id="bc-exp-tu" class="form-control" value="${tu}"/></div>
              <div class="form-group"><label class="form-label">Đến ngày</label><input type="date" id="bc-exp-den" class="form-control" value="${den}"/></div>
            </div>
            <div id="bc-exp-wrap-ngay" class="form-group" style="display:none">
              <label class="form-label">Chọn ngày</label>
              <input type="date" id="bc-exp-ngay" class="form-control" value="${den}"/>
            </div>
            <div id="bc-exp-wrap-thang" class="form-group" style="display:none">
              <label class="form-label">Chọn tháng</label>
              <input type="month" id="bc-exp-thang" class="form-control" value="${thang}"/>
            </div>
            <div id="bc-exp-wrap-nam" class="form-group" style="display:none">
              <label class="form-label">Chọn năm</label>
              <input type="number" id="bc-exp-nam" class="form-control" min="2020" max="2100" value="${nam}" style="width:120px"/>
            </div>
            <div class="form-group">
              <label class="form-label">Nhóm chi tiết trong file</label>
              <select id="bc-exp-nhom" class="form-control">
                <option value="ngay">Theo ngày</option>
                <option value="thang">Theo tháng</option>
                <option value="nam">Theo năm</option>
                <option value="bac_si">Theo bác sĩ</option>
              </select>
            </div>
            <div class="form-group">
              <label class="form-label">Định dạng file</label>
              <select id="bc-exp-dinh-dang" class="form-control">
                <option value="xlsx">Excel (.xlsx)</option>
                <option value="pdf">PDF</option>
                <option value="docx">Word (.docx)</option>
                <option value="csv">CSV</option>
              </select>
            </div>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-outline" onclick="BaoCaoTaiChinh.closeExportDialog()">Hủy</button>
            <button type="button" class="btn btn-primary" id="bc-exp-submit" onclick="BaoCaoTaiChinh.confirmExport()">
              <i class="fas fa-download"></i> Tải xuống
            </button>
          </div>
        </div>
      </div>`;
    document.body.insertAdjacentHTML('beforeend', html);
    const overlay = document.getElementById('bc-export-overlay');
    overlay.addEventListener('click', (e) => {
      if (e.target === overlay) this.closeExportDialog();
    });
  },

  openExportDialog(sourcePrefix) {
    this._exportSourcePrefix = sourcePrefix || 'kt';
    this._ensureExportModal();
    const p = this._exportSourcePrefix;
    const tu = document.getElementById(`${p}-tu`)?.value || this._firstDayOfMonth();
    const den = document.getElementById(`${p}-den`)?.value || this._today();
    const tuEl = document.getElementById('bc-exp-tu');
    const denEl = document.getElementById('bc-exp-den');
    const ngayEl = document.getElementById('bc-exp-ngay');
    if (tuEl) tuEl.value = tu;
    if (denEl) denEl.value = den;
    if (ngayEl) ngayEl.value = den;
    const kyEl = document.getElementById('bc-exp-ky-loai');
    if (kyEl) kyEl.value = 'khoang';
    this.onExportKyLoaiChange();
    const overlay = document.getElementById('bc-export-overlay');
    if (overlay) {
      overlay.classList.add('open');
      document.body.style.overflow = 'hidden';
    }
  },

  closeExportDialog() {
    const overlay = document.getElementById('bc-export-overlay');
    if (overlay) overlay.classList.remove('open');
    document.body.style.overflow = '';
  },

  onExportKyLoaiChange() {
    const ky = document.getElementById('bc-exp-ky-loai')?.value || 'khoang';
    const show = (id, on) => {
      const el = document.getElementById(id);
      if (el) el.style.display = on ? '' : 'none';
    };
    show('bc-exp-wrap-khoang', ky === 'khoang');
    show('bc-exp-wrap-ngay', ky === 'ngay');
    show('bc-exp-wrap-thang', ky === 'thang');
    show('bc-exp-wrap-nam', ky === 'nam');
  },

  buildExportParams() {
    const kyLoai = document.getElementById('bc-exp-ky-loai')?.value || 'khoang';
    const nhom = document.getElementById('bc-exp-nhom')?.value || 'ngay';
    const qs = { ky_loai: kyLoai, nhom };

    if (kyLoai === 'ngay') {
      const ngay = document.getElementById('bc-exp-ngay')?.value;
      if (!ngay) return { error: 'Chọn ngày cụ thể.' };
      qs.ngay = ngay;
      qs.tu = ngay;
      qs.den = ngay;
    } else if (kyLoai === 'thang') {
      const thang = document.getElementById('bc-exp-thang')?.value;
      if (!thang) return { error: 'Chọn tháng cụ thể.' };
      qs.thang = thang;
      const [y, m] = thang.split('-').map(Number);
      const last = new Date(y, m, 0).getDate();
      qs.tu = `${y}-${String(m).padStart(2, '0')}-01`;
      qs.den = `${y}-${String(m).padStart(2, '0')}-${String(last).padStart(2, '0')}`;
    } else if (kyLoai === 'nam') {
      const nam = document.getElementById('bc-exp-nam')?.value;
      if (!nam) return { error: 'Chọn năm cụ thể.' };
      qs.nam = String(nam);
      qs.tu = `${nam}-01-01`;
      qs.den = `${nam}-12-31`;
    } else {
      const tu = document.getElementById('bc-exp-tu')?.value;
      const den = document.getElementById('bc-exp-den')?.value;
      if (!tu || !den) return { error: 'Chọn từ ngày và đến ngày.' };
      if (tu > den) return { error: 'Từ ngày không được lớn hơn đến ngày.' };
      qs.tu = tu;
      qs.den = den;
    }
    return qs;
  },

  async confirmExport() {
    const built = this.buildExportParams();
    if (built.error) {
      Toast.hien('Thiếu thông tin', built.error, 'warning');
      return;
    }
    const dinhDang = document.getElementById('bc-exp-dinh-dang')?.value || 'xlsx';
    built.dinh_dang = dinhDang;
    const qs = new URLSearchParams(built);
    const url = `/thuoc/dashboard/ke-toan/tai-chinh-xuat/?${qs.toString()}`;

    const btn = document.getElementById('bc-exp-submit');
    if (btn) {
      btn.disabled = true;
      btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Đang xuất…';
    }

    const ok = await Http.taiFile(url);

    if (btn) {
      btn.disabled = false;
      btn.innerHTML = '<i class="fas fa-download"></i> Tải xuống';
    }

    if (ok) {
      this.closeExportDialog();
      Toast.hien('Thành công', `Đã tải báo cáo ${String(dinhDang).toUpperCase()}`, 'success');
    }
  },

  chartSectionHtml(prefix) {
    const p = prefix || 'bc';
    return `
      <div class="card" style="margin-top:16px">
        <div class="card-header d-flex flex-wrap align-items-center justify-content-between gap-2">
          <strong><i class="fas fa-chart-bar"></i> Biểu đồ doanh thu</strong>
          <div style="display:flex;gap:6px;flex-wrap:wrap">
            <select id="${p}-chart-nhom" class="form-control" style="width:auto;padding:4px 8px;font-size:13px" onchange="BaoCaoTaiChinh.redrawChart('${p}')" title="Theo ngày = từng ngày trong tháng; Theo tháng = 12 tháng/năm; Theo năm = so sánh các năm">
              <option value="ngay">Theo ngày (trong tháng)</option>
              <option value="thang">Theo tháng (12 tháng/năm)</option>
              <option value="nam">Theo năm (so sánh)</option>
            </select>
            <button type="button" class="btn btn-outline btn-sm" onclick="BaoCaoTaiChinh.exportChartPng('${p}')"><i class="fas fa-image"></i> Xuất PNG</button>
          </div>
        </div>
        <div class="card-body">
          <canvas id="${p}-chart-canvas" width="900" height="320" style="max-width:100%;height:auto"></canvas>
        </div>
      </div>`;
  },

  setChartData(prefix, data) {
    const p = prefix || 'bc';
    window.__bcChartData = window.__bcChartData || {};
    window.__bcChartData[p] = data;
    setTimeout(() => this.redrawChart(p), 50);
  },

  redrawChart(prefix) {
    const p = prefix || 'bc';
    const data = (window.__bcChartData || {})[p];
    const canvas = document.getElementById(`${p}-chart-canvas`);
    const nhomEl = document.getElementById(`${p}-chart-nhom`);
    if (!canvas || !data) return;
    const nhom = nhomEl?.value || 'ngay';
    const rows = this._rowsForNhom(data, nhom);
    this._drawBarChart(canvas, rows, nhom, data);
  },

  _drawBarChart(canvas, rows, nhom, data) {
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    const dpr = window.devicePixelRatio || 1;
    const w = canvas.clientWidth || 900;
    const h = 320;
    canvas.width = w * dpr;
    canvas.height = h * dpr;
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.scale(dpr, dpr);
    ctx.clearRect(0, 0, w, h);

    const pad = { l: 48, r: 16, t: 24, b: 56 };
    const chartW = w - pad.l - pad.r;
    const chartH = h - pad.t - pad.b;

    if (!rows.length) {
      ctx.fillStyle = '#64748b';
      ctx.font = '14px sans-serif';
      ctx.fillText('Không có dữ liệu trong kỳ', pad.l, pad.t + 40);
      return;
    }

    const labelKey = this._labelKey(nhom);
    const labels = rows.map((r, i) => {
      if (nhom === 'ngay' && rows.length > 20 && i % 2 === 1) return '';
      return this._chartLabel(r, nhom, data);
    });
    const vals = rows.map((r) => Number(r.tong_doanh_thu || 0));
    const maxV = Math.max(...vals, 1);

    ctx.strokeStyle = '#e2e8f0';
    for (let i = 0; i <= 4; i++) {
      const y = pad.t + (chartH * i) / 4;
      ctx.beginPath();
      ctx.moveTo(pad.l, y);
      ctx.lineTo(pad.l + chartW, y);
      ctx.stroke();
      const v = maxV * (1 - i / 4);
      ctx.fillStyle = '#94a3b8';
      ctx.font = '10px sans-serif';
      ctx.textAlign = 'right';
      ctx.fillText(this._fmtMoney(v).replace(' đ', ''), 40, y + 4);
    }

    const barGap = nhom === 'ngay' ? 2 : 8;
    const barW = Math.max(nhom === 'ngay' ? 6 : 12, (chartW - barGap * (rows.length + 1)) / rows.length);
    rows.forEach((r, i) => {
      const v = Number(r.tong_doanh_thu || 0);
      const barH = (v / maxV) * chartH;
      const x = pad.l + barGap + i * (barW + barGap);
      const y = pad.t + chartH - barH;
      ctx.fillStyle = v > 0 ? '#1a365d' : '#cbd5e1';
      ctx.fillRect(x, y, barW, barH);
      if (labels[i]) {
        ctx.fillStyle = '#475569';
        ctx.font = '8px sans-serif';
        ctx.textAlign = 'center';
        ctx.save();
        ctx.translate(x + barW / 2, h - pad.b + 6);
        ctx.rotate(nhom === 'ngay' ? -0.9 : -0.45);
        ctx.fillText(labels[i], 0, 0);
        ctx.restore();
      }
    });

    ctx.fillStyle = '#0f172a';
    ctx.font = 'bold 13px sans-serif';
    ctx.textAlign = 'left';
    ctx.fillText(this._chartSubtitle(nhom, data), pad.l, 16);
  },

  exportChartPng(prefix) {
    const p = prefix || 'bc';
    const canvas = document.getElementById(`${p}-chart-canvas`);
    if (!canvas) return;
    const built = this.buildQueryParams(p);
    const tag = built.tu && built.den ? `${built.tu}_${built.den}` : 'chart';
    const link = document.createElement('a');
    link.download = `bieu-do-doanh-thu_${tag}.png`;
    link.href = canvas.toDataURL('image/png');
    link.click();
    Toast.hien('Thành công', 'Đã tải biểu đồ PNG', 'success');
  },

  detailTableHtml(data, nhom) {
    const rows = this._rowsForNhom(data, nhom);
    if (nhom === 'bac_si') {
      const body = rows.map((r) => `<tr>
        <td>${this._esc(r.ten_bac_si || '—')}</td>
        <td style="text-align:right">${this._fmtMoney(r.doanh_thu_don_hang)}</td>
        <td style="text-align:right">${this._fmtMoney(r.doanh_thu_don_thuoc)}</td>
        <td style="text-align:right">${this._fmtMoney(r.doanh_thu_tiem)}</td>
        <td style="text-align:right;font-weight:600">${this._fmtMoney(r.tong_doanh_thu)}</td>
      </tr>`).join('');
      return `
        <h3 style="font-size:15px;margin:12px 0 8px">Doanh thu theo bác sĩ</h3>
        <div style="overflow:auto;border:1px solid var(--c-border,#e2e8f0);border-radius:8px">
          <table class="data-table" style="width:100%;font-size:13px;min-width:520px">
            <thead><tr><th>Bác sĩ</th><th style="text-align:right">Đơn hàng</th><th style="text-align:right">Toa</th><th style="text-align:right">Tiêm</th><th style="text-align:right">Tổng</th></tr></thead>
            <tbody>${body || '<tr><td colspan="5" class="text-muted">Không có.</td></tr>'}</tbody>
          </table>
        </div>`;
    }
    const labelKey = this._labelKey(nhom);
    const title = this.NHOM_LABELS[nhom] || 'Chi tiết';
    const body = rows.map((r) => `<tr>
        <td>${this._esc(r[labelKey] || r.ngay || '')}</td>
        <td style="text-align:right">${this._fmtMoney(r.doanh_thu_don_hang)}</td>
        <td style="text-align:right">${this._fmtMoney(r.doanh_thu_don_thuoc)}</td>
        <td style="text-align:right">${this._fmtMoney(r.doanh_thu_tiem)}</td>
        <td style="text-align:right;font-weight:600">${this._fmtMoney(r.tong_doanh_thu)}</td>
      </tr>`).join('');
    return `
      <h3 style="font-size:15px;margin:12px 0 8px">Doanh thu ${title.toLowerCase()}</h3>
      <div style="overflow:auto;max-height:280px;border:1px solid var(--c-border,#e2e8f0);border-radius:8px">
        <table class="data-table" style="width:100%;font-size:13px;min-width:520px">
          <thead><tr><th>${title}</th><th style="text-align:right">Đơn hàng</th><th style="text-align:right">Toa</th><th style="text-align:right">Tiêm</th><th style="text-align:right">Tổng</th></tr></thead>
          <tbody>${body || '<tr><td colspan="5" class="text-muted">Không có phát sinh trong kỳ.</td></tr>'}</tbody>
        </table>
      </div>`;
  },
};
