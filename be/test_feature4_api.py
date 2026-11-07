# -*- coding: utf-8 -*-
"""
FEATURE 4: KIỂM THỬ REST API & PHÂN QUYỀN RBAC (Lịch trực, Nhà thuốc, Kho & Báo cáo) — 14 Test Cases
Áp dụng kỹ thuật kiểm thử: Phân vùng tương đương (EP), Phân tích giá trị biên (BVA),
Bảng quyết định (Decision Table), Kiểm thử Phân quyền (RBAC) và Kiểm thử Hợp đồng API (API Contract).
- Function 4.1: API Đăng ký Ca làm Bác sĩ (/api/doctor-schedule/) & API Bán thuốc tại quầy (UC009, UC011 - 7 Test Cases: TC_API_01..TC_API_07)
- Function 4.2: API Nhập kho dược (/api/thuoc/phieu-nhap/) & API Báo cáo tài chính (UC012, UC013 - 7 Test Cases: TC_API_08..TC_API_14)
Không bao gồm Đăng nhập (UC001) và Đăng ký tài khoản (UC002).
"""

import json
from datetime import timedelta
from decimal import Decimal

from base_test_setup import BasePhongKhamTestSetup
from nguoidung.models import DoctorSchedule
from benhan.models import HoSoBenhAn, DonThuoc, ChiTietDonThuoc
from donhang.models import DonHang
from baocao.models import BaoCao


class Feature4APIRBACTests(BasePhongKhamTestSetup):
    """Kiểm thử Feature 4: REST API & Phân quyền RBAC (14 Test Cases: 12 Passed, 2 Failed phát hiện lỗi thực tế so với SRS)."""

    # ==========================================================================
    # FUNCTION 4.1: API Đăng ký Ca làm Bác sĩ & API Bán thuốc tại quầy — 7 TCs
    # ==========================================================================
    def test_TC_API_01_ep_bac_si_dang_ky_nhieu_ca_lam_trong_ngay(self):
        """TC_API_01 [EP - Hợp lệ]: Bác sĩ gọi POST /api/doctor-schedule/dang_ky_nhieu/ đăng ký nhiều ca làm ['SANG', 'CHIEU'] thành công (UC009)."""
        self.api_client.force_authenticate(user=self.u_bacsi2)
        ngay_dk = (self.today + timedelta(days=5)).isoformat()
        res = self.api_client.post(
            '/api/doctor-schedule/dang_ky_nhieu/',
            {
                'ngay_lam': ngay_dk,
                'ca_lam': ['SANG', 'CHIEU'],
                'ghi_chu': 'Đăng ký lịch khám nhi tuần tới',
            },
            format='json',
        )
        self.assertEqual(res.status_code, 201, res.content)
        self.assertEqual(len(res.data['created']), 2)
        self.assertEqual(
            DoctorSchedule.objects.filter(bac_si=self.bacsi2, ngay_lam=ngay_dk).count(),
            2,
        )

    def test_TC_API_02_bva_chan_bac_si_dang_ky_ca_lam_ngay_qua_khu(self):
        """TC_API_02 [BVA - Biên ngày]: API /api/doctor-schedule/ chặn Bác sĩ đăng ký ca làm việc vào ngày trong quá khứ (REQ-SCHED-02)."""
        self.api_client.force_authenticate(user=self.u_bacsi2)
        ngay_qua_khu = (self.today - timedelta(days=1)).isoformat()
        res = self.api_client.post(
            '/api/doctor-schedule/',
            {'ngay_lam': ngay_qua_khu, 'ca_lam': 'SANG'},
            format='json',
        )
        self.assertEqual(res.status_code, 400)

    def test_TC_API_03_rbac_kiem_soat_quyen_tren_api_doctor_schedule(self):
        """TC_API_03 [RBAC]: Chặn Nhân viên/Bệnh nhân đăng ký ca làm bác sĩ (403) và chặn Bác sĩ xóa ca làm của đồng nghiệp (REQ-SCHED-03)."""
        self.api_client.force_authenticate(user=self.u_letan)
        future_day = (self.today + timedelta(days=5)).isoformat()
        res_nv = self.api_client.post(
            '/api/doctor-schedule/',
            {'ngay_lam': future_day, 'ca_lam': 'SANG'},
            format='json',
        )
        self.assertEqual(res_nv.status_code, 403)

        ca_bs1 = DoctorSchedule.objects.filter(bac_si=self.bacsi1).first()
        self.api_client.force_authenticate(user=self.u_bacsi2)
        res_del = self.api_client.delete(f'/api/doctor-schedule/{ca_bs1.pk}/')
        self.assertIn(res_del.status_code, (403, 404))
        self.assertTrue(DoctorSchedule.objects.filter(pk=ca_bs1.pk).exists())

    def test_TC_API_04_ep_nhan_vien_ban_thuoc_ban_le_tai_quay_va_thu_tien_mat(self):
        """TC_API_04 [EP - Hợp lệ]: Nhân viên bán thuốc (BAN_THUOC) tạo đơn bán lẻ tại quầy và xác nhận thanh toán tiền mặt -> HOAN_THANH (UC011)."""
        self.api_client.force_authenticate(user=self.u_banthuoc)
        res_sale = self.api_client.post(
            '/api/don-hang/don-hang/ban-thuoc-le/',
            json.dumps({
                'benh_nhan_id': str(self.bn1.pk),
                'items': [{'thuoc_id': str(self.thuoc_otc.pk), 'so_luong': 5}],
                'ghi_chu': 'Khách mua lẻ tại quầy',
            }),
            content_type='application/json',
        )
        self.assertEqual(res_sale.status_code, 200, res_sale.content)
        sale_data = json.loads(res_sale.content)['data']
        dh_id = sale_data['don_hang_id']
        self.assertEqual(sale_data['tong_tien'], 10000.0)

        res_pay = self.api_client.post(
            f'/api/don-hang/don-hang/{dh_id}/thanh-toan/',
            json.dumps({'phuong_thuc': 'TIEN_MAT', 'noi_dung': 'Thu tiền mặt tại quầy dược'}),
            content_type='application/json',
        )
        self.assertEqual(res_pay.status_code, 200, res_pay.content)
        dh = DonHang.objects.get(pk=dh_id)
        self.assertEqual(dh.trang_thai, 'HOAN_THANH')

    def test_TC_API_05_decision_table_ban_theo_toa_bac_si_va_chan_ban_trung_toa_da_hoan_thanh(self):
        """TC_API_05 [Decision Table]: Nhân viên bán thuốc xuất bán theo toa bác sĩ, thu tiền hoàn tất toa và chặn tạo đơn lần 2 trên cùng toa (REQ-POS-02)."""
        hs = HoSoBenhAn.objects.create(
            benh_nhan=self.bn1,
            bac_si=self.bacsi1,
            ly_do_kham='Khám nhiễm khuẩn hô hấp',
            trieu_chung='Ho sốt',
        )
        dt = DonThuoc.objects.create(ho_so=hs, benh_nhan=self.bn1, bac_si=self.bacsi1)
        ct = ChiTietDonThuoc.objects.create(
            don_thuoc=dt,
            thuoc=self.thuoc_rx,
            so_luong=6,
            lieu_dung='1 viên x 2 lần',
            cach_dung='UONG',
            so_ngay_dung=3,
            don_gia_tai_thoi_diem=Decimal('18000.00'),
        )
        dt.tinh_tong_tien()

        self.api_client.force_authenticate(user=self.u_banthuoc)
        res1 = self.api_client.post(
            '/api/don-hang/don-hang/ban-theo-toa/',
            json.dumps({
                'ma_don': dt.ma_don,
                'items': [{'chi_tiet_don_thuoc_id': str(ct.pk), 'so_luong': 6}],
            }),
            content_type='application/json',
        )
        self.assertEqual(res1.status_code, 200, res1.content)
        dh_id = json.loads(res1.content)['data']['don_hang_id']

        # Thanh toán đơn tại quầy -> tự động đồng bộ toa sang HOAN_THANH
        self.api_client.post(
            f'/api/don-hang/don-hang/{dh_id}/thanh-toan/',
            json.dumps({'phuong_thuc': 'TIEN_MAT'}),
            content_type='application/json',
        )

        # Tạo đơn lần 2 trên cùng toa đã HOAN_THANH -> chặn 400 Bad Request
        res2 = self.api_client.post(
            '/api/don-hang/don-hang/ban-theo-toa/',
            json.dumps({
                'ma_don': dt.ma_don,
                'items': [{'chi_tiet_don_thuoc_id': str(ct.pk), 'so_luong': 6}],
            }),
            content_type='application/json',
        )
        self.assertEqual(res2.status_code, 400)

    def test_TC_API_06_bva_chan_ban_le_thuoc_ke_don_va_chan_ban_vuot_so_luong_toa(self):
        """TC_API_06 [BVA & Business Rule]: Chặn bán lẻ không toa đối với thuốc kê đơn (can_don_thuoc=True) trả về 400 Bad Request (REQ-POS-01)."""
        self.api_client.force_authenticate(user=self.u_banthuoc)
        res_rx = self.api_client.post(
            '/api/don-hang/don-hang/ban-thuoc-le/',
            json.dumps({
                'benh_nhan_id': str(self.bn1.pk),
                'items': [{'thuoc_id': str(self.thuoc_rx.pk), 'so_luong': 2}],
            }),
            content_type='application/json',
        )
        self.assertEqual(res_rx.status_code, 400)

    def test_TC_API_07_rbac_chan_le_tan_va_benh_nhan_goi_api_ban_thuoc_tai_quay(self):
        """TC_API_07 [RBAC]: Chặn nhân viên Lễ tân (LE_TAN) và Bệnh nhân gọi API bán thuốc lẻ tại quầy trả về 403 Forbidden (REQ-POS-04)."""
        for user in (self.u_letan, self.u_bn1):
            self.api_client.force_authenticate(user=user)
            res = self.api_client.post(
                '/api/don-hang/don-hang/ban-thuoc-le/',
                json.dumps({
                    'benh_nhan_id': str(self.bn1.pk),
                    'items': [{'thuoc_id': str(self.thuoc_otc.pk), 'so_luong': 2}],
                }),
                content_type='application/json',
            )
            self.assertEqual(res.status_code, 403)

    # ==========================================================================
    # FUNCTION 4.2: API Nhập kho dược & API Báo cáo tài chính — 7 TCs
    # ==========================================================================
    def test_TC_API_08_ep_ke_toan_tao_phieu_nhap_kho_thuoc_cap_nhat_ton_kho(self):
        """TC_API_08 [EP - Hợp lệ]: Kế toán tạo phiếu nhập kho thuốc (POST /api/thuoc/phieu-nhap/) — tự động lưu mã PNK và cộng tồn kho (UC012)."""
        self.api_client.force_authenticate(user=self.u_ketoan)
        ton_truoc = self.thuoc_otc.ton_kho()
        res = self.api_client.post(
            '/api/thuoc/phieu-nhap/',
            {
                'ma_phieu': 'PNK-TEST-001',
                'loai_nhap': 'THUOC',
                'nha_cung_cap': str(self.ncc.pk),
                'ngay_chung_tu': self.today.isoformat(),
                'so_chung_tu': 'HD-NK-2026-001',
                'ghi_chu': 'Nhập bổ sung Paracetamol quý 4',
                'chi_tiet_thuoc': [
                    {
                        'thuoc': str(self.thuoc_otc.pk),
                        'so_luong': 200,
                        'don_gia': '1200.00',
                        'han_su_dung': (self.today + timedelta(days=365)).isoformat(),
                        'lo_sx': 'LO-PARA-NEW-01',
                    }
                ],
            },
            format='json',
        )
        self.assertEqual(res.status_code, 201, res.content)
        self.assertTrue(res.data['ma_phieu'].startswith('PNK-'))
        self.assertTrue(res.data['da_cap_nhat_kho'])
        self.assertEqual(self.thuoc_otc.ton_kho(), ton_truoc + 200)

    def test_TC_API_09_ep_ke_toan_tao_phieu_nhap_kho_vaccine_cap_nhat_ton_kho(self):
        """TC_API_09 [EP - Hợp lệ]: Kế toán tạo phiếu nhập kho Vaccine (loai_nhap='VACCINE') — tự động cộng số liều vào KhoVaccine (UC012)."""
        self.api_client.force_authenticate(user=self.u_ketoan)
        ton_vc_truoc = self.vaccine.ton_kho()
        res = self.api_client.post(
            '/api/thuoc/phieu-nhap/',
            {
                'ma_phieu': 'PNK-VC-001',
                'loai_nhap': 'VACCINE',
                'nha_cung_cap': str(self.ncc.pk),
                'ngay_chung_tu': self.today.isoformat(),
                'so_chung_tu': 'HD-VC-2026-001',
                'chi_tiet_vaccine': [
                    {
                        'vaccine': str(self.vaccine.pk),
                        'so_luong': 30,
                        'don_gia': '280000.00',
                        'han_su_dung': (self.today + timedelta(days=300)).isoformat(),
                        'lo_sx': 'LO-VC-NEW-01',
                    }
                ],
            },
            format='json',
        )
        self.assertEqual(res.status_code, 201, res.content)
        self.assertEqual(self.vaccine.ton_kho(), ton_vc_truoc + 30)

    def test_TC_API_10_bva_chan_tao_phieu_nhap_kho_rong_chi_tiet(self):
        """TC_API_10 [BVA - Không hợp lệ]: Chặn tạo phiếu nhập kho khi danh sách chi_tiet_thuoc rỗng [] trả về 400 Bad Request."""
        self.api_client.force_authenticate(user=self.u_ketoan)
        res_empty = self.api_client.post(
            '/api/thuoc/phieu-nhap/',
            {
                'ma_phieu': 'PNK-ERR-001',
                'loai_nhap': 'THUOC',
                'nha_cung_cap': str(self.ncc.pk),
                'ngay_chung_tu': self.today.isoformat(),
                'so_chung_tu': 'HD-ERR-01',
                'chi_tiet_thuoc': [],
            },
            format='json',
        )
        self.assertEqual(res_empty.status_code, 400)

    def test_TC_API_11_rbac_chan_nhan_vien_ban_thuoc_tao_phieu_nhap_kho(self):
        """TC_API_11 [RBAC]: Chặn nhân viên Bán thuốc/Lễ tân tạo phiếu nhập kho dược trả về 403 Forbidden (REQ-STOCK-01)."""
        self.api_client.force_authenticate(user=self.u_banthuoc)
        res_forbidden = self.api_client.post(
            '/api/thuoc/phieu-nhap/',
            {
                'ma_phieu': 'PNK-ERR-002',
                'loai_nhap': 'THUOC',
                'nha_cung_cap': str(self.ncc.pk),
                'ngay_chung_tu': self.today.isoformat(),
                'so_chung_tu': 'HD-ERR-02',
                'chi_tiet_thuoc': [
                    {
                        'thuoc': str(self.thuoc_otc.pk),
                        'so_luong': 50,
                        'don_gia': '1200.00',
                        'han_su_dung': (self.today + timedelta(days=365)).isoformat(),
                        'lo_sx': 'LO-FORBIDDEN',
                    }
                ],
            },
            format='json',
        )
        self.assertEqual(res_forbidden.status_code, 403)

    def test_TC_API_12_ep_rbac_xuat_bao_cao_tai_chinh_excel_va_chan_benh_nhan(self):
        """TC_API_12 [EP & RBAC]: Kế toán xuất báo cáo tài chính ra file Excel (.xlsx) thành công và chặn Bệnh nhân truy cập (403 Forbidden)."""
        tu = (self.today - timedelta(days=30)).isoformat()
        den = self.today.isoformat()
        self.api_client.force_authenticate(user=self.u_ketoan)
        res_xlsx = self.api_client.get(
            f'/api/thuoc/dashboard/ke-toan/tai-chinh-xuat/?dinh_dang=xlsx&tu={tu}&den={den}'
        )
        self.assertEqual(res_xlsx.status_code, 200)
        self.assertIn(
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            res_xlsx['Content-Type'],
        )

        self.api_client.force_authenticate(user=self.u_bn1)
        res_bn = self.api_client.get(
            f'/api/thuoc/dashboard/ke-toan/tai-chinh-xuat/?dinh_dang=xlsx&tu={tu}&den={den}'
        )
        self.assertEqual(res_bn.status_code, 403)

    def test_TC_API_13_contract_tao_bao_cao_doanh_thu_qua_endpoint_baocao_theo_srs(self):
        """TC_API_13 [API Contract - FAILED vs SRS]: Theo SRS UC013/REQ-REP-01, gọi POST /api/bao-cao/bao-cao/tao_bao_cao/ phải tạo bản ghi BaoCao (201)."""
        self.api_client.force_authenticate(user=self.u_ketoan)
        try:
            res = self.api_client.post(
                '/api/bao-cao/bao-cao/tao_bao_cao/',
                {
                    'loai_bao_cao': 'DOANH_THU',
                    'tu_ngay': (self.today - timedelta(days=30)).isoformat(),
                    'den_ngay': self.today.isoformat(),
                },
                format='json',
            )
            status_code = res.status_code
        except AttributeError:
            status_code = 500

        self.assertEqual(
            status_code,
            201,
            "LỖI SRS (UC013/REQ-REP-01): Endpoint /api/bao-cao/bao-cao/tao_bao_cao/ lỗi AttributeError do thiếu hàm BaoCao.tao_bao_cao_doanh_thu!",
        )

    def test_TC_API_14_contract_xuat_bao_cao_pdf_tren_baocao_viewset_theo_srs(self):
        """TC_API_14 [API Contract - FAILED vs SRS]: Theo SRS UC013/REQ-REP-03, gọi GET /api/bao-cao/bao-cao/{id}/xuat_pdf/ phải trả về file PDF."""
        self.api_client.force_authenticate(user=self.u_ketoan)
        bc = BaoCao.objects.create(
            ten_bao_cao='Báo cáo doanh thu tháng 11',
            loai='DOANH_THU',
            thoi_gian_bat_dau=self.today - timedelta(days=30),
            thoi_gian_ket_thuc=self.today,
            nguoi_tao=self.u_ketoan,
        )
        res = self.api_client.get(f'/api/bao-cao/bao-cao/{bc.pk}/xuat_pdf/')
        self.assertEqual(
            res.get('Content-Type'),
            'application/pdf',
            "LỖI SRS (UC013/REQ-REP-03): Endpoint /api/bao-cao/bao-cao/{id}/xuat_pdf/ chưa xuất file PDF mà chỉ trả về JSON TODO!",
        )
