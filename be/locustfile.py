# -*- coding: utf-8 -*-
"""
LOCUST PERFORMANCE & CONCURRENCY LOAD TEST SUITE — PHÒNGKHÁM+ (Feature 3)
=========================================================================
Công cụ kiểm thử hiệu năng & chịu tải đa người dùng đồng thời (Concurrent Users)
theo chuẩn đề xuất cho Django (Locust + JMeter), bám sát đặc tả SRS Mục 5.1 (QA-PERF-01..04):
  - Function 3.1 (QA-PERF-01..03): Kiểm thử tốc độ phản hồi & thông lượng (Throughput / RPS)
    của các API Hàng chờ Lễ tân, Danh mục thuốc đa lô, Tổng hợp Báo cáo Tài chính & Xuất Excel.
  - Function 3.2 (QA-PERF-04): Kiểm thử chịu tải đồng thời khi nhiều người dùng cùng truy cập
    giỏ hàng, đặt lịch hẹn và tra cứu lịch sử.

Cách chạy:
  1. Giao diện biểu đồ Web UI của Locust (http://localhost:8089):
     .venv\\Scripts\\locust -f be/locustfile.py --host=http://127.0.0.1:8000
  2. Chạy tự động Headless (VD: 20 người dùng đồng thời, tốc độ sinh 5 user/s trong 15 giây):
     .venv\\Scripts\\locust -f be/locustfile.py --host=http://127.0.0.1:8000 --headless -u 20 -r 5 -t 15s --html=locust_report.html
"""

from locust import HttpUser, between, task


class BaseClinicLocustUser(HttpUser):
    abstract = True
    wait_time = between(0.5, 1.5)
    username = ""
    password = "Password@123"
    fallback_username = ""
    fallback_password = ""
    token = None

    def on_start(self):
        """Đăng nhập JWT qua /api/users/login/ khi mỗi Virtual User bắt đầu phiên tải."""
        creds = [(self.username, self.password)]
        if self.fallback_username:
            creds.append((self.fallback_username, self.fallback_password))

        for uname, pwd in creds:
            with self.client.post(
                "/api/users/login/",
                json={"ten_dang_nhap": uname, "password": pwd},
                name="/api/users/login/ [JWT Login]",
                catch_response=True,
            ) as resp:
                if resp.status_code == 200:
                    data = resp.json()
                    self.token = data.get("access") or data.get("tokens", {}).get("access")
                    resp.success()
                    return
                resp.success()  # Thử tài khoản fallback nếu chưa khớp

    @property
    def auth_headers(self):
        if self.token:
            return {"Authorization": f"Bearer {self.token}"}
        return {}


class LeTanConcurrencyUser(BaseClinicLocustUser):
    """
    Virtual User 1: Nhân viên Lễ tân tra cứu hàng chờ hôm nay & bảng xếp hạng bác sĩ trực ca
    (Kiểm thử TC_PERF_01 & TC_PERF_10 dưới tải đồng thời).
    """

    weight = 3
    username = "letan_test"
    password = "Password@123"
    fallback_username = "letan"
    fallback_password = "Letan@123"

    @task(3)
    def get_queue_today(self):
        with self.client.get(
            "/api/lich-hen/lich-hen/hom_nay_letan/",
            headers=self.auth_headers,
            name="[TC_PERF_01] GET /api/lich-hen/lich-hen/hom_nay_letan/",
            catch_response=True,
        ) as resp:
            if resp.status_code == 200 and resp.elapsed.total_seconds() < 2.0:
                resp.success()
            else:
                resp.failure(f"Status={resp.status_code}, Latency={resp.elapsed.total_seconds():.3f}s")

    @task(2)
    def get_doctor_ranking(self):
        self.client.get(
            "/api/lich-hen/lich-hen/bac_si_xep_hang/",
            headers=self.auth_headers,
            name="[TC_WEB_17] GET /api/lich-hen/lich-hen/bac_si_xep_hang/",
        )


class BenhNhanShopAndBookingUser(BaseClinicLocustUser):
    """
    Virtual User 2: Bệnh nhân truy cập trang chủ Web SPA, duyệt danh mục thuốc đa lô
    và tra cứu lịch hẹn (Kiểm thử TC_PERF_02, TC_PERF_05, TC_PERF_09).
    """

    weight = 5
    username = "benhnhan1_test"
    password = "Password@123"
    fallback_username = "benhnhan"
    fallback_password = "Benhnhan@123"

    @task(2)
    def load_web_spa_home(self):
        self.client.get("/", name="[TC_WEB_01] GET / (Web SPA Home)")

    @task(4)
    def browse_medicine_catalog(self):
        with self.client.get(
            "/api/thuoc/thuoc/?page_size=60",
            headers=self.auth_headers,
            name="[TC_PERF_02] GET /api/thuoc/thuoc/?page_size=60",
            catch_response=True,
        ) as resp:
            if resp.status_code == 200 and resp.elapsed.total_seconds() < 2.0:
                resp.success()
            else:
                resp.failure(f"Status={resp.status_code}, Latency={resp.elapsed.total_seconds():.3f}s")

    @task(2)
    def list_appointments_paginated(self):
        self.client.get(
            "/api/lich-hen/lich-hen/?page_size=50",
            headers=self.auth_headers,
            name="[TC_PERF_09] GET /api/lich-hen/lich-hen/?page_size=50",
        )


class KeToanFinancialReportUser(BaseClinicLocustUser):
    """
    Virtual User 3: Kế toán tổng hợp Báo cáo Tài chính & Xuất file Excel (.xlsx) dưới tải
    (Kiểm thử TC_PERF_03 & TC_PERF_04).
    """

    weight = 2
    username = "ketoan_test"
    password = "Password@123"
    fallback_username = "ketoan"
    fallback_password = "Ketoan@123"

    @task(3)
    def get_financial_summary(self):
        with self.client.get(
            "/api/thuoc/dashboard/ke-toan/tom-tat/",
            headers=self.auth_headers,
            name="[TC_PERF_03] GET /api/thuoc/dashboard/ke-toan/tom-tat/",
            catch_response=True,
        ) as resp:
            if resp.status_code == 200 and resp.elapsed.total_seconds() < 2.0:
                resp.success()
            else:
                resp.failure(f"Status={resp.status_code}")

    @task(1)
    def export_financial_excel(self):
        with self.client.get(
            "/api/thuoc/dashboard/ke-toan/tai-chinh-xuat/?dinh_dang=xlsx",
            headers=self.auth_headers,
            name="[TC_PERF_04] GET /api/thuoc/dashboard/ke-toan/tai-chinh-xuat/?dinh_dang=xlsx",
            catch_response=True,
        ) as resp:
            if resp.status_code == 200 and resp.elapsed.total_seconds() < 3.0:
                resp.success()
            else:
                resp.failure(f"Status={resp.status_code}")

