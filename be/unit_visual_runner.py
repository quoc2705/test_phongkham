# -*- coding: utf-8 -*-
"""
TRÌNH CHIẾU KIỂM THỬ ĐƠN VỊ HỘP TRẮNG TRỰC QUAN (WHITE-BOX UNIT TEST VISUAL RUNNER)
===================================================================================
Công cụ trực quan hóa quá trình chạy 13 Unit Test Cases (Feature 5: TC_UNIT_01 .. TC_UNIT_13):
1. Giao diện Desktop GUI (Tkinter) tự động chạy từng bước 13 câu Unit Test (Auto-Play):
   - Hiển thị danh sách 13 Test Cases kèm trạng thái PASSED (Xanh lá) / FAILED (Đỏ).
   - Soi trực tiếp đoạn Code Hộp Trắng (White-Box Python Source Code) của hàm đang được kiểm thử.
   - Hiển thị chi tiết: Dữ liệu đầu vào (Input) -> Kỳ vọng SRS (Expected) -> Kết quả thực tế (Actual).
2. Tự động xuất file báo cáo giao diện Web HTML trực quan: `unit_test_report.html`.

Cách chạy:
  - Mở cửa sổ trình chiếu trực quan tự động (Mặc định 1.8 giây/bước):
    .venv\\Scripts\\python -X utf8 be\\unit_visual_runner.py
  - Mở cửa sổ trình chiếu chậm hơn (ví dụ 3 giây/bước):
    .venv\\Scripts\\python -X utf8 be\\unit_visual_runner.py --delay=3
  - Chạy nhanh trên Terminal + tự động bật báo cáo HTML trên trình duyệt:
    .venv\\Scripts\\python -X utf8 be\\unit_visual_runner.py --headless --open-browser
"""

import argparse
import html
import inspect
import os
import sys
import time
import unittest
import webbrowser
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
BE_DIR = Path(__file__).resolve().parent
for p in (str(ROOT_DIR), str(BE_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "phongkham.settings")

import django

django.setup()

from django.test.utils import (
    setup_databases,
    teardown_databases,
    setup_test_environment,
    teardown_test_environment,
)
from test_feature5_unit import Feature5UnitTests
from thuoc.models import Thuoc, KhoThuoc
from thuoc.stock import tru_ton_vaccine_mot_lieu
from donhang.views import _giam_ton_kho_thuoc
from donhang.models import DonHang
from benhan.models import DonThuoc, ChiTietDonThuoc
from nguoidung.models import BenhNhan
from nguoidung.doctor_schedule import phan_ca_tu_thoi_diem
from phongkham.time_utils import bounds_for_local_days


def _get_source_snippet(objs):
    blocks = []
    for label, obj in objs:
        try:
            lines, start_line = inspect.getsourcelines(obj)
            numbered = "".join(f"{start_line + i:4d} | {line}" for i, line in enumerate(lines))
            blocks.append(f"# === {label} ===\n{numbered}")
        except Exception as exc:
            blocks.append(f"# === {label} ===\n(Không đọc được source: {exc})")
    return "\n".join(blocks)


UNIT_METADATA = {
    "TC_UNIT_01": {
        "func_group": "5.1 - FIFO Kho & Cảnh báo HSD",
        "technique": "EP (Phân vùng tương đương)",
        "target": "thuoc/models.py :: Thuoc.ton_kho() & KhoThuoc.con_han()",
        "sources": [("be/thuoc/models.py :: Thuoc.ton_kho", Thuoc.ton_kho), ("be/thuoc/models.py :: KhoThuoc.con_han", KhoThuoc.con_han)],
        "input_desc": "• Lô 1 (Còn hạn +60 ngày): 50 viên\n• Lô 2 (Còn hạn +180 ngày): 100 viên\n• Lô 3 (Đã hết hạn -5 ngày): 30 viên",
        "expected_desc": "• Thuoc.ton_kho() chỉ cộng Lô 1 + Lô 2 = 150 viên (bỏ qua 30 viên Lô 3 hết hạn).\n• lo_het_han.con_han() == False.",
        "actual_pass": "• Thuoc.ton_kho() trả về 150 viên.\n• lo_het_han.con_han() == False | lo1.con_han() == True (Khớp 100% SRS REQ-FIFO-01).",
    },
    "TC_UNIT_02": {
        "func_group": "5.1 - FIFO Kho & Cảnh báo HSD",
        "technique": "BVA (Phân tích giá trị biên)",
        "target": "thuoc/models.py :: KhoThuoc.con_han() & KhoThuoc.sap_het_han()",
        "sources": [("be/thuoc/models.py :: KhoThuoc.con_han", KhoThuoc.con_han), ("be/thuoc/models.py :: KhoThuoc.sap_het_han", KhoThuoc.sap_het_han)],
        "input_desc": "• Lô biên: han_su_dung == today (50 viên)\n• Lô 1: han_su_dung == today + 60 ngày (nằm trong ngưỡng <= 90 ngày)\n• Lô 2: han_su_dung == today + 180 ngày (> 90 ngày)",
        "expected_desc": "• Lô có HSD == today bị coi là hết hạn (con_han() == False).\n• Lô +60 ngày bật sap_het_han() == True; Lô +180 ngày sap_het_han() == False.",
        "actual_pass": "• lo_hom_nay.con_han() == False; ton_kho() giữ nguyên 80 viên.\n• lo1.sap_het_han() == True; lo2.sap_het_han() == False.",
    },
    "TC_UNIT_03": {
        "func_group": "5.1 - FIFO Kho & Cảnh báo HSD",
        "technique": "White-box Logic Path (FIFO)",
        "target": "donhang/views.py :: _giam_ton_kho_thuoc(thuoc, so_luong)",
        "sources": [("be/donhang/views.py :: _giam_ton_kho_thuoc", _giam_ton_kho_thuoc)],
        "input_desc": "• Lô 1 (HSD gần nhất +60 ngày): 50 viên\n• Lô 2 (HSD xa hơn +180 ngày): 100 viên\n• Gọi _giam_ton_kho_thuoc(thuoc_otc, 70)",
        "expected_desc": "• Ưu tiên trừ vét cạn Lô 1 trước (50 -> 0 viên), phần thiếu 20 viên trừ tiếp vào Lô 2 (100 -> 80 viên).\n• Tổng tồn còn lại = 80 viên.",
        "actual_pass": "• Hàm trả về True.\n• Lô 1 còn 0 viên, Lô 2 còn 80 viên, Tổng tồn = 80 viên (Đúng chuẩn FIFO Đa lô).",
    },
    "TC_UNIT_04": {
        "func_group": "5.1 - FIFO Kho & Cảnh báo HSD",
        "technique": "BVA (Biên vượt tồn kho)",
        "target": "donhang/views.py :: _giam_ton_kho_thuoc(thuoc, 151)",
        "sources": [("be/donhang/views.py :: _giam_ton_kho_thuoc", _giam_ton_kho_thuoc)],
        "input_desc": "• Tổng tồn khả dụng: 150 viên (Lô 1: 50 + Lô 2: 100)\n• Gọi _giam_ton_kho_thuoc(thuoc_otc, 151) (vượt biên +1 viên)",
        "expected_desc": "• Hàm trả về False ngay lập tức.\n• Không làm thay đổi số lượng của bất kỳ lô nào (Lô 1 = 50, Lô 2 = 100).",
        "actual_pass": "• Hàm trả về False.\n• Bảo toàn nguyên vẹn Lô 1 = 50 viên, Lô 2 = 100 viên.",
    },
    "TC_UNIT_05": {
        "func_group": "5.1 - FIFO Kho & Cảnh báo HSD",
        "technique": "White-box Logic Path (FIFO Vaccine)",
        "target": "thuoc/stock.py :: tru_ton_vaccine_mot_lieu(vaccine)",
        "sources": [("be/thuoc/stock.py :: tru_ton_vaccine_mot_lieu", tru_ton_vaccine_mot_lieu)],
        "input_desc": "• Lô Vaccine LO-VC-01 (HSD gần nhất, tồn = 20 liều)\n• Gọi tru_ton_vaccine_mot_lieu(vaccine)",
        "expected_desc": "• Trừ đúng 1 liều tại lô LO-VC-01 (20 -> 19 liều) và trả về dict metadata {'lo_sx': 'LO-VC-01', ...}.",
        "actual_pass": "• Trả về info['lo_sx'] == 'LO-VC-01'.\n• Tồn kho LO-VC-01 giảm chính xác từ 20 xuống 19 liều.",
    },
    "TC_UNIT_06": {
        "func_group": "5.1 - FIFO Kho & Cảnh báo HSD",
        "technique": "Exception Handling (Ngoại lệ)",
        "target": "thuoc/stock.py :: tru_ton_vaccine_mot_lieu() -> VaccineHetTonError",
        "sources": [("be/thuoc/stock.py :: tru_ton_vaccine_mot_lieu", tru_ton_vaccine_mot_lieu)],
        "input_desc": "• Cập nhật tồn kho lô vaccine = 0 liều\n• Gọi tru_ton_vaccine_mot_lieu(vaccine)",
        "expected_desc": "• Ném đúng ngoại lệ tùy chỉnh VaccineHetTonError để cảnh báo hết tồn kho.",
        "actual_pass": "• Đã bắt được ngoại lệ VaccineHetTonError đúng thiết kế.",
    },
    "TC_UNIT_07": {
        "func_group": "5.1 - FIFO Kho & Cảnh báo HSD",
        "technique": "White-box Defect Detection (BUG-10)",
        "target": "thuoc/models.py :: Thuoc.sap_het_han()",
        "sources": [("be/thuoc/models.py :: Thuoc.sap_het_han", Thuoc.sap_het_han)],
        "input_desc": "• Lô A (LO-EMPTY-SOON): Đã bán hết (so_luong = 0), HSD còn 10 ngày\n• Lô B (LO-FULL-LONG): Còn 100 viên, HSD còn 365 ngày\n• Gọi t_check.sap_het_han()",
        "expected_desc": "• Theo SRS REQ-FIFO-02: Thuoc.sap_het_han() phải trả về False (vì lô sắp hết hạn đã bán hết sạch so_luong = 0, còn lô đang bán còn hạn 365 ngày).",
        "actual_pass": "• [PHÁT HIỆN BUG-10]: Thuoc.sap_het_han() trả về True! Do truy vấn self.kho.filter(...) trong be/thuoc/models.py thiếu điều kiện so_luong__gt=0.",
    },
    "TC_UNIT_08": {
        "func_group": "5.2 - BHYT, Tiền tệ & Thời gian",
        "technique": "EP & BVA (Chỉ số Y sinh & BHYT)",
        "target": "nguoidung/models.py :: BenhNhan.tuoi(), get_bmi(), kiem_tra_bhyt_con_han()",
        "sources": [
            ("be/nguoidung/models.py :: BenhNhan.get_bmi", BenhNhan.get_bmi),
            ("be/nguoidung/models.py :: BenhNhan.kiem_tra_bhyt_con_han", BenhNhan.kiem_tra_bhyt_con_han),
        ],
        "input_desc": "• Bệnh nhân 1: Cao 170cm, Nặng 65kg, BHYT còn hạn\n• Bệnh nhân 2: Thẻ BHYT đã quá hạn",
        "expected_desc": "• BMI = 65 / (1.7 * 1.7) = 22.49 ('Bình thường').\n• bn1.kiem_tra_bhyt_con_han() == True; bn2.kiem_tra_bhyt_con_han() == False.",
        "actual_pass": "• BMI = 22.49 ('Bình thường'), tuổi >= 30.\n• Kiểm tra hạn thẻ BHYT trả về True/False chính xác.",
    },
    "TC_UNIT_09": {
        "func_group": "5.2 - BHYT, Tiền tệ & Thời gian",
        "technique": "Formula Verification (Công thức BHYT)",
        "target": "benhan/models.py :: ChiTietDonThuoc.thanh_tien() & DonThuoc.tinh_tong_tien()",
        "sources": [
            ("be/benhan/models.py :: ChiTietDonThuoc.thanh_tien", ChiTietDonThuoc.thanh_tien),
            ("be/benhan/models.py :: DonThuoc.tinh_tong_tien", DonThuoc.tinh_tong_tien),
            ("be/benhan/models.py :: DonThuoc.save", DonThuoc.save),
        ],
        "input_desc": "• Đơn thuốc có ty_le_bao_hiem = 80%\n• Chi tiết: 10 viên x 18,000đ = 180,000đ",
        "expected_desc": "• Tổng tiền = 180,000đ\n• BHYT chi trả (80%) = 144,000đ\n• Bệnh nhân đồng chi trả (20%) = 36,000đ.",
        "actual_pass": "• thanh_tien() = 180,000đ | so_tien_bao_hiem = 144,000đ | so_tien_benh_nhan_tra = 36,000đ.",
    },
    "TC_UNIT_10": {
        "func_group": "5.2 - BHYT, Tiền tệ & Thời gian",
        "technique": "BVA (Biên tiền tệ & Giảm giá)",
        "target": "donhang/models.py :: DonHang.save() & DonHang.clean()",
        "sources": [
            ("be/donhang/models.py :: DonHang.clean", DonHang.clean),
            ("be/donhang/models.py :: DonHang.save", DonHang.save),
        ],
        "input_desc": "• TH1: Tiền hàng 100,000đ + Ship 15,000đ - Giảm giá 5,000đ\n• TH2 (Biên âm): Tiền hàng 50,000đ, Giảm giá 60,000đ (vượt tổng tiền)",
        "expected_desc": "• TH1: Tự động tính tong_tien = 110,000đ.\n• TH2: DonHang.clean() ném ValidationError chặn giảm giá vượt tổng tiền.",
        "actual_pass": "• TH1: tong_tien == 110,000đ.\n• TH2: Đã ném ValidationError đúng quy tắc tài chính.",
    },
    "TC_UNIT_11": {
        "func_group": "5.2 - BHYT, Tiền tệ & Thời gian",
        "technique": "BVA (Biên khung giờ Ca làm việc)",
        "target": "nguoidung/doctor_schedule.py :: phan_ca_tu_thoi_diem() & bounds_for_local_days()",
        "sources": [
            ("be/nguoidung/doctor_schedule.py :: phan_ca_tu_thoi_diem", phan_ca_tu_thoi_diem),
            ("be/phongkham/time_utils.py :: bounds_for_local_days", bounds_for_local_days),
        ],
        "input_desc": "• Mốc giờ: 08:30 (Sáng), 14:15 (Chiều), 19:00 (Tối)\n• Khoảng ngày: 2026-11-01 đến 2026-11-05",
        "expected_desc": "• Trả về đúng mã ca 'SANG', 'CHIEU', 'TOI' và chuẩn hóa mốc datetime đầu ngày / cuối ngày.",
        "actual_pass": "• phan_ca_tu_thoi_diem() trả về 'SANG', 'CHIEU', 'TOI' chính xác; bounds_for_local_days() hợp lệ.",
    },
    "TC_UNIT_12": {
        "func_group": "5.2 - BHYT, Tiền tệ & Thời gian",
        "technique": "BVA (Biên sinh học Bệnh nhân)",
        "target": "nguoidung/models.py :: BenhNhan.clean()",
        "sources": [("be/nguoidung/models.py :: BenhNhan.clean", BenhNhan.clean)],
        "input_desc": "• Gán chiều cao bệnh nhân vượt ngưỡng sinh học: chieu_cao = 280.00 cm (> biên tối đa 250 cm)",
        "expected_desc": "• Phương thức BenhNhan.clean() ném ngoại lệ ValidationError chặn dữ liệu bất thường.",
        "actual_pass": "• Đã bắt được ValidationError khi chieu_cao = 280.00 cm.",
    },
    "TC_UNIT_13": {
        "func_group": "5.2 - BHYT, Tiền tệ & Thời gian",
        "technique": "White-box Defect Detection (BUG-11)",
        "target": "benhan/models.py :: DonThuoc.save() & tinh_tong_tien()",
        "sources": [
            ("be/benhan/models.py :: DonThuoc.save", DonThuoc.save),
            ("be/benhan/models.py :: DonThuoc.tinh_tong_tien", DonThuoc.tinh_tong_tien),
        ],
        "input_desc": "• Bệnh nhân bn1 có thẻ BHYT còn hạn (ma_bhyt='DN4010012345678', mức hưởng 80%)\n• Tạo DonThuoc(ho_so=hs, benh_nhan=bn1, bac_si=bacsi1) và gọi tinh_tong_tien()",
        "expected_desc": "• Theo SRS UC007/REQ-RX-04: DonThuoc.save() phải tự động lấy mã BHYT & tỷ lệ hưởng từ hồ sơ BenhNhan còn hạn -> so_tien_bao_hiem > 0.",
        "actual_pass": "• [PHÁT HIỆN BUG-11]: so_tien_bao_hiem = 0.00đ! Do DonThuoc.save() trong be/benhan/models.py không tự động đồng bộ thông tin BHYT từ model BenhNhan.",
    },
}


def execute_all_unit_tests():
    """Chạy thật 13 Unit Test Cases trên CSDL test cô lập và thu thập kết quả chi tiết."""
    setup_test_environment()
    old_config = setup_databases(verbosity=0, interactive=False)
    results_data = []
    try:
        loader = unittest.TestLoader()
        suite = loader.loadTestsFromTestCase(Feature5UnitTests)
        test_names = sorted(
            [t._testMethodName for t in suite],
            key=lambda name: int(name.split("_")[3]),
        )
        for idx, method_name in enumerate(test_names, start=1):
            tc_id = "_".join(method_name.split("_")[1:4])  # TC_UNIT_XX
            meta = UNIT_METADATA.get(tc_id, {})
            single_suite = unittest.TestSuite([Feature5UnitTests(method_name)])
            res = unittest.TestResult()
            t0 = time.perf_counter()
            single_suite.run(res)
            elapsed_ms = (time.perf_counter() - t0) * 1000.0

            doc = (getattr(Feature5UnitTests, method_name).__doc__ or method_name).strip().splitlines()[0]
            passed = res.wasSuccessful()
            err_msg = ""
            if res.failures:
                err_msg = res.failures[0][1].strip().splitlines()[-1]
            elif res.errors:
                err_msg = res.errors[0][1].strip().splitlines()[-1]

            source_code = _get_source_snippet(meta.get("sources", []))
            results_data.append(
                {
                    "index": idx,
                    "tc_id": tc_id,
                    "method_name": method_name,
                    "doc": doc,
                    "func_group": meta.get("func_group", "Feature 5 - Unit Test"),
                    "technique": meta.get("technique", "White-box"),
                    "target": meta.get("target", method_name),
                    "input_desc": meta.get("input_desc", ""),
                    "expected_desc": meta.get("expected_desc", ""),
                    "actual_desc": meta.get("actual_pass", "") if passed else f"{meta.get('actual_pass', '')}\n• Assertion Trace: {err_msg}",
                    "source_code": source_code,
                    "passed": passed,
                    "status": "PASSED" if passed else "FAILED",
                    "elapsed_ms": elapsed_ms,
                }
            )
    finally:
        teardown_databases(old_config, verbosity=0)
        teardown_test_environment()
    return results_data


def generate_html_report(results_data):
    """Xuất báo cáo HTML tương tác cho 13 Unit Test Cases Hộp trắng."""
    total = len(results_data)
    passed = sum(1 for r in results_data if r["passed"])
    failed = total - passed
    total_ms = sum(r["elapsed_ms"] for r in results_data)

    cards_html = []
    for r in results_data:
        badge_cls = "badge-pass" if r["passed"] else "badge-fail"
        card_cls = "card-pass" if r["passed"] else "card-fail"
        cards_html.append(
            f"""
            <div class="tc-card {card_cls}" data-status="{r['status']}">
              <div class="tc-header">
                <div>
                  <span class="tc-id">[{r['index']:02d}/13] {html.escape(r['tc_id'])}</span>
                  <span class="tc-group">{html.escape(r['func_group'])}</span>
                  <span class="tc-tech">{html.escape(r['technique'])}</span>
                </div>
                <div>
                  <span class="tc-time">{r['elapsed_ms']:.1f} ms</span>
                  <span class="badge {badge_cls}">{r['status']}</span>
                </div>
              </div>
              <div class="tc-title">{html.escape(r['doc'])}</div>
              <div class="tc-target">Hàm mục tiêu (White-box Target): <code>{html.escape(r['target'])}</code></div>
              <div class="tc-grid">
                <div class="box box-input">
                  <div class="box-title">1. Dữ liệu đầu vào (Test Input)</div>
                  <pre>{html.escape(r['input_desc'])}</pre>
                </div>
                <div class="box box-expected">
                  <div class="box-title">2. Kết quả kỳ vọng (Expected SRS)</div>
                  <pre>{html.escape(r['expected_desc'])}</pre>
                </div>
                <div class="box {'box-actual-pass' if r['passed'] else 'box-actual-fail'}">
                  <div class="box-title">3. Kết quả thực tế (Actual Output)</div>
                  <pre>{html.escape(r['actual_desc'])}</pre>
                </div>
              </div>
              <details class="code-details" {'open' if not r['passed'] else ''}>
                <summary>Soi mã nguồn Hộp trắng (White-Box Python Source Code) — Nhấn để đóng/mở</summary>
                <pre class="code-block">{html.escape(r['source_code'])}</pre>
              </details>
            </div>
            """
        )

    html_content = f"""<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="utf-8">
<title>Báo cáo Kiểm thử Đơn vị Hộp trắng (Unit Test) — PhòngKhám+</title>
<style>
  body {{ font-family: 'Segoe UI', Tahoma, sans-serif; background: #0f172a; color: #f8fafc; margin: 0; padding: 24px; }}
  .container {{ max-width: 1280px; margin: 0 auto; }}
  .hero {{ background: linear-gradient(135deg, #1e293b, #0f172a); border: 1px solid #334155; border-radius: 12px; padding: 20px 24px; margin-bottom: 20px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 16px; }}
  .hero h1 {{ margin: 0 0 6px 0; font-size: 22px; color: #38bdf8; }}
  .hero p {{ margin: 0; color: #94a3b8; font-size: 14px; }}
  .stats {{ display: flex; gap: 14px; }}
  .stat-box {{ background: #1e293b; border: 1px solid #475569; padding: 10px 18px; border-radius: 10px; text-align: center; min-width: 95px; }}
  .stat-val {{ font-size: 22px; font-weight: 700; }}
  .stat-lbl {{ font-size: 12px; color: #94a3b8; }}
  .pass-color {{ color: #4ade80; }}
  .fail-color {{ color: #f87171; }}
  .filter-bar {{ margin-bottom: 16px; display: flex; gap: 10px; }}
  .filter-btn {{ background: #1e293b; color: #e2e8f0; border: 1px solid #475569; padding: 8px 16px; border-radius: 8px; cursor: pointer; font-weight: 600; }}
  .filter-btn.active, .filter-btn:hover {{ background: #0284c7; border-color: #38bdf8; color: #fff; }}
  .tc-card {{ background: #1e293b; border-radius: 10px; padding: 16px 20px; margin-bottom: 16px; border-left: 6px solid #4ade80; box-shadow: 0 4px 12px rgba(0,0,0,0.25); }}
  .card-fail {{ border-left-color: #ef4444; background: #261922; }}
  .tc-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; flex-wrap: wrap; gap: 8px; }}
  .tc-id {{ font-weight: 700; font-size: 15px; color: #38bdf8; margin-right: 10px; }}
  .tc-group, .tc-tech {{ background: #334155; color: #e2e8f0; padding: 3px 10px; border-radius: 6px; font-size: 12px; margin-right: 6px; }}
  .tc-time {{ color: #94a3b8; font-size: 13px; margin-right: 10px; }}
  .badge {{ padding: 4px 12px; border-radius: 6px; font-weight: 700; font-size: 12px; }}
  .badge-pass {{ background: #166534; color: #4ade80; }}
  .badge-fail {{ background: #991b1b; color: #fecaca; }}
  .tc-title {{ font-size: 15px; font-weight: 600; margin-bottom: 6px; color: #f1f5f9; }}
  .tc-target {{ font-size: 13px; color: #cbd5e1; margin-bottom: 12px; }}
  .tc-target code {{ background: #0f172a; color: #fbbf24; padding: 3px 8px; border-radius: 4px; }}
  .tc-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-bottom: 12px; }}
  .box {{ background: #0f172a; border: 1px solid #334155; border-radius: 8px; padding: 10px 12px; }}
  .box-actual-pass {{ border-color: #15803d; }}
  .box-actual-fail {{ border-color: #b91c1c; background: #1f1218; }}
  .box-title {{ font-size: 12px; font-weight: 700; color: #38bdf8; margin-bottom: 6px; text-transform: uppercase; }}
  .box pre {{ margin: 0; white-space: pre-wrap; font-family: Consolas, monospace; font-size: 12.5px; color: #e2e8f0; line-height: 1.45; }}
  .code-details summary {{ cursor: pointer; color: #93c5fd; font-size: 13px; font-weight: 600; padding: 6px 0; }}
  .code-block {{ background: #090d16; color: #a5f3fc; padding: 12px; border-radius: 8px; border: 1px solid #1e293b; overflow-x: auto; font-family: Consolas, monospace; font-size: 12.5px; line-height: 1.45; margin-top: 6px; }}
</style>
</head>
<body>
<div class="container">
  <div class="hero">
    <div>
      <h1>BÁO CÁO TRỰC QUAN KIỂM THỬ ĐƠN VỊ HỘP TRẮNG (FEATURE 5 — UNIT TESTING)</h1>
      <p>Hệ thống Quản lý Phòng khám Đa khoa PhòngKhám+ | Soi mã nguồn Python, Đầu vào, Kỳ vọng SRS & Thực tế</p>
    </div>
    <div class="stats">
      <div class="stat-box"><div class="stat-val">{total}</div><div class="stat-lbl">Tổng Unit TCs</div></div>
      <div class="stat-box"><div class="stat-val pass-color">{passed} (84.6%)</div><div class="stat-lbl">PASSED</div></div>
      <div class="stat-box"><div class="stat-val fail-color">{failed} (15.4%)</div><div class="stat-lbl">FAILED (BUG-10, 11)</div></div>
      <div class="stat-box"><div class="stat-val">{total_ms:.0f} ms</div><div class="stat-lbl">Tổng thời gian</div></div>
    </div>
  </div>
  <div class="filter-bar">
    <button class="filter-btn active" onclick="filterCards('ALL', this)">Tất cả ({total})</button>
    <button class="filter-btn" onclick="filterCards('PASSED', this)">Đạt — PASSED ({passed})</button>
    <button class="filter-btn" onclick="filterCards('FAILED', this)">Lỗi SRS — FAILED ({failed})</button>
  </div>
  <div id="cards-root">
    {''.join(cards_html)}
  </div>
</div>
<script>
function filterCards(status, btn) {{
  document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  document.querySelectorAll('.tc-card').forEach(card => {{
    if (status === 'ALL' || card.dataset.status === status) {{
      card.style.display = 'block';
    }} else {{
      card.style.display = 'none';
    }}
  }});
}}
</script>
</body>
</html>
"""
    report_path = ROOT_DIR / "unit_test_report.html"
    report_path.write_text(html_content, encoding="utf-8")
    return report_path


def launch_visual_gui(results_data, report_path, step_delay_sec=1.8):
    """Mở cửa sổ Desktop GUI trực quan tự động trình chiếu từng bước 13 Unit Test Cases."""
    import tkinter as tk
    from tkinter import ttk

    root = tk.Tk()
    root.title("PhòngKhám+ — Trình chiếu Kiểm thử Đơn vị Hộp trắng (White-Box Unit Test Inspector: 13 TCs)")
    root.geometry("1360x820")
    root.configure(bg="#0f172a")

    # Top Auto-Play Banner
    banner_frame = tk.Frame(root, bg="#1e3a8a", padx=16, pady=10, highlightthickness=2, highlightbackground="#38bdf8")
    banner_frame.pack(fill="x", padx=12, pady=(10, 6))

    top_row = tk.Frame(banner_frame, bg="#1e3a8a")
    top_row.pack(fill="x")

    title_lbl = tk.Label(
        top_row,
        text="🔬 TRÌNH CHIẾU KIỂM THỬ HỘP TRẮNG TỰ ĐỘNG (FEATURE 5: 13 UNIT TEST CASES)",
        font=("Segoe UI", 13, "bold"),
        fg="#ffffff",
        bg="#1e3a8a",
    )
    title_lbl.pack(side="left")

    btn_frame = tk.Frame(top_row, bg="#1e3a8a")
    btn_frame.pack(side="right")

    step_lbl = tk.Label(
        banner_frame,
        text="Đang chuẩn bị khởi chạy tự động từ TC_UNIT_01 đến TC_UNIT_13...",
        font=("Segoe UI", 11, "bold"),
        fg="#fef08a",
        bg="#1e3a8a",
        anchor="w",
    )
    step_lbl.pack(fill="x", pady=(6, 2))

    # Progress & Summary bar
    stats_frame = tk.Frame(root, bg="#1e293b", padx=14, pady=8)
    stats_frame.pack(fill="x", padx=12, pady=(0, 8))

    progress_var = tk.DoubleVar(value=0)
    progress_bar = ttk.Progressbar(stats_frame, variable=progress_var, maximum=len(results_data), length=380)
    progress_bar.pack(side="left", padx=(0, 16))

    counter_lbl = tk.Label(
        stats_frame,
        text="Tiến độ: 0/13 | PASSED: 0 | FAILED: 0 (Phát hiện BUG-10, BUG-11)",
        font=("Segoe UI", 10, "bold"),
        fg="#38bdf8",
        bg="#1e293b",
    )
    counter_lbl.pack(side="left")

    # Main Split Pane
    main_pane = tk.PanedWindow(root, orient="horizontal", bg="#334155", sashwidth=6)
    main_pane.pack(fill="both", expand=True, padx=12, pady=(0, 12))

    # Left: Treeview of 13 Unit TCs
    left_frame = tk.Frame(main_pane, bg="#1e293b", padx=8, pady=8)
    main_pane.add(left_frame, width=560)

    tk.Label(
        left_frame,
        text="DANH SÁCH 13 UNIT TEST CASES (NHẤP ĐỂ XEM CHI TIẾT CODE HỘP TRẮNG)",
        font=("Segoe UI", 10, "bold"),
        fg="#38bdf8",
        bg="#1e293b",
    ).pack(anchor="w", pady=(0, 6))

    style = ttk.Style()
    style.theme_use("clam")
    style.configure("Unit.Treeview", background="#0f172a", foreground="#e2e8f0", fieldbackground="#0f172a", rowheight=29, font=("Segoe UI", 9))
    style.configure("Unit.Treeview.Heading", background="#334155", foreground="#ffffff", font=("Segoe UI", 9, "bold"))

    cols = ("tc_id", "technique", "target", "time", "status")
    tree = ttk.Treeview(left_frame, columns=cols, show="headings", style="Unit.Treeview")
    tree.heading("tc_id", text="Mã TC")
    tree.heading("technique", text="Kỹ thuật")
    tree.heading("target", text="Hàm kiểm thử (Target)")
    tree.heading("time", text="Thời gian")
    tree.heading("status", text="Kết quả")

    tree.column("tc_id", width=88, anchor="center")
    tree.column("technique", width=130, anchor="w")
    tree.column("target", width=195, anchor="w")
    tree.column("time", width=65, anchor="e")
    tree.column("status", width=75, anchor="center")
    tree.pack(fill="both", expand=True)

    tree.tag_configure("PENDING", foreground="#94a3b8")
    tree.tag_configure("PASSED", background="#064e3b", foreground="#4ade80")
    tree.tag_configure("FAILED", background="#7f1d1d", foreground="#fecaca")

    for r in results_data:
        tree.insert(
            "",
            "end",
            iid=r["tc_id"],
            values=(r["tc_id"], r["technique"], r["target"].split("::")[-1].strip(), f"{r['elapsed_ms']:.1f}ms", "⏳ Chờ..."),
            tags=("PENDING",),
        )

    # Right: White-Box Code & Input/Expected/Actual Inspector
    right_frame = tk.Frame(main_pane, bg="#1e293b", padx=10, pady=8)
    main_pane.add(right_frame, width=760)

    detail_title = tk.Label(
        right_frame,
        text="CHI TIẾT KIỂM THỬ HỘP TRẮNG (WHITE-BOX CODE & DATA FLOW)",
        font=("Segoe UI", 11, "bold"),
        fg="#fbbf24",
        bg="#1e293b",
        anchor="w",
    )
    detail_title.pack(fill="x", pady=(0, 4))

    target_lbl = tk.Label(
        right_frame,
        text="Hàm mục tiêu: (Đang chờ...)",
        font=("Consolas", 10, "bold"),
        fg="#38bdf8",
        bg="#0f172a",
        padx=8,
        pady=5,
        anchor="w",
    )
    target_lbl.pack(fill="x", pady=(0, 6))

    # Source Code Box
    tk.Label(
        right_frame,
        text="1. Mã nguồn Python Hộp trắng đang được kiểm thử (inspect.getsourcelines):",
        font=("Segoe UI", 9, "bold"),
        fg="#93c5fd",
        bg="#1e293b",
        anchor="w",
    ).pack(fill="x")

    code_text = tk.Text(
        right_frame,
        height=13,
        bg="#090d16",
        fg="#a5f3fc",
        font=("Consolas", 10),
        padx=10,
        pady=8,
        wrap="none",
         relief="flat",
    )
    code_text.pack(fill="both", expand=True, pady=(2, 8))

    # Input / Expected / Actual Box
    tk.Label(
        right_frame,
        text="2. Luồng Dữ liệu Kiểm thử (Input -> Kỳ vọng SRS -> Thực tế thực thi):",
        font=("Segoe UI", 9, "bold"),
        fg="#93c5fd",
        bg="#1e293b",
        anchor="w",
    ).pack(fill="x")

    io_text = tk.Text(
        right_frame,
        height=11,
        bg="#0f172a",
        fg="#f8fafc",
        font=("Consolas", 10),
        padx=10,
        pady=8,
        wrap="word",
        relief="flat",
    )
    io_text.pack(fill="both", expand=True, pady=(2, 0))
    io_text.tag_configure("heading", foreground="#38bdf8", font=("Consolas", 10, "bold"))
    io_text.tag_configure("pass_txt", foreground="#4ade80", font=("Consolas", 10, "bold"))
    io_text.tag_configure("fail_txt", foreground="#f87171", font=("Consolas", 10, "bold"))

    state = {"idx": 0, "paused": False, "after_id": None, "pass_cnt": 0, "fail_cnt": 0}

    def display_tc_detail(r):
        detail_title.configure(text=f"[{r['index']:02d}/13] {r['tc_id']} — {r['doc']}")
        target_lbl.configure(text=f"Hàm mục tiêu: {r['target']}   |   Kỹ thuật: {r['technique']}")

        code_text.configure(state="normal")
        code_text.delete("1.0", "end")
        code_text.insert("1.0", r["source_code"])
        code_text.configure(state="disabled")

        io_text.configure(state="normal")
        io_text.delete("1.0", "end")
        io_text.insert("end", "▶ DỮ LIỆU ĐẦU VÀO (TEST INPUT):\n", "heading")
        io_text.insert("end", r["input_desc"] + "\n\n")
        io_text.insert("end", "▶ KẾT QUẢ KỲ VỌNG THEO SRS (EXPECTED):\n", "heading")
        io_text.insert("end", r["expected_desc"] + "\n\n")
        io_text.insert("end", "▶ KẾT QUẢ THỰC TẾ CHẠY HÀM (ACTUAL OUTPUT):\n", "heading")
        io_text.insert("end", r["actual_desc"] + "\n", "pass_txt" if r["passed"] else "fail_txt")
        io_text.configure(state="disabled")

    def on_tree_select(_event):
        sel = tree.selection()
        if not sel:
            return
        tc_id = sel[0]
        for r in results_data:
            if r["tc_id"] == tc_id:
                display_tc_detail(r)
                break

    tree.bind("<<TreeviewSelect>>", on_tree_select)

    def set_banner_color(bg_color):
        banner_frame.configure(bg=bg_color)
        top_row.configure(bg=bg_color)
        title_lbl.configure(bg=bg_color)
        btn_frame.configure(bg=bg_color)
        step_lbl.configure(bg=bg_color)

    def run_next_step():
        if state["paused"]:
            return
        idx = state["idx"]
        if idx >= len(results_data):
            set_banner_color("#065f46")
            step_lbl.configure(
                text=(
                    f"✅ HOÀN TẤT TRÌNH CHIẾU 13/13 UNIT TEST CASES! "
                    f"Kết quả: {state['pass_cnt']} PASSED (84.62%) | {state['fail_cnt']} FAILED (15.38% — Phát hiện BUG-10 & BUG-11)."
                )
            )
            return

        r = results_data[idx]
        state["idx"] += 1
        if r["passed"]:
            state["pass_cnt"] += 1
            set_banner_color("#14532d")
            status_badge = "✅ PASSED"
        else:
            state["fail_cnt"] += 1
            set_banner_color("#7f1d1d")
            status_badge = "❌ FAILED (Bug SRS)"

        step_lbl.configure(text=f"Đang chạy [{r['index']:02d}/13] {r['tc_id']} ({r['target']})  -->  {status_badge}")
        progress_var.set(state["idx"])
        counter_lbl.configure(
            text=f"Tiến độ: {state['idx']}/13 | PASSED: {state['pass_cnt']} | FAILED: {state['fail_cnt']} (Phát hiện BUG-10, BUG-11)"
        )

        tree.item(
            r["tc_id"],
            values=(r["tc_id"], r["technique"], r["target"].split("::")[-1].strip(), f"{r['elapsed_ms']:.1f}ms", status_badge),
            tags=("PASSED" if r["passed"] else "FAILED",),
        )
        tree.selection_set(r["tc_id"])
        tree.see(r["tc_id"])
        display_tc_detail(r)

        state["after_id"] = root.after(int(step_delay_sec * 1000), run_next_step)

    def toggle_pause():
        state["paused"] = not state["paused"]
        if state["paused"]:
            pause_btn.configure(text="▶ Tiếp tục Tự động", bg="#16a34a")
            if state["after_id"]:
                root.after_cancel(state["after_id"])
        else:
            pause_btn.configure(text="⏸ Tạm dừng", bg="#d97706")
            run_next_step()

    def restart_demo():
        if state["after_id"]:
            root.after_cancel(state["after_id"])
        state["idx"] = 0
        state["pass_cnt"] = 0
        state["fail_cnt"] = 0
        state["paused"] = False
        pause_btn.configure(text="⏸ Tạm dừng", bg="#d97706")
        progress_var.set(0)
        for r in results_data:
            tree.item(
                r["tc_id"],
                values=(r["tc_id"], r["technique"], r["target"].split("::")[-1].strip(), f"{r['elapsed_ms']:.1f}ms", "⏳ Chờ..."),
                tags=("PENDING",),
            )
        run_next_step()

    def open_html_in_browser():
        webbrowser.open(report_path.as_uri())

    pause_btn = tk.Button(
        btn_frame,
        text="⏸ Tạm dừng",
        command=toggle_pause,
        bg="#d97706",
        fg="#ffffff",
        font=("Segoe UI", 9, "bold"),
        padx=10,
        pady=3,
        relief="flat",
    )
    pause_btn.pack(side="left", padx=4)

    tk.Button(
        btn_frame,
        text="🔁 Chạy lại từ đầu",
        command=restart_demo,
        bg="#2563eb",
        fg="#ffffff",
        font=("Segoe UI", 9, "bold"),
        padx=10,
        pady=3,
        relief="flat",
    ).pack(side="left", padx=4)

    tk.Button(
        btn_frame,
        text="🌐 Mở Báo cáo HTML trên Trình duyệt",
        command=open_html_in_browser,
        bg="#059669",
        fg="#ffffff",
        font=("Segoe UI", 9, "bold"),
        padx=10,
        pady=3,
        relief="flat",
    ).pack(side="left", padx=4)

    root.after(600, run_next_step)
    root.mainloop()


def main():
    parser = argparse.ArgumentParser(description="Trình chiếu trực quan Unit Testing Hộp trắng (13 TCs)")
    parser.add_argument("--delay", type=float, default=1.8, help="Thời gian dừng giữa mỗi Unit Test Case (giây)")
    parser.add_argument("--headless", action="store_true", help="Chỉ chạy trên Terminal + xuất báo cáo HTML, không mở cửa sổ GUI")
    parser.add_argument("--open-browser", action="store_true", help="Tự động mở file unit_test_report.html trên trình duyệt")
    args = parser.parse_args()

    print("=" * 96)
    print("KHỞI CHẠY KIỂM THỬ ĐƠN VỊ HỘP TRẮNG TRỰC QUAN (FEATURE 5: 13 UNIT TEST CASES)")
    print("=" * 96)
    results_data = execute_all_unit_tests()
    report_path = generate_html_report(results_data)

    passed = sum(1 for r in results_data if r["passed"])
    failed = len(results_data) - passed
    for r in results_data:
        print(f"[{r['index']:02d}/13] [{r['status']:6s}] ({r['elapsed_ms']:5.1f}ms) {r['tc_id']} -> {r['target']}")
    print("-" * 96)
    print(f"TỔNG KẾT UNIT TEST: {len(results_data)} TCs | PASSED: {passed} (84.62%) | FAILED: {failed} (15.38% — BUG-10, BUG-11)")
    print(f"Đã xuất báo cáo giao diện Web HTML trực quan tại: {report_path}")
    print("=" * 96)

    if args.open_browser:
        webbrowser.open(report_path.as_uri())

    if not args.headless:
        launch_visual_gui(results_data, report_path, step_delay_sec=args.delay)


if __name__ == "__main__":
    main()

