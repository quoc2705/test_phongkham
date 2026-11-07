# -*- coding: utf-8 -*-
"""
FEATURE 2: KIỂM THỬ LUỒNG ỨNG DỤNG NGHIỆP VỤ ĐA VAI TRÒ (App Workflows) — 16 Test Cases
Áp dụng kỹ thuật kiểm thử: Phân vùng tương đương (EP), Phân tích giá trị biên (BVA),
Chuyển đổi trạng thái (State Transition), Tích hợp liên phân hệ (Integration) và Error Guessing.
- Function 2.1: Luồng Khám bệnh, Tạo Hồ sơ bệnh án, Chẩn đoán ICD-10, Kê đơn & Tiêm chủng (UC005..UC008 - 8 Test Cases: TC_APP_01..TC_APP_08)
- Function 2.2: Luồng Mua thuốc Online, Giỏ hàng & Thanh toán VNPay (UC010 - 8 Test Cases: TC_APP_09..TC_APP_16)
Không bao gồm Đăng nhập (UC001) và Đăng ký tài khoản (UC002).
Mỗi Test Case đều định nghĩa tường minh Quy trình thực hiện (Test Case Procedure) và Dữ liệu nhập (du_lieu_nhap) trên màn hình ứng dụng.
"""

import json
from datetime import timedelta
from decimal import Decimal
from django.utils import timezone

from base_test_setup import BasePhongKhamTestSetup
from lichhen.models import LichHen
from donhang.models import GioHang, DonHang, ThanhToan


class Feature2AppWorkflowTests(BasePhongKhamTestSetup):
    """Kiểm thử Feature 2: Luồng Ứng dụng Nghiệp vụ Đa vai trò (16 Test Cases: 13 Passed, 3 Failed phát hiện lỗi thực tế so với SRS)."""

    def _tao_lich_checked_in_cho_bs1(self, ghi_chu='Khám viêm họng cấp'):
        self.api_client.force_authenticate(user=self.u_letan)
        du_lieu_nhap_walkin = {
            'benh_nhan': str(self.bn1.pk),
            'bac_si': str(self.bacsi1.pk),
            'loai_lich': 'KHAM_BENH',
            'ma_phong': 'P101',
            'ten_phong': 'Phòng Khám Nội 1',
            'ghi_chu': ghi_chu,
        }
        res = self.api_client.post('/api/lich-hen/lich-hen/walk_in/', du_lieu_nhap_walkin, format='json')
        return res.data['id']

    # ==========================================================================
    # FUNCTION 2.1: Luồng Khám bệnh, Hồ sơ bệnh án, Chẩn đoán ICD-10 & Kê đơn — 8 TCs
    # ==========================================================================
    def test_TC_APP_01_state_bac_si_mo_ho_so_benh_an_tu_lich_checked_in(self):
        """
        TC_APP_01 [State Transition]: Bác sĩ mở hồ sơ bệnh án từ lịch CHECKED_IN — tự động tạo HoSoBenhAn, gắn LichKham và chuyển sang DANG_KHAM.
        Test Case Procedure:
          1. Lễ tân tiếp nhận Walk-in cho BN_TEST_01 (Lê Văn Bệnh Nhân) vào Phòng P101 của BS. Nguyễn Văn An với ghi chú 'Khám viêm họng cấp'.
          2. Bác sĩ (bacsi1_test / Password@123) đăng nhập ứng dụng -> chọn menu [Hàng chờ hôm nay (đã check-in)].
          3. Chọn bệnh nhân Lê Văn Bệnh Nhân và nhấn nút [Mở hồ sơ khám] kèm dữ liệu khởi tạo phiên khám (du_lieu_nhap).
          4. Kiểm tra hệ thống trả về HTTP 201 Created, tự sinh mã hồ sơ 'HS...', gắn LichKham và chuyển trạng thái lịch sang DANG_KHAM.
        """
        lich_id = self._tao_lich_checked_in_cho_bs1(ghi_chu='Khám viêm họng cấp, sốt 38.5 độ')
        self.api_client.force_authenticate(user=self.u_bacsi1)
        du_lieu_nhap = {
            'lich_hen_id': str(lich_id),
            'phong_kham': 'P101 - Phòng Khám Nội 1',
            'ghi_chu_tiep_nhan': 'Bắt đầu khám lâm sàng cho bệnh nhân Lê Văn Bệnh Nhân',
        }
        res = self.api_client.post(f'/api/lich-hen/lich-hen/{lich_id}/mo_ho_so_benh_an/', du_lieu_nhap, format='json')
        self.assertEqual(res.status_code, 201, res.content)
        self.assertTrue(res.data['tao_moi'])
        self.assertEqual(res.data['lich_hen']['trang_thai'], 'DANG_KHAM')
        self.assertTrue(res.data['ho_so']['ma_hs'].startswith('HS'))

    def test_TC_APP_02_state_chan_mo_ho_so_khi_chua_check_in_hoac_sai_bac_si(self):
        """
        TC_APP_02 [State Transition & RBAC]: Chặn mở hồ sơ khi lịch chưa CHECKED_IN (400) hoặc lịch thuộc bác sĩ khác (403 - REQ-EMR-01).
        Test Case Procedure:
          1. Bệnh nhân đặt lịch hẹn trực tuyến (du_lieu_nhap_dat_lich) đang ở trạng thái 'Chờ xác nhận' (chưa Check-in tại quầy).
          2. Bác sĩ 1 (bacsi1_test) nhấn [Mở hồ sơ khám] trên lịch chưa Check-in với dữ liệu (du_lieu_nhap_mo_hs) -> Kiểm tra bị chặn 400 Bad Request.
          3. Bác sĩ 2 (bacsi2_test) đăng nhập và gửi yêu cầu [Mở hồ sơ khám] trên lịch CHECKED_IN thuộc về Bác sĩ 1 -> Kiểm tra bị chặn 403/404.
        """
        self.api_client.force_authenticate(user=self.u_bn1)
        du_lieu_nhap_dat_lich = {
            'bac_si': str(self.bacsi1.pk),
            'loai_lich': 'KHAM_BENH',
            'ngay_gio_hen': (timezone.now() + timedelta(hours=3)).isoformat(),
            'so_dien_thoai_lien_he': '0901000007',
            'email_lien_he': 'bn1_test@gmail.com',
            'ghi_chu': 'Lịch hẹn chưa đến quầy check-in',
        }
        res_dat = self.api_client.post('/api/lich-hen/lich-hen/', du_lieu_nhap_dat_lich, format='json')
        self.assertEqual(res_dat.status_code, 201)
        lh_chua_ci_id = LichHen.objects.get(ghi_chu=du_lieu_nhap_dat_lich['ghi_chu']).pk

        du_lieu_nhap_mo_hs = {
            'ghi_chu_tiep_nhan': 'Thử mở hồ sơ khi bệnh nhân chưa check-in',
        }
        self.api_client.force_authenticate(user=self.u_bacsi1)
        res_not_ci = self.api_client.post(
            f'/api/lich-hen/lich-hen/{lh_chua_ci_id}/mo_ho_so_benh_an/',
            du_lieu_nhap_mo_hs,
            format='json',
        )
        self.assertEqual(res_not_ci.status_code, 400)

        lich_bs1_id = self._tao_lich_checked_in_cho_bs1()
        self.api_client.force_authenticate(user=self.u_bacsi2)
        res_wrong_bs = self.api_client.post(
            f'/api/lich-hen/lich-hen/{lich_bs1_id}/mo_ho_so_benh_an/',
            {'ghi_chu_tiep_nhan': 'Bác sĩ 2 thử mở hồ sơ bệnh nhân của Bác sĩ 1'},
            format='json',
        )
        self.assertIn(res_wrong_bs.status_code, (403, 404))

    def test_TC_APP_03_ep_bac_si_nhap_chan_doan_icd10_va_kham_lam_sang(self):
        """
        TC_APP_03 [EP - Hợp lệ]: Bác sĩ nhập form triệu chứng, kết quả khám lâm sàng và chẩn đoán mã ICD-10 hợp lệ (REQ-DIAG-01..04).
        Test Case Procedure:
          1. Đăng nhập tài khoản Bác sĩ (bacsi1_test) -> Mở hồ sơ khám của BN_TEST_01 -> Chọn tab [Nhập chẩn đoán].
          2. Nhập dữ liệu vào các trường trên form Chẩn đoán (du_lieu_nhap):
             - Triệu chứng (trieu_chung): 'Đau rát họng, sốt 38.5 độ C, ho khan'
             - Kết quả khám lâm sàng (ket_qua_kham_lam_sang): 'Niêm mạc họng đỏ xung huyết, amidan sưng nhẹ'
             - Mã ICD-10 (ma_icd10): 'J02.9'
             - Tên bệnh (ten_benh): 'Viêm họng cấp, không đặc hiệu'
             - Loại bệnh (loai_benh): 'NGOAI_TRU'
             - Mức độ (muc_do): 'TRUNG_BINH'
             - Mô tả (mo_ta): 'Theo dõi viêm họng cấp do vi khuẩn'
             - Kết luận (ket_luan): 'Điều trị nội khoa kháng sinh và hạ sốt 5 ngày'
          3. Nhấn nút [Lưu chẩn đoán] (POST '/api/benh-an/ho-so-benh-an/{id}/nhap_chan_doan/').
          4. Kiểm tra HTTP 200 OK, lưu đúng mã ICD-10 'J02.9' và cập nhật triệu chứng trên HoSoBenhAn.
        """
        lich_id = self._tao_lich_checked_in_cho_bs1()
        self.api_client.force_authenticate(user=self.u_bacsi1)
        ho_so_id = self.api_client.post(f'/api/lich-hen/lich-hen/{lich_id}/mo_ho_so_benh_an/', {}, format='json').data['ho_so']['id']

        du_lieu_nhap = {
            'trieu_chung': 'Đau rát họng, sốt 38.5 độ C, ho khan',
            'ket_qua_kham_lam_sang': 'Niêm mạc họng đỏ xung huyết, amidan sưng nhẹ',
            'ma_icd10': 'J02.9',
            'ten_benh': 'Viêm họng cấp, không đặc hiệu',
            'loai_benh': 'NGOAI_TRU',
            'muc_do': 'TRUNG_BINH',
            'mo_ta': 'Theo dõi viêm họng cấp do vi khuẩn',
            'ket_luan': 'Điều trị nội khoa kháng sinh và hạ sốt 5 ngày',
        }
        res_cd = self.api_client.post(
            f'/api/benh-an/ho-so-benh-an/{ho_so_id}/nhap_chan_doan/',
            du_lieu_nhap,
            format='json',
        )
        self.assertEqual(res_cd.status_code, 200, res_cd.content)
        self.assertEqual(res_cd.data['ma_icd10'], 'J02.9')
        self.assertEqual(res_cd.data['ho_so']['trieu_chung'], 'Đau rát họng, sốt 38.5 độ C, ho khan')

    def test_TC_APP_04_ep_bac_si_ke_don_thuoc_tu_dong_tinh_tong_tien(self):
        """
        TC_APP_04 [EP - Hợp lệ]: Bác sĩ nhập form Kê đơn thuốc gồm nhiều dòng thuốc — hệ thống tự động tính tổng tiền đơn thuốc (REQ-RX-01..04).
        Test Case Procedure:
          1. Đăng nhập Bác sĩ (bacsi1_test) -> Mở hồ sơ khám của BN_TEST_01 -> Chọn tab [Kê đơn].
          2. Nhập dữ liệu vào form Kê đơn thuốc (du_lieu_nhap):
             - Ghi chú toa thuốc (ghi_chu): 'Uống thuốc đúng giờ sau ăn, tái khám sau 5 ngày'
             - Dòng thuốc 1: Thuốc = Augmentin 625mg (TH_RX_01 - 18.000đ/viên), Số lượng = 10, Liều dùng = '1 viên/lần x 2 lần/ngày', Cách dùng = 'UONG', Thời điểm = 'SAU_AN', Số ngày = 5
             - Dòng thuốc 2: Thuốc = Paracetamol 500mg (TH_OTC_01 - 2.000đ/viên), Số lượng = 10, Liều dùng = '1 viên khi sốt > 38.5 độ', Cách dùng = 'UONG', Thời điểm = 'SAU_AN', Số ngày = 5
          3. Nhấn nút [Lưu đơn] (POST '/api/benh-an/ho-so-benh-an/{id}/tao_don_thuoc/').
          4. Kiểm tra HTTP 201 Created, tổng tiền đơn thuốc tự động tính = 10*18.000 + 10*2.000 = 200.000,00 VND.
        """
        lich_id = self._tao_lich_checked_in_cho_bs1()
        self.api_client.force_authenticate(user=self.u_bacsi1)
        ho_so_id = self.api_client.post(f'/api/lich-hen/lich-hen/{lich_id}/mo_ho_so_benh_an/', {}, format='json').data['ho_so']['id']

        du_lieu_nhap = {
            'ghi_chu': 'Uống thuốc đúng giờ sau ăn, tái khám sau 5 ngày',
            'chi_tiet': [
                {
                    'thuoc': str(self.thuoc_rx.pk),
                    'so_luong': 10,
                    'lieu_dung': '1 viên/lần x 2 lần/ngày',
                    'cach_dung': 'UONG',
                    'thoi_diem': 'SAU_AN',
                    'so_ngay_dung': 5,
                },
                {
                    'thuoc': str(self.thuoc_otc.pk),
                    'so_luong': 10,
                    'lieu_dung': '1 viên khi sốt > 38.5 độ',
                    'cach_dung': 'UONG',
                    'thoi_diem': 'SAU_AN',
                    'so_ngay_dung': 5,
                },
            ],
        }
        res_dt = self.api_client.post(
            f'/api/benh-an/ho-so-benh-an/{ho_so_id}/tao_don_thuoc/',
            du_lieu_nhap,
            format='json',
        )
        self.assertEqual(res_dt.status_code, 201, res_dt.content)
        self.assertEqual(Decimal(str(res_dt.data['tong_tien'])), Decimal('200000.00'))
        self.assertEqual(len(res_dt.data['chi_tiet']), 2)

    def test_TC_APP_05_bva_chan_ke_don_thuoc_rong_hoac_so_luong_khong_hop_le(self):
        """
        TC_APP_05 [BVA - Không hợp lệ]: Chặn bác sĩ lưu đơn thuốc khi nhập dòng thuốc thiếu mã thuốc hoặc so_luong <= 0 (REQ-RX-01).
        Test Case Procedure:
          1. Đăng nhập Bác sĩ (bacsi1_test) -> Mở hồ sơ khám của BN_TEST_01 -> Chọn tab [Kê đơn].
          2. Nhập dữ liệu biên không hợp lệ vào form Kê đơn (du_lieu_nhap):
             - Ghi chú (ghi_chu): 'Đơn có dòng thuốc không hợp lệ'
             - Dòng thuốc: Thuốc = None (bỏ trống), Số lượng (so_luong) = 0, Liều dùng (lieu_dung) = ''
          3. Nhấn nút [Lưu đơn].
          4. Kiểm tra hệ thống chặn với mã HTTP 400 Bad Request.
        """
        lich_id = self._tao_lich_checked_in_cho_bs1()
        self.api_client.force_authenticate(user=self.u_bacsi1)
        ho_so_id = self.api_client.post(f'/api/lich-hen/lich-hen/{lich_id}/mo_ho_so_benh_an/', {}, format='json').data['ho_so']['id']

        du_lieu_nhap = {
            'ghi_chu': 'Đơn có dòng thuốc không hợp lệ',
            'chi_tiet': [
                {
                    'thuoc': None,
                    'la_thuoc_mua_ngoai': False,
                    'so_luong': 0,
                    'lieu_dung': '',
                }
            ],
        }
        res_invalid = self.api_client.post(
            f'/api/benh-an/ho-so-benh-an/{ho_so_id}/tao_don_thuoc/',
            du_lieu_nhap,
            format='json',
        )
        self.assertEqual(res_invalid.status_code, 400)

    def test_TC_APP_06_integration_bac_si_chi_dinh_tiem_chung_da_tiem_tru_ton_kho_vaccine(self):
        """
        TC_APP_06 [Integration]: Bác sĩ nhập form Tiêm chủng với trạng thái DA_TIEM trên hồ sơ — tự động trừ 1 liều tồn kho vaccine và lưu số lô (UC008).
        Test Case Procedure:
          1. Đăng nhập Bác sĩ (bacsi1_test) -> Mở hồ sơ khám của BN_TEST_01 -> Chọn tab [Tiêm chủng].
          2. Nhập dữ liệu vào form Tiêm chủng (du_lieu_nhap):
             - Vaccine (vaccine): 'Influvac Tetra 0.5ml' (VC_CUM_01)
             - Số mũi (so_mui): 1
             - Ngày tiêm (ngay_tiem): Hôm nay (today)
             - Trạng thái (trang_thai): 'DA_TIEM'
             - Vị trí tiêm (vi_tri_tiem): 'Cơ delta cánh tay trái'
             - Ghi chú phản ứng sau tiêm (phan_ung_sau_tiem): 'Bình thường, theo dõi 30 phút tại phòng tiêm'
          3. Nhấn nút [Lưu tiêm chủng] (POST '/api/benh-an/ho-so-benh-an/{id}/chi_dinh_tiem/').
          4. Kiểm tra HTTP 201 Created, ghi nhận đúng lô 'LO-VC-01' và tồn kho vaccine giảm 1 liều (từ 10 còn 9).
        """
        lich_id = self._tao_lich_checked_in_cho_bs1()
        self.api_client.force_authenticate(user=self.u_bacsi1)
        ho_so_id = self.api_client.post(f'/api/lich-hen/lich-hen/{lich_id}/mo_ho_so_benh_an/', {}, format='json').data['ho_so']['id']

        ton_truoc = self.vaccine.ton_kho()
        du_lieu_nhap = {
            'vaccine': str(self.vaccine.pk),
            'so_mui': 1,
            'ngay_tiem': self.today.isoformat(),
            'trang_thai': 'DA_TIEM',
            'vi_tri_tiem': 'Cơ delta cánh tay trái',
            'ghi_chu': 'Bình thường, theo dõi 30 phút tại phòng tiêm',
        }
        res_tiem = self.api_client.post(
            f'/api/benh-an/ho-so-benh-an/{ho_so_id}/chi_dinh_tiem/',
            du_lieu_nhap,
            format='json',
        )
        self.assertEqual(res_tiem.status_code, 201, res_tiem.content)
        self.assertEqual(res_tiem.data['lo_vaccine'], 'LO-VC-01')
        self.assertEqual(self.vaccine.ton_kho(), ton_truoc - 1)

    def test_TC_APP_07_bva_bat_buoc_nhap_ma_icd10_khi_luu_chan_doan_theo_srs(self):
        """
        TC_APP_07 [BVA - FAILED vs SRS]: Theo SRS REQ-DIAG-02, bắt buộc nhập mã ICD-10 (ma_icd10); bỏ trống phải trả về 400 Bad Request.
        Test Case Procedure:
          1. Đăng nhập Bác sĩ (bacsi1_test) -> Mở hồ sơ khám của BN_TEST_01 -> Chọn tab [Nhập chẩn đoán].
          2. Nhập dữ liệu vào form Chẩn đoán nhưng bỏ trống trường Mã ICD-10 (du_lieu_nhap):
             - Triệu chứng (trieu_chung): 'Ho nhẹ, đau rát họng'
             - Kết quả khám lâm sàng (ket_qua_kham_lam_sang): 'Họng đỏ nhẹ'
             - Mã ICD-10 (ma_icd10): '' (Bỏ trống)
             - Tên bệnh (ten_benh): 'Viêm họng'
             - Loại bệnh (loai_benh): 'NGOAI_TRU'
             - Mức độ (muc_do): 'NHE'
             - Mô tả (mo_ta): 'Chẩn đoán thiếu mã ICD-10'
             - Kết luận (ket_luan): 'Theo dõi tại nhà'
          3. Nhấn nút [Lưu chẩn đoán].
          4. Kiểm tra phản hồi: Kỳ vọng theo SRS REQ-DIAG-02 trả về 400 Bad Request.
        """
        lich_id = self._tao_lich_checked_in_cho_bs1()
        self.api_client.force_authenticate(user=self.u_bacsi1)
        ho_so_id = self.api_client.post(f'/api/lich-hen/lich-hen/{lich_id}/mo_ho_so_benh_an/', {}, format='json').data['ho_so']['id']

        du_lieu_nhap = {
            'trieu_chung': 'Ho nhẹ, đau rát họng',
            'ket_qua_kham_lam_sang': 'Họng đỏ nhẹ',
            'ten_benh': 'Viêm họng',
            'ma_icd10': '',
            'loai_benh': 'NGOAI_TRU',
            'muc_do': 'NHẸ',
            'mo_ta': 'Chẩn đoán thiếu mã ICD-10',
            'ket_luan': 'Theo dõi tại nhà',
        }
        res_cd = self.api_client.post(
            f'/api/benh-an/ho-so-benh-an/{ho_so_id}/nhap_chan_doan/',
            du_lieu_nhap,
            format='json',
        )
        self.assertEqual(
            res_cd.status_code,
            400,
            "LỖI SRS (REQ-DIAG-02): Hệ thống cho phép lưu chẩn đoán (200 OK) khi bỏ trống mã bệnh quốc tế ma_icd10!",
        )

    def test_TC_APP_08_ep_nhap_chan_doan_voi_loai_benh_chinh_phu_theo_srs(self):
        """
        TC_APP_08 [EP - FAILED vs SRS]: Theo SRS REQ-DIAG-03 & Mục 4.2.11, trường loai_benh nhận giá trị 'CHINH' hoặc 'PHU'.
        Test Case Procedure:
          1. Đăng nhập Bác sĩ (bacsi1_test) -> Mở hồ sơ khám của BN_TEST_01 -> Chọn tab [Nhập chẩn đoán].
          2. Nhập dữ liệu vào form Chẩn đoán theo đúng danh mục của SRS (du_lieu_nhap):
             - Triệu chứng (trieu_chung): 'Đau họng, sốt cao'
             - Kết quả khám lâm sàng (ket_qua_kham_lam_sang): 'Amidan sưng đỏ'
             - Mã ICD-10 (ma_icd10): 'J02.9'
             - Tên bệnh (ten_benh): 'Viêm họng cấp'
             - Loại bệnh (loai_benh): 'CHINH' (Bệnh chính theo SRS Mục 4.2.11)
             - Mức độ (muc_do): 'TRUNG_BINH'
             - Mô tả (mo_ta): 'Bệnh chính'
             - Kết luận (ket_luan): 'Uống thuốc theo toa'
          3. Nhấn nút [Lưu chẩn đoán].
          4. Kiểm tra phản hồi: Kỳ vọng theo SRS REQ-DIAG-03 trả về 200 OK.
        """
        lich_id = self._tao_lich_checked_in_cho_bs1()
        self.api_client.force_authenticate(user=self.u_bacsi1)
        ho_so_id = self.api_client.post(f'/api/lich-hen/lich-hen/{lich_id}/mo_ho_so_benh_an/', {}, format='json').data['ho_so']['id']

        du_lieu_nhap = {
            'trieu_chung': 'Đau họng, sốt cao',
            'ket_qua_kham_lam_sang': 'Amidan sưng đỏ',
            'ten_benh': 'Viêm họng cấp',
            'ma_icd10': 'J02.9',
            'loai_benh': 'CHINH',
            'muc_do': 'TRUNG_BINH',
            'mo_ta': 'Bệnh chính',
            'ket_luan': 'Uống thuốc theo toa',
        }
        res_cd = self.api_client.post(
            f'/api/benh-an/ho-so-benh-an/{ho_so_id}/nhap_chan_doan/',
            du_lieu_nhap,
            format='json',
        )
        self.assertEqual(
            res_cd.status_code,
            200,
            "LỖI SRS (REQ-DIAG-03): Model ChanDoan không chấp nhận giá trị loai_benh='CHINH' như đặc tả trong SRS!",
        )

    # ==========================================================================
    # FUNCTION 2.2: Luồng Mua thuốc Online, Giỏ hàng & Thanh toán VNPay (UC010) — 8 TCs
    # ==========================================================================
    def test_TC_APP_09_rbac_benh_nhan_xem_cua_hang_chi_hien_thuoc_khong_ke_don(self):
        """
        TC_APP_09 [RBAC/Filter]: Bệnh nhân nhập từ khóa tìm kiếm trên Nhà thuốc trực tuyến chỉ thấy thuốc OTC (can_don_thuoc=False), ẩn thuốc kê đơn.
        Test Case Procedure:
          1. Đăng nhập tài khoản Bệnh nhân (benhnhan1_test) -> Chọn menu [Mua thuốc] (Nhà thuốc trực tuyến).
          2. Tại ô tìm kiếm sản phẩm, nhập dữ liệu lọc (du_lieu_nhap):
             - Từ khóa tìm kiếm (search): '' (Tất cả sản phẩm), Kích thước trang (page_size): 20
          3. Kiểm tra danh sách trả về chỉ hiển thị thuốc OTC 'Paracetamol 500mg' (TH_OTC_01) và ẩn thuốc kê đơn 'Augmentin 625mg' (TH_RX_01).
        """
        self.api_client.force_authenticate(user=self.u_bn1)
        du_lieu_nhap = {
            'search': '',
            'page_size': 20,
        }
        res = self.api_client.get('/api/thuoc/thuoc/', du_lieu_nhap)
        self.assertEqual(res.status_code, 200)
        items = res.data.get('results', res.data) if isinstance(res.data, dict) else res.data
        ma_list = [item['ma_thuoc'] for item in items]
        self.assertIn('TH_OTC_01', ma_list)
        self.assertNotIn('TH_RX_01', ma_list)

    def test_TC_APP_10_ep_benh_nhan_them_thuoc_vao_gio_hang_hop_le(self):
        """
        TC_APP_10 [EP - Hợp lệ]: Bệnh nhân nhập số lượng mua và thêm thuốc OTC vào giỏ hàng — chốt đơn giá và tính đúng tổng tiền.
        Test Case Procedure:
          1. Đăng nhập tài khoản Bệnh nhân (benhnhan1_test) -> Chọn menu [Mua thuốc].
          2. Chọn sản phẩm 'Paracetamol 500mg' (đơn giá 2.000đ/viên), nhập dữ liệu (du_lieu_nhap):
             - Bệnh nhân (benh_nhan_id): BN_TEST_01
             - Sản phẩm (thuoc_id): Paracetamol 500mg (TH_OTC_01)
             - Số lượng đặt mua (so_luong): 5
          3. Nhấn nút [Thêm vào giỏ] (POST '/api/don-hang/gio-hang/them/').
          4. Kiểm tra HTTP 200 OK, giỏ hàng ghi nhận 5 viên và tổng tiền = 10.000,0 VND.
        """
        self.api_client.force_authenticate(user=self.u_bn1)
        du_lieu_nhap = {
            'benh_nhan_id': str(self.bn1.pk),
            'thuoc_id': str(self.thuoc_otc.pk),
            'so_luong': 5,
        }
        res_add = self.api_client.post(
            '/api/don-hang/gio-hang/them/',
            json.dumps(du_lieu_nhap),
            content_type='application/json',
        )
        self.assertEqual(res_add.status_code, 200)
        body_add = json.loads(res_add.content)
        self.assertTrue(body_add['success'])
        self.assertEqual(body_add['data']['tong_tien_gio_hang'], 10000.0)

    def test_TC_APP_11_bva_chan_them_gio_hang_vuot_ton_kho_kha_dung(self):
        """
        TC_APP_11 [BVA - Biên tồn kho]: Chặn thêm thuốc vào giỏ hàng khi nhập so_luong vượt quá tồn kho khả dụng (151 > 150 -> 400 Bad Request, REQ-ONLINE-02).
        Test Case Procedure:
          1. Đăng nhập tài khoản Bệnh nhân (benhnhan1_test) -> Chọn menu [Mua thuốc].
          2. Chọn 'Paracetamol 500mg' (tồn kho khả dụng = 150 viên), nhập dữ liệu tại biên trên + 1 (du_lieu_nhap):
             - Bệnh nhân (benh_nhan_id): BN_TEST_01
             - Sản phẩm (thuoc_id): Paracetamol 500mg (TH_OTC_01)
             - Số lượng (so_luong): 151 (vượt tồn kho 150 viên)
          3. Nhấn nút [Thêm vào giỏ].
          4. Kiểm tra hệ thống chặn với mã HTTP 400 Bad Request.
        """
        self.api_client.force_authenticate(user=self.u_bn1)
        du_lieu_nhap = {
            'benh_nhan_id': str(self.bn1.pk),
            'thuoc_id': str(self.thuoc_otc.pk),
            'so_luong': 151,
        }
        res_over = self.api_client.post(
            '/api/don-hang/gio-hang/them/',
            json.dumps(du_lieu_nhap),
            content_type='application/json',
        )
        self.assertEqual(res_over.status_code, 400)

    def test_TC_APP_12_ep_cap_nhat_so_luong_va_xoa_san_pham_khoi_gio_hang(self):
        """
        TC_APP_12 [EP & State Transition]: Bệnh nhân nhập số lượng mới cập nhật trong giỏ hàng và xóa sản phẩm khỏi giỏ hàng (UC010).
        Test Case Procedure:
          1. Đăng nhập tài khoản Bệnh nhân (benhnhan1_test) -> Thêm 5 viên Paracetamol 500mg vào giỏ (du_lieu_nhap_them).
          2. Mở màn hình [Giỏ hàng], sửa ô Số lượng thành 12 viên (du_lieu_nhap_cap_nhat = {'so_luong': 12}) -> Nhấn [Cập nhật].
          3. Kiểm tra tổng tiền giỏ hàng tự động cập nhật thành 24.000,0 VND (12 * 2.000đ).
          4. Nhấn nút [Xóa] sản phẩm khỏi giỏ hàng -> Kiểm tra tổng tiền giỏ hàng về 0,0 VND.
        """
        self.api_client.force_authenticate(user=self.u_bn1)
        du_lieu_nhap_them = {
            'benh_nhan_id': str(self.bn1.pk),
            'thuoc_id': str(self.thuoc_otc.pk),
            'so_luong': 5,
        }
        res_add = self.api_client.post(
            '/api/don-hang/gio-hang/them/',
            json.dumps(du_lieu_nhap_them),
            content_type='application/json',
        )
        item_id = json.loads(res_add.content)['data']['item_id']

        du_lieu_nhap_cap_nhat = {'so_luong': 12}
        res_upd = self.api_client.put(
            f'/api/don-hang/gio-hang/cap-nhat/{item_id}/',
            json.dumps(du_lieu_nhap_cap_nhat),
            content_type='application/json',
        )
        self.assertEqual(res_upd.status_code, 200)
        self.assertEqual(json.loads(res_upd.content)['data']['tong_tien_gio_hang'], 24000.0)

        res_del = self.api_client.delete(f'/api/don-hang/gio-hang/xoa/{item_id}/')
        self.assertEqual(res_del.status_code, 200)
        self.assertEqual(json.loads(res_del.content)['data']['tong_tien_gio_hang'], 0.0)

    def test_TC_APP_13_state_benh_nhan_tao_don_hang_online_tu_gio_hang_tru_ton_kho(self):
        """
        TC_APP_13 [State Transition - Hợp lệ]: Bệnh nhân nhập thông tin giao hàng và đặt đơn hàng ONLINE từ giỏ hàng — trừ tồn kho FIFO và làm trống giỏ.
        Test Case Procedure:
          1. Đăng nhập tài khoản Bệnh nhân (benhnhan1_test) -> Thêm 20 viên Paracetamol 500mg vào giỏ hàng (du_lieu_nhap_gio_hang).
          2. Mở [Giỏ hàng], nhập dữ liệu vào form Thông tin giao hàng (du_lieu_nhap_dat_hang):
             - Loại đơn (loai_don): 'ONLINE'
             - Tên người nhận (ten_nguoi_nhan): 'Lê Văn Bệnh Nhân'
             - Số điện thoại nhận (so_dien_thoai_nhan): '0901000007'
             - Email nhận xác nhận (email_nhan): 'bn1_test@gmail.com'
             - Địa chỉ giao hàng (dia_chi_giao_hang): '123 Nguyễn Văn Linh, Hải Châu, Đà Nẵng'
             - Phí vận chuyển (phi_ship): 15000
             - Giảm giá (giam_gia): 0
             - Ghi chú đơn hàng (ghi_chu): 'Giao giờ hành chính'
          3. Nhấn nút [Đặt hàng] (POST '/api/don-hang/don-hang/tao/').
          4. Kiểm tra đơn hàng ở trạng thái CHO_THANH_TOAN, tổng tiền = 55.000đ, tồn kho giảm 20 viên (150 -> 130) và giỏ hàng được làm trống.
        """
        self.api_client.force_authenticate(user=self.u_bn1)
        du_lieu_nhap_gio_hang = {
            'benh_nhan_id': str(self.bn1.pk),
            'thuoc_id': str(self.thuoc_otc.pk),
            'so_luong': 20,
        }
        self.api_client.post(
            '/api/don-hang/gio-hang/them/',
            json.dumps(du_lieu_nhap_gio_hang),
            content_type='application/json',
        )
        ton_truoc = self.thuoc_otc.ton_kho()

        du_lieu_nhap_dat_hang = {
            'benh_nhan_id': str(self.bn1.pk),
            'loai_don': 'ONLINE',
            'ten_nguoi_nhan': 'Lê Văn Bệnh Nhân',
            'so_dien_thoai_nhan': '0901000007',
            'email_nhan': 'bn1_test@gmail.com',
            'dia_chi_giao_hang': '123 Nguyễn Văn Linh, Hải Châu, Đà Nẵng',
            'phi_ship': 15000,
            'giam_gia': 0,
            'ghi_chu': 'Giao giờ hành chính',
        }
        res_order = self.api_client.post(
            '/api/don-hang/don-hang/tao/',
            json.dumps(du_lieu_nhap_dat_hang),
            content_type='application/json',
        )
        self.assertEqual(res_order.status_code, 200, res_order.content)
        body = json.loads(res_order.content)
        self.assertTrue(body['success'])
        dh = DonHang.objects.get(pk=body['data']['don_hang_id'])
        self.assertEqual(dh.trang_thai, 'CHO_THANH_TOAN')
        self.assertEqual(float(dh.tong_tien), 55000.0)
        self.assertEqual(self.thuoc_otc.ton_kho(), ton_truoc - 20)
        self.assertFalse(GioHang.objects.filter(benh_nhan=self.bn1).exists())

    def test_TC_APP_14_error_guessing_chan_tao_don_hang_khi_gio_hang_trong(self):
        """
        TC_APP_14 [Error Guessing]: Chặn bệnh nhân nhập thông tin đặt đơn hàng Online khi giỏ hàng đang trống (400 Bad Request).
        Test Case Procedure:
          1. Đăng nhập tài khoản Bệnh nhân 2 (benhnhan2_test - giỏ hàng đang trống) -> Mở màn hình [Giỏ hàng].
          2. Nhập thông tin nhận hàng vào form Đặt hàng (du_lieu_nhap):
             - Tên người nhận (ten_nguoi_nhan): 'Phạm Thị Hoa'
             - Số điện thoại nhận (so_dien_thoai_nhan): '0901000008'
             - Email nhận xác nhận (email_nhan): 'bn2_test@gmail.com'
             - Địa chỉ giao hàng (dia_chi_giao_hang): '456 Lê Duẩn, Thanh Khê, Đà Nẵng'
          3. Nhấn nút [Đặt hàng].
          4. Kiểm tra hệ thống chặn với mã HTTP 400 Bad Request ('Giỏ hàng trống').
        """
        self.api_client.force_authenticate(user=self.u_bn2)
        du_lieu_nhap = {
            'benh_nhan_id': str(self.bn2.pk),
            'loai_don': 'ONLINE',
            'ten_nguoi_nhan': 'Phạm Thị Hoa',
            'so_dien_thoai_nhan': '0901000008',
            'email_nhan': 'bn2_test@gmail.com',
            'dia_chi_giao_hang': '456 Lê Duẩn, Thanh Khê, Đà Nẵng',
        }
        res_empty = self.api_client.post(
            '/api/don-hang/don-hang/tao/',
            json.dumps(du_lieu_nhap),
            content_type='application/json',
        )
        self.assertEqual(res_empty.status_code, 400)

    def test_TC_APP_15_integration_thanh_toan_don_online_qua_vnpay_tao_url_va_ipn_xac_nhan(self):
        """
        TC_APP_15 [Integration]: Đặt đơn hàng Online, chọn thanh toán VNPay và nhập thông tin thẻ trên cổng VNPay Mock/IPN chuyển sang DA_THANH_TOAN.
        Test Case Procedure:
          1. Đăng nhập Bệnh nhân (benhnhan1_test) -> Thêm 10 viên Paracetamol 500mg vào giỏ (du_lieu_nhap_gio_hang).
          2. Nhập form Đặt hàng Online (du_lieu_nhap_dat_hang) và chọn phương thức thanh toán 'VNPay' -> Nhấn [Đặt hàng].
          3. Hệ thống sinh URL thanh toán VNPay ('/api/don-hang/don-hang/{id}/vnpay-tao-url/').
          4. Tại màn hình cổng thanh toán VNPay Sandbox, nhập thông tin thẻ NCB test (du_lieu_nhap_the_vnpay):
             - Số thẻ (so_the): '9704198526191432198'
             - Tên chủ thẻ (ten_chu_the): 'NGUYEN VAN A'
             - Ngày phát hành/hết hạn (ngay_het_han): '07/15'
             - Mã OTP (otp): '123456'
             - Hành động (action): 'success'
          5. Nhấn [Xác nhận thanh toán] -> Kiểm tra đơn hàng chuyển sang DA_THANH_TOAN và lưu bản ghi ThanhToan(phuong_thuc='VNPAY', trang_thai='THANH_CONG').
        """
        self.api_client.force_authenticate(user=self.u_bn1)
        du_lieu_nhap_gio_hang = {
            'benh_nhan_id': str(self.bn1.pk),
            'thuoc_id': str(self.thuoc_otc.pk),
            'so_luong': 10,
        }
        self.api_client.post(
            '/api/don-hang/gio-hang/them/',
            json.dumps(du_lieu_nhap_gio_hang),
            content_type='application/json',
        )
        du_lieu_nhap_dat_hang = {
            'benh_nhan_id': str(self.bn1.pk),
            'loai_don': 'ONLINE',
            'ten_nguoi_nhan': 'Lê Văn Bệnh Nhân',
            'so_dien_thoai_nhan': '0901000007',
            'email_nhan': 'bn1_test@gmail.com',
            'dia_chi_giao_hang': '123 Nguyễn Văn Linh, Hải Châu, Đà Nẵng',
            'phuong_thuc_thanh_toan': 'VNPAY',
        }
        res_order = self.api_client.post(
            '/api/don-hang/don-hang/tao/',
            json.dumps(du_lieu_nhap_dat_hang),
            content_type='application/json',
        )
        dh_id = json.loads(res_order.content)['data']['don_hang_id']

        res_url = self.api_client.post(f'/api/don-hang/don-hang/{dh_id}/vnpay-tao-url/')
        self.assertEqual(res_url.status_code, 200, res_url.content)
        url_data = json.loads(res_url.content)['data']
        self.assertIn('payment_url', url_data)

        du_lieu_nhap_the_vnpay = {
            'txn_ref': url_data['txn_ref'],
            'amount': int(url_data['amount'] * 100),
            'action': 'success',
            'ngan_hang': 'NCB',
            'so_the': '9704198526191432198',
            'ten_chu_the': 'NGUYEN VAN A',
            'ngay_het_han': '07/15',
            'otp': '123456',
        }
        res_confirm = self.api_client.post('/api/don-hang/vnpay-mock/confirm/', du_lieu_nhap_the_vnpay)
        self.assertIn(res_confirm.status_code, (200, 302))
        dh = DonHang.objects.get(pk=dh_id)
        self.assertEqual(dh.trang_thai, 'DA_THANH_TOAN')
        self.assertTrue(ThanhToan.objects.filter(don_hang=dh, phuong_thuc='VNPAY', trang_thai='THANH_CONG').exists())

    def test_TC_APP_16_state_huy_don_hang_online_phai_tu_dong_hoan_tra_ton_kho_thuoc(self):
        """
        TC_APP_16 [State Transition - FAILED vs SRS]: Theo SRS UC010/REQ-FIFO-04, khi hủy đơn hàng Online (DA_HUY) phải hoàn trả lại số lượng thuốc về kho.
        Test Case Procedure:
          1. Đăng nhập Bệnh nhân (benhnhan1_test) -> Thêm 20 viên Paracetamol 500mg vào giỏ (du_lieu_nhap_gio_hang).
          2. Nhập thông tin giao hàng (du_lieu_nhap_dat_hang) và nhấn [Đặt hàng] (tồn kho Paracetamol giảm từ 150 xuống 130 viên).
          3. Thực hiện hủy đơn hàng vừa đặt với dữ liệu nhập (du_lieu_nhap_huy_don):
             - Trạng thái mới (trang_thai): 'DA_HUY'
             - Lý do hủy đơn (ly_do_huy): 'Khách hàng yêu cầu hủy đơn do đặt nhầm số lượng'
          4. Kiểm tra lại tồn kho Paracetamol 500mg: Kỳ vọng theo SRS REQ-FIFO-04 phải hoàn trả 20 viên về kho (150 viên).
        """
        self.api_client.force_authenticate(user=self.u_bn1)
        ton_ban_dau = self.thuoc_otc.ton_kho()  # 150
        du_lieu_nhap_gio_hang = {
            'benh_nhan_id': str(self.bn1.pk),
            'thuoc_id': str(self.thuoc_otc.pk),
            'so_luong': 20,
        }
        self.api_client.post(
            '/api/don-hang/gio-hang/them/',
            json.dumps(du_lieu_nhap_gio_hang),
            content_type='application/json',
        )
        du_lieu_nhap_dat_hang = {
            'benh_nhan_id': str(self.bn1.pk),
            'loai_don': 'ONLINE',
            'ten_nguoi_nhan': 'Lê Văn Bệnh Nhân',
            'so_dien_thoai_nhan': '0901000007',
            'email_nhan': 'bn1_test@gmail.com',
            'dia_chi_giao_hang': '123 Nguyễn Văn Linh, Hải Châu, Đà Nẵng',
        }
        res_order = self.api_client.post(
            '/api/don-hang/don-hang/tao/',
            json.dumps(du_lieu_nhap_dat_hang),
            content_type='application/json',
        )
        dh_id = json.loads(res_order.content)['data']['don_hang_id']
        self.assertEqual(self.thuoc_otc.ton_kho(), ton_ban_dau - 20)  # 130

        # Hủy đơn hàng với dữ liệu nhập lý do hủy
        self.api_client.force_authenticate(user=self.u_banthuoc)
        du_lieu_nhap_huy_don = {
            'trang_thai': 'DA_HUY',
            'ly_do_huy': 'Khách hàng yêu cầu hủy đơn do đặt nhầm số lượng',
        }
        res_cancel = self.api_client.put(
            f'/api/don-hang/don-hang/{dh_id}/cap-nhat-trang-thai/',
            json.dumps(du_lieu_nhap_huy_don),
            content_type='application/json',
        )
        self.assertEqual(res_cancel.status_code, 200, res_cancel.content)
        # Kỳ vọng theo SRS: Tồn kho phải được hoàn trả về 150 viên.
        # Thực tế DonHang.huy_don_hang không tính CHO_THANH_TOAN trong TRANG_THAI_DA_TRU_KHO nên tồn kho bị mất 20 viên (còn 130)!
        self.assertEqual(
            self.thuoc_otc.ton_kho(),
            ton_ban_dau,
            "LỖI SRS (UC010/REQ-FIFO-04): Hủy đơn hàng Online ở trạng thái CHO_THANH_TOAN không hoàn trả lại 20 viên thuốc đã trừ kho!",
        )
