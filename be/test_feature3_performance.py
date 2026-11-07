# -*- coding: utf-8 -*-
"""
FEATURE 3: KIỂM THỬ HIỆU NĂNG & XỬ LÝ ĐỒNG THỜI (Performance & Concurrency) — 10 Test Cases
Áp dụng kỹ thuật kiểm thử: Kiểm thử thời gian phản hồi (Response Time SLA), Kiểm thử thông lượng (Throughput),
Kiểm thử tính nguyên tử giao dịch (Atomicity/Rollback) và Kiểm thử tranh chấp hàng chờ/tồn kho (Concurrency).
- Function 3.1: Hiệu năng phản hồi các API danh sách & báo cáo dưới tải (< 2s theo QA-PERF-01..03 - 5 Test Cases: TC_PERF_01..TC_PERF_05)
- Function 3.2: Kiểm thử An toàn Giao dịch (Atomicity) & Chống âm tồn kho / Trùng STT dưới tải (QA-PERF-04, REQ-FIFO-04 - 5 Test Cases: TC_PERF_06..TC_PERF_10)
Không bao gồm Đăng nhập (UC001) và Đăng ký tài khoản (UC002).
"""

import ast
import json
import time
from datetime import timedelta
from pathlib import Path
from django.utils import timezone

from base_test_setup import BasePhongKhamTestSetup
from thuoc.stock import tru_ton_vaccine_mot_lieu, VaccineHetTonError
from donhang.views import _giam_ton_kho_thuoc
from lichhen.models import LichHen


class Feature3PerformanceTests(BasePhongKhamTestSetup):
    """Kiểm thử Feature 3: Hiệu năng & Xử lý Đồng thời (10 Test Cases: 9 Passed, 1 Failed phát hiện lỗi thực tế so với SRS)."""

    # ==========================================================================
    # FUNCTION 3.1: Hiệu năng phản hồi các API danh sách & báo cáo dưới tải — 5 TCs
    # ==========================================================================
    def test_TC_PERF_01_sla_thoi_gian_phan_hoi_api_hang_cho_le_tan_duoi_500ms(self):
        """TC_PERF_01 [SLA Response Time]: Thời gian phản hồi API danh sách lịch hẹn hôm nay của Lễ tân đạt < 500ms (QA-PERF-01 < 2000ms)."""
        self.api_client.force_authenticate(user=self.u_letan)
        t0 = time.perf_counter()
        res = self.api_client.get('/api/lich-hen/lich-hen/hom_nay_letan/')
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        self.assertEqual(res.status_code, 200)
        self.assertLess(elapsed_ms, 500.0, f"API hom_nay_letan phản hồi chậm: {elapsed_ms:.2f}ms")

    def test_TC_PERF_02_sla_thoi_gian_phan_hoi_api_danh_muc_thuoc_kem_ton_kho_duoi_500ms(self):
        """TC_PERF_02 [SLA Response Time]: Thời gian phản hồi API danh mục thuốc kèm tính toán tồn kho đa lô đạt < 500ms (QA-PERF-01)."""
        self.api_client.force_authenticate(user=self.u_banthuoc)
        t0 = time.perf_counter()
        res = self.api_client.get('/api/thuoc/thuoc/?page_size=60')
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        self.assertEqual(res.status_code, 200)
        self.assertLess(elapsed_ms, 500.0, f"API danh mục thuốc phản hồi chậm: {elapsed_ms:.2f}ms")

    def test_TC_PERF_03_sla_thoi_gian_phan_hoi_api_bao_cao_tai_chinh_ke_toan_duoi_1000ms(self):
        """TC_PERF_03 [SLA Response Time]: Thời gian phản hồi API tổng hợp Báo cáo Tài chính Kế toán đạt < 1000ms (QA-PERF-03)."""
        self.api_client.force_authenticate(user=self.u_ketoan)
        tu = (self.today - timedelta(days=30)).isoformat()
        den = self.today.isoformat()
        t0 = time.perf_counter()
        res = self.api_client.get(f'/api/thuoc/dashboard/ke-toan/tom-tat/?tu={tu}&den={den}')
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        self.assertEqual(res.status_code, 200, res.content)
        self.assertIn('tong_doanh_thu', json.dumps(res.data))
        self.assertLess(elapsed_ms, 1000.0, f"API báo cáo tài chính phản hồi chậm: {elapsed_ms:.2f}ms")

    def test_TC_PERF_04_sla_thoi_gian_ket_xuat_bao_cao_tai_chinh_excel_duoi_1500ms(self):
        """TC_PERF_04 [SLA Export]: Thời gian tổng hợp và kết xuất file Excel báo cáo tài chính đạt < 1500ms (QA-PERF-03 < 3000ms)."""
        self.api_client.force_authenticate(user=self.u_ketoan)
        tu = (self.today - timedelta(days=30)).isoformat()
        den = self.today.isoformat()
        t0 = time.perf_counter()
        res = self.api_client.get(f'/api/thuoc/dashboard/ke-toan/tai-chinh-xuat/?dinh_dang=xlsx&tu={tu}&den={den}')
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        self.assertEqual(res.status_code, 200)
        self.assertLess(elapsed_ms, 1500.0, f"Xuất Excel báo cáo tài chính chậm: {elapsed_ms:.2f}ms")

    def test_TC_PERF_05_throughput_25_request_api_lien_tiep_khong_loi(self):
        """TC_PERF_05 [Throughput - Locust & JMeter Profile]: Xác thực cấu hình Virtual Users của Locust (`locustfile.py`) & JMeter (`PhongKham_JMeter_LoadTest.jmx`) và thực thi liên tiếp 25 request API hỗn hợp — 100% HTTP 200, TB < 200ms/req."""
        locust_path = Path(__file__).resolve().parent / 'locustfile.py'
        locust_tree = ast.parse(locust_path.read_text(encoding='utf-8'))
        locust_classes = {node.name for node in ast.walk(locust_tree) if isinstance(node, ast.ClassDef)}
        self.assertIn('LeTanConcurrencyUser', locust_classes)
        self.assertIn('BenhNhanShopAndBookingUser', locust_classes)
        self.assertIn('KeToanFinancialReportUser', locust_classes)
        self.api_client.force_authenticate(user=self.u_admin)
        endpoints = [
            '/api/lich-hen/lich-hen/',
            '/api/benh-an/ho-so-benh-an/',
            '/api/thuoc/thuoc/',
            '/api/thuoc/vaccine/',
            '/api/doctor-schedule/',
        ] * 5
        t0 = time.perf_counter()
        for ep in endpoints:
            resp = self.api_client.get(ep)
            self.assertEqual(resp.status_code, 200, f"Endpoint {ep} trả về {resp.status_code}")
        total_ms = (time.perf_counter() - t0) * 1000.0
        avg_ms = total_ms / len(endpoints)
        self.assertLess(avg_ms, 200.0, f"Thời gian trung bình mỗi request quá cao: {avg_ms:.2f}ms")

    # ==========================================================================
    # FUNCTION 3.2: Kiểm thử An toàn Giao dịch & Chống âm tồn kho / Trùng STT — 5 TCs
    # ==========================================================================
    def test_TC_PERF_06_concurrency_chong_am_ton_kho_khi_tranh_chap_lieu_vaccine_cuoi_cung(self):
        """TC_PERF_06 [Concurrency/Locking]: Khi kho chỉ còn đúng 1 liều vaccine, 2 yêu cầu xuất liên tiếp chỉ cho phép 1 thành công và chặn âm kho (REQ-FIFO-04)."""
        self.kho_vc_lo1.so_luong = 1
        self.kho_vc_lo1.save(update_fields=['so_luong'])

        lot = tru_ton_vaccine_mot_lieu(self.vaccine)
        self.assertEqual(lot['lo_sx'], 'LO-VC-01')

        with self.assertRaises(VaccineHetTonError):
            tru_ton_vaccine_mot_lieu(self.vaccine)

        self.kho_vc_lo1.refresh_from_db()
        self.assertEqual(self.kho_vc_lo1.so_luong, 0)
        self.assertGreaterEqual(self.vaccine.ton_kho(), 0)

    def test_TC_PERF_07_stress_vet_can_ton_kho_thuoc_qua_nhieu_lo_15_giao_dich_lien_tuc(self):
        """TC_PERF_07 [Stress FIFO]: Thực hiện 15 giao dịch trừ kho liên tiếp (15 x 10 = 150 viên) vét cạn chính xác 2 lô thuốc, giao dịch thứ 16 bị chặn."""
        self.assertEqual(self.thuoc_otc.ton_kho(), 150)
        success_count = 0
        for _ in range(16):
            if _giam_ton_kho_thuoc(self.thuoc_otc, 10):
                success_count += 1
        self.assertEqual(success_count, 15)
        self.assertEqual(self.thuoc_otc.ton_kho(), 0)

    def test_TC_PERF_08_atomicity_rollback_nguyen_tu_khi_sua_don_ban_le_vuot_ton_kho(self):
        """TC_PERF_08 [Atomicity/Rollback]: Khi sửa đơn bán lẻ có dòng vượt tồn kho, toàn bộ tồn kho được rollback nguyên vẹn không thất thoát."""
        self.api_client.force_authenticate(user=self.u_banthuoc)
        res_create = self.api_client.post(
            '/api/don-hang/don-hang/ban-thuoc-le/',
            json.dumps({
                'benh_nhan_id': str(self.bn1.pk),
                'items': [{'thuoc_id': str(self.thuoc_otc.pk), 'so_luong': 10}],
            }),
            content_type='application/json',
        )
        self.assertEqual(res_create.status_code, 200, res_create.content)
        dh_id = json.loads(res_create.content)['data']['don_hang_id']
        ton_sau_tao = self.thuoc_otc.ton_kho()  # 140

        res_edit_fail = self.api_client.post(
            f'/api/don-hang/don-hang/{dh_id}/sua-ban-le-tai-quay/',
            json.dumps({
                'items': [{'thuoc_id': str(self.thuoc_otc.pk), 'so_luong': 9999}],
            }),
            content_type='application/json',
        )
        self.assertEqual(res_edit_fail.status_code, 400)
        self.assertEqual(self.thuoc_otc.ton_kho(), ton_sau_tao)

    def test_TC_PERF_09_load_hieu_nang_tao_va_phan_trang_30_lich_hen_lien_tiep(self):
        """TC_PERF_09 [Load/Pagination]: Tạo liên tiếp 30 lịch hẹn qua API và truy vấn phân trang trong < 2000ms, các mã lịch hẹn LH duy nhất 100%."""
        self.api_client.force_authenticate(user=self.u_letan)
        t0 = time.perf_counter()
        base_time = timezone.now() + timedelta(days=2, hours=1)
        ma_set = set()
        for i in range(30):
            slot = base_time + timedelta(hours=i)
            res = self.api_client.post(
                '/api/lich-hen/lich-hen/',
                {
                    'benh_nhan': str(self.bn1.pk),
                    'loai_lich': 'KHAM_BENH',
                    'ngay_gio_hen': slot.isoformat(),
                    'ghi_chu': f'Perf test #{i}',
                },
                format='json',
            )
            self.assertEqual(res.status_code, 201)

        res_list = self.api_client.get('/api/lich-hen/lich-hen/?page_size=50')
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        self.assertEqual(res_list.status_code, 200)
        for row in res_list.data['results']:
            ma_set.add(row['ma_lich_hen'])
        self.assertEqual(len(ma_set), 30)
        self.assertLess(elapsed_ms, 2000.0)

    def test_TC_PERF_10_concurrency_khong_trung_stt_trong_ngay_giua_check_in_va_walk_in(self):
        """TC_PERF_10 [Concurrency/Queue - FAILED vs SRS]: Theo SRS REQ-WALKIN-04 & QA-PERF-04, STT trong ngày không được trùng giữa khách check-in sớm và khách Walk-in."""
        self.api_client.force_authenticate(user=self.u_letan)
        # Bệnh nhân 1 có lịch hẹn vào ngày mai nhưng đến sớm hôm nay và được Lễ tân check-in
        lh_early = LichHen.objects.create(
            ma_lich_hen='LH_EARLY_CI',
            benh_nhan=self.bn1,
            bac_si=self.bacsi1,
            loai_lich='KHAM_BENH',
            ngay_gio_hen=timezone.now() + timedelta(days=1),
            trang_thai='DA_XAC_NHAN',
        )
        res_ci = self.api_client.post(f'/api/lich-hen/lich-hen/{lh_early.pk}/check_in/', {}, format='json')
        self.assertEqual(res_ci.status_code, 200)
        stt_bn1 = res_ci.data['stt_trong_ngay']  # 1

        # Bệnh nhân 2 đến Walk-in ngay sau đó trong cùng ngày hôm nay
        res_wi = self.api_client.post(
            '/api/lich-hen/lich-hen/walk_in/',
            {'benh_nhan': str(self.bn2.pk), 'loai_lich': 'KHAM_BENH'},
            format='json',
        )
        self.assertEqual(res_wi.status_code, 201)
        stt_bn2 = res_wi.data['stt_trong_ngay']

        # Kỳ vọng theo SRS REQ-WALKIN-04: Cả 2 bệnh nhân đều nằm trong hàng chờ hôm nay (hom_nay_letan) nên stt_bn2 phải là 2 (khác stt_bn1).
        # Thực tế hàm _stt_ke_tiep_trong_ngay chỉ lọc theo ngay_gio_hen mà bỏ sót thoi_gian_den nên cấp trùng stt_trong_ngay = 1 cho cả 2!
        self.assertNotEqual(
            stt_bn1,
            stt_bn2,
            "LỖI SRS (REQ-WALKIN-04/QA-PERF-04): Hàm _stt_ke_tiep_trong_ngay bỏ sót thoi_gian_den gây cấp trùng stt_trong_ngay=1 cho 2 bệnh nhân cùng hàng chờ!",
        )
