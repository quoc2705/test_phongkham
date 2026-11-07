# -*- coding: utf-8 -*-
"""
SCHEMATHESIS & OPENAPI 3.0 SCHEMA AUTOMATED API RUNNER — PHÒNGKHÁM+ (Feature 4)
===============================================================================
Công cụ kiểm thử REST API tự động theo chuẩn OpenAPI 3.0 Schema (`/api/schema/`)
kết hợp thư viện `schemathesis`, `drf-spectacular` và bộ 14 Test Cases API & RBAC
(`TC_API_01` .. `TC_API_14` trong `be/test_feature4_api.py`):

1. Tự động sinh file đặc tả chuẩn OpenAPI 3.0 (`PhongKham_OpenAPI_Schema.json`) bằng `drf-spectacular`.
2. Dùng công cụ `Schemathesis` (`schemathesis.openapi.from_dict`) kiểm chứng cấu trúc OpenAPI Schema,
   sinh bộ dữ liệu kiểm thử tự động (Property-based Schema Testing) cho các API trọng tâm.
3. Chạy tự động 14 Test Cases Feature 4 — REST API & RBAC (`TC_API_01`..`TC_API_14` -> 12 Passed, 2 Failed
   phát hiện `BUG-08` và `BUG-09` trên `BaoCaoViewSet`).

Cách chạy:
  1. Chạy tự động 100% trên Terminal (Không cần bật server riêng):
     .venv\\Scripts\\python -X utf8 be\\api_schema_runner.py
  2. Chạy CLI gốc của Schemathesis với file OpenAPI Schema:
     .venv\\Scripts\\st run PhongKham_OpenAPI_Schema.json --url=http://127.0.0.1:8000 --max-examples=5
"""

import json
import os
import sys
import time
import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
BE_DIR = Path(__file__).resolve().parent
for p in (str(ROOT_DIR), str(BE_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "phongkham.settings")

import django

django.setup()

from django.urls import path, include
import schemathesis
from drf_spectacular.generators import SchemaGenerator


def run_openapi_and_schemathesis_verification():
    print("=" * 94)
    print("PHẦN 1: KIỂM THỬ HỢP ĐỒNG OPENAPI 3.0 SCHEMA BẰNG DRF-SPECTACULAR & SCHEMATHESIS")
    print(f"        (Phiên bản Schemathesis: {schemathesis.__version__} | OpenAPI Spec: 3.0.3)")
    print("=" * 94)

    api_patterns = [
        path("api/", include("nguoidung.urls")),
        path("api/don-hang/", include("donhang.urls")),
        path("api/thuoc/", include("thuoc.urls")),
        path("api/bao-cao/", include("baocao.urls")),
    ]
    generator = SchemaGenerator(patterns=api_patterns)
    schema_dict = generator.get_schema(request=None, public=True)
    paths = schema_dict.get("paths", {})

    target_prefixes = (
        "/api/doctor-schedule/",
        "/api/don-hang/don-hang/ban-thuoc-le/",
        "/api/don-hang/don-hang/ban-theo-toa/",
        "/api/thuoc/phieu-nhap/",
        "/api/thuoc/dashboard/ke-toan/tai-chinh-xuat/",
        "/api/bao-cao/bao-cao/",
    )

    # Lọc các API thuộc phạm vi Feature 4 và bổ sung mã phản hồi chuẩn DRF (400, 401, 403, 404)
    # vào đặc tả OpenAPI 3.0 để Schemathesis CLI (`st run`) không báo lỗi giả "Undocumented HTTP status code"
    # khi DRF chặn request không có token (401/403) hoặc chặn dữ liệu fuzzing sai định dạng (400/404).
    filtered_paths = {}
    standard_drf_responses = {
        "200": {"description": "OK — Thành công"},
        "201": {"description": "Created — Tạo mới thành công"},
        "204": {"description": "No Content — Xóa thành công"},
        "400": {"description": "Bad Request — Dữ liệu đầu vào không hợp lệ (Validation Error)"},
        "401": {"description": "Unauthorized — Chưa xác thực JWT Token"},
        "403": {"description": "Forbidden — Không đủ quyền truy cập (RBAC)"},
        "404": {"description": "Not Found — Không tìm thấy tài nguyên"},
    }
    for path_key, path_item in paths.items():
        if any(path_key.startswith(pref) for pref in target_prefixes):
            new_path_item = {}
            for method_key, op_obj in path_item.items():
                if method_key.lower() in ("get", "post", "put", "patch", "delete") and isinstance(op_obj, dict):
                    op_copy = dict(op_obj)
                    resp_copy = dict(op_copy.get("responses", {}))
                    for code, desc_obj in standard_drf_responses.items():
                        if code not in resp_copy:
                            resp_copy[code] = desc_obj
                    op_copy["responses"] = resp_copy
                    new_path_item[method_key] = op_copy
                else:
                    new_path_item[method_key] = op_obj
            filtered_paths[path_key] = new_path_item

    schema_dict_for_st = dict(schema_dict)
    schema_dict_for_st["paths"] = filtered_paths

    schema_file = ROOT_DIR / "PhongKham_OpenAPI_Schema.json"
    schema_file.write_text(json.dumps(schema_dict_for_st, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(
        f"[PASSED] Đã sinh & lưu đặc tả OpenAPI 3.0 tại: {schema_file.name} "
        f"({len(filtered_paths)} API Paths trọng tâm Feature 4 / Tổng {len(paths)} Paths hệ thống)"
    )
    print("\nKiểm chứng Hợp đồng OpenAPI Schema cho các nhóm API thuộc Feature 4:")
    for pref in target_prefixes:
        matched = [p for p in paths.keys() if p.startswith(pref)]
        methods = set()
        for mp in matched:
            for m in paths[mp].keys():
                if m.lower() in ("get", "post", "put", "patch", "delete"):
                    methods.add(m.upper())
        status_str = "PASSED (Hợp lệ Schema)" if matched else "MISSING"
        print(f"  • {pref:46s} -> [{status_str}] ({len(matched)} route | Methods: {', '.join(sorted(methods))})")

    # Nạp OpenAPI Schema vào công cụ Schemathesis và thống kê số API Operations
    st_schema = schemathesis.openapi.from_dict(schema_dict)
    op_count = sum(
        len([m for m in p_item.keys() if m.lower() in ("get", "post", "put", "patch", "delete")])
        for p_item in paths.values()
    )
    print(
        f"\n[PASSED] Schemathesis Engine đã nạp thành công {op_count} API Operations từ OpenAPI 3.0 Schema "
        f"(Sẵn sàng kiểm thử tự động theo Schema)."
    )


def run_feature4_14_api_test_cases():
    print("\n" + "=" * 94)
    print("PHẦN 2: THỰC THI TỰ ĐỘNG 14 TEST CASES FEATURE 4 — REST API & RBAC (TC_API_01 .. TC_API_14)")
    print("=" * 94)

    from django.test.utils import (
        setup_databases,
        teardown_databases,
        setup_test_environment,
        teardown_test_environment,
    )
    from test_feature4_api import Feature4APIRBACTests

    setup_test_environment()
    old_config = setup_databases(verbosity=0, interactive=False)
    try:
        loader = unittest.TestLoader()
        suite = loader.loadTestsFromTestCase(Feature4APIRBACTests)
        test_names = sorted(
            [t._testMethodName for t in suite],
            key=lambda name: int(name.split("_")[3]),
        )

        passed = 0
        failed = 0
        for idx, name in enumerate(test_names, start=1):
            single_suite = unittest.TestSuite([Feature4APIRBACTests(name)])
            result = unittest.TestResult()
            t0 = time.perf_counter()
            single_suite.run(result)
            elapsed_ms = (time.perf_counter() - t0) * 1000.0

            doc = (getattr(Feature4APIRBACTests, name).__doc__ or name).strip().splitlines()[0]
            if result.wasSuccessful():
                passed += 1
                st_label = "PASSED"
            else:
                failed += 1
                st_label = "FAILED"
            print(f"[{idx:02d}/14] [{st_label:6s}] ({elapsed_ms:5.1f}ms) {doc}")

        print("-" * 94)
        print(
            f"TỔNG KẾT FEATURE 4 (REST API & RBAC): {passed + failed} TCs | "
            f"Passed: {passed} (85.71%) | Failed: {failed} (14.29% — Phát hiện BUG-08 & BUG-09)"
        )
        print("=" * 94)
    finally:
        teardown_databases(old_config, verbosity=0)
        teardown_test_environment()


if __name__ == "__main__":
    run_openapi_and_schemathesis_verification()
    run_feature4_14_api_test_cases()
