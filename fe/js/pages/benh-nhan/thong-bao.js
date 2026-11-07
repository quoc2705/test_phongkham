/** Alias — bệnh nhân dùng ThongBaoBell chung */
const PageThongBaoBenhNhan = {
  init() {
    ThongBaoBell.init({ badgeId: 'bn-noti-badge' });
  },
  togglePopup(e) {
    ThongBaoBell.togglePopup(e);
  },
  taiThongBao(showToast) {
    return ThongBaoBell.taiThongBao(showToast);
  },
  danhDau(id) {
    return ThongBaoBell.danhDau(id);
  },
  danhDauTatCa() {
    return ThongBaoBell.danhDauTatCa();
  },
};

window.PageThongBaoBenhNhan = PageThongBaoBenhNhan;
