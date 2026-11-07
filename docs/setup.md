# ⚙️ Hướng dẫn Thiết lập & Cấu hình Hệ thống PhòngKhám+

Tài liệu này cung cấp hướng dẫn chi tiết từng bước để cài đặt, cấu hình các dịch vụ phụ trợ, thiết lập cơ sở dữ liệu và vận hành hệ thống **PhòngKhám+** trên môi trường cục bộ (Local Development) cũng như mạng nội bộ (LAN).

---

## 📋 1. Yêu cầu Hệ thống & Tiền đề (Prerequisites)

Trước khi tiến hành cài đặt, hãy đảm bảo hệ thống của bạn đáp ứng các yêu cầu sau:

*   **Hệ điều hành:** Windows 10/11 hoặc Linux (Ubuntu 20.04 LTS trở lên).
*   **Python:** Phiên bản **3.10** hoặc **3.11** (khuyến cáo để tương thích tối đa với Django 4.2 & Channels).
*   **MySQL Server:** Phiên bản **8.0** trở lên.
*   **Redis Server:** Phiên bản **5.0** trở lên (bắt buộc để chạy WebSockets chat thời gian thực và quản lý hàng chờ nhiệm vụ Celery).
*   **Trình duyệt web:** Google Chrome, Microsoft Edge, Mozilla Firefox phiên bản mới nhất.

---

## 🛠️ 2. Hướng dẫn Cài đặt các Dịch vụ Phụ trợ

### 2.1 Cài đặt & Khởi chạy Redis Server
Hệ thống sử dụng Redis làm **Channel Layer** cho WebSockets (thông qua Django Channels) và làm **Message Broker** cho Celery.

*   **Trên Linux (Ubuntu):**
    ```bash
    sudo apt update
    sudo apt install redis-server -y
    sudo systemctl enable redis-server.service
    sudo systemctl start redis-server.service
    # Kiểm tra trạng thái hoạt động
    redis-cli ping
    # Kết quả trả về "PONG" là thành công
    ```

*   **Trên Windows:**
    1.  Tải xuống bản phân phối Redis dành cho Windows (Khuyến nghị dùng bản cài đặt MSI qua Archive GitHub hoặc chạy thông qua **WSL - Windows Subsystem for Linux**).
    2.  Nếu dùng WSL, khởi động bằng lệnh: `sudo service redis-server start`
    3.  Đảm bảo cổng mặc định `6379` đang được lắng nghe.

### 2.2 Cài đặt & Thiết lập CSDL MySQL
1.  Cài đặt **MySQL Community Server** qua bộ cài đặt chính thức.
2.  Khởi động dịch vụ MySQL và truy cập vào MySQL CLI:
    ```sql
    mysql -u root -p
    ```
3.  Tạo cơ sở dữ liệu trống có tên `phongkham` hỗ trợ hiển thị Tiếng Việt đầy đủ (bảng mã `utf8mb4`):
    ```sql
    CREATE DATABASE IF NOT EXISTS phongkham 
    CHARACTER SET utf8mb4 
    COLLATE utf8mb4_unicode_ci;
    ```

---

## 💻 3. Thiết lập Mã nguồn & Môi trường Python

### 3.1 Khởi tạo Môi trường ảo (Virtual Environment)
Mở cửa sổ Command Prompt/PowerShell (Windows) hoặc Terminal (Linux) tại thư mục gốc của dự án `Maneger-Medical-System`:

```bash
# Tạo môi trường ảo venv
python -m venv venv

# Kích hoạt môi trường ảo:
# Trên Windows (PowerShell):
venv\Scripts\Activate.ps1
# Trên Windows (CMD):
venv\Scripts\activate.bat
# Trên Linux/macOS:
source venv/bin/activate
```

### 3.2 Cài đặt Dependencies
Cài đặt tất cả các thư viện Python cần thiết được liệt kê trong tệp [requirements.txt](file:///c:/Users/Admin/OneDrive%20-%20The%20University%20of%20Technology/K%C3%AC%206/PBL5/Maneger-Medical-System/requirements.txt):

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

---

## ⚙️ 4. Cấu hình tệp biến môi trường (`.env`)

Di chuyển vào thư mục [be/](file:///c:/Users/Admin/OneDrive%20-%20The%20University%20of%20Technology/K%C3%AC%206/PBL5/Maneger-Medical-System/be), sao chép tệp mẫu cấu hình:

```bash
cd be
copy .env.example .env   # Trên Windows
cp .env.example .env     # Trên Linux
```

Mở tệp `.env` vừa tạo và chỉnh sửa các giá trị cho khớp với môi trường của bạn:

```ini
# --- BẢO MẬT & DEBUG DJANGO ---
DJANGO_SECRET_KEY=django-insecure-your-secret-key-here
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1

# --- CẤU HÌNH CƠ SỞ DỮ LIỆU MYSQL ---
DB_ENGINE=django.db.backends.mysql
DB_NAME=phongkham
DB_USER=root
DB_PASSWORD=your_mysql_password_here
DB_HOST=127.0.0.1
DB_PORT=3306

# --- CẤU HÌNH BẢO MẬT GIAO DIỆN (CORS & CSRF) ---
# Điền IP của Server và các URL Client được phép kết nối để tránh lỗi bảo mật
DJANGO_CSRF_TRUSTED_ORIGINS=http://localhost:8000,http://127.0.0.1:8000
DJANGO_CORS_ALLOWED_ORIGINS=http://localhost:8000,http://127.0.0.1:8000,http://localhost:8080

# --- CỐNG THANH TOÁN ONLINE VNPAY (SANDBOX) ---
VNPAY_TMN_CODE=your_tmn_code
VNPAY_HASH_SECRET=your_hash_secret
VNPAY_PAYMENT_URL=https://sandbox.vnpayment.vn/paymentv2/vpcpay.html
VNPAY_RETURN_URL=http://127.0.0.1:8000/payment/vnpay-return
VNPAY_IPN_URL=http://127.0.0.1:8000/api/don-hang/vnpay-ipn/

# --- HỆ THỐNG TIN NHẮN SMS (eSMS.vn) ---
SMS_ENABLED=false
SMS_API_KEY=your_api_key
SMS_SECRET_KEY=your_secret_key
SMS_BRAND_NAME=PhongKham
```

---

## 🗄️ 5. Đồng bộ Cơ sở dữ liệu & Tạo Tài khoản

Sau khi đã điền thông tin kết nối MySQL chính xác trong tệp `.env`, hãy tiến hành khởi tạo cấu trúc bảng (Schema):

```bash
# Đảm bảo đang ở thư mục be/ có tệp manage.py
python manage.py showmigrations   # Kiểm tra danh sách migration
python manage.py migrate          # Tạo bảng và liên kết trên MySQL
```

Tiếp tục tạo tài khoản quản trị tối cao (Admin) để đăng nhập cấu hình dữ liệu ban đầu:

```bash
python manage.py createsuperuser
```
Hệ thống sẽ yêu cầu nhập:
*   `Tên đăng nhập` (Ví dụ: `admin`)
*   `Địa chỉ email` (Ví dụ: `admin@phongkham.com`)
*   `Mật khẩu` (nhập 2 lần, mật khẩu sẽ không hiển thị trên màn hình khi gõ).

---

## 🚀 6. Khởi chạy Ứng dụng

Hệ thống sử dụng các phân hệ chạy ngầm phục vụ cả kết nối HTTP thông thường, WebSockets (cho Chat) và các tác vụ tính toán gửi tin ngầm. Hãy chạy các dịch vụ sau:

### 6.1 Khởi chạy Web Server

*   **Cách 1: Chạy Chế độ Phát triển (Development Mode):**
    ```bash
    python manage.py runserver
    ```
    *Lưu ý: Mặc dù `runserver` hỗ trợ reload nhanh khi thay đổi code, tuy nhiên nó không được tối ưu để xử lý mượt mà kết nối WebSockets thời gian thực.*

*   **Cách 2: Chạy Môi trường Chuẩn (ASGI Daphne Server):**
    Sử dụng máy chủ ASGI **Daphne** (bản chạy chính thức được tích hợp trong dự án):
    ```bash
    daphne -b 127.0.0.1 -p 8000 phongkham.asgi:application
    ```
    *Daphne sẽ tự động điều phối cả kết nối HTTP và WebSockets một cách đồng thời và bảo mật.*

*   **Cách 3: Chạy trên mạng nội bộ LAN (chỉ dành cho Windows):**
    Chạy trực tiếp tệp script batch:
    ```bash
    start_lan_server.bat 0.0.0.0 8000
    ```
    Script này sẽ tự động chạy lệnh thu thập file tĩnh giao diện (`collectstatic`) vào thư mục `staticfiles` rồi chạy Daphne.

### 6.2 Khởi chạy Hàng chờ Task ngầm (Celery)
Mở thêm một cửa sổ Terminal mới (đã kích hoạt môi trường ảo `venv` và đang ở thư mục `be/`):

1.  **Chạy Worker xử lý tác vụ ngầm (SMS, Email thông báo, tính doanh số):**
    ```bash
    celery -A phongkham worker --loglevel=info
    ```
2.  **Chạy Beat điều phối lịch gửi định kỳ (Ví dụ: Tự động nhắc nhở lịch khám trước 1 ngày):**
    ```bash
    celery -A phongkham beat --loglevel=info
    ```

---

## 🔍 7. Kiểm tra & Bàn giao Hệ thống

Sau khi khởi chạy đầy đủ các dịch vụ, hãy thực hiện kiểm tra nhanh:

1.  **Giao diện SPA:** Mở trình duyệt và truy cập `http://127.0.0.1:8000/login/` để kiểm tra màn hình đăng nhập sáng/tối.
2.  **Trang Quản trị Admin:** Truy cập `http://127.0.0.1:8000/admin/` bằng tài khoản superuser vừa tạo. Tiến hành:
    *   Tạo người dùng mới và chỉ định vai trò (`BENH_NHAN`, `BAC_SI`, `NHAN_VIEN`).
    *   Tạo thông tin chi tiết tương ứng trong các bảng liên kết `benh_nhan`, `bac_si`, hoặc `nhan_vien` (chọn chức vụ Lễ tân, Bán thuốc, Kho, hay Kế toán).
3.  **Tài liệu API (Interactive API Docs):** Truy cập `http://127.0.0.1:8000/api/docs/` để xem danh sách toàn bộ các API Endpoints và thực hiện gọi thử trực tiếp bằng Swagger UI.
