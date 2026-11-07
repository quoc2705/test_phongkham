# Trien khai phongkham_system tren LAN (day du vai tro)

Tai lieu nay dung cho mo hinh 1 server trung tam + 2-3 may client trong cung LAN.
Client chi can trinh duyet, du lieu tap trung tren server.

## 1) Chuan bi server

- Dat IP tinh cho server, vi du: `192.168.1.10`
- Mo firewall cho cong web app (vi du `8000`) va cho phep truy cap trong LAN
- Cai MySQL va tao database `phongkham`
- Sao chep `be/.env.example` thanh `be/.env`, cap nhat:
  - `DJANGO_ALLOWED_HOSTS`: them IP server, vd `localhost,127.0.0.1,192.168.1.10`
  - `DJANGO_CSRF_TRUSTED_ORIGINS`: them `http://192.168.1.10:8000`
  - `DJANGO_CORS_ALLOWED_ORIGINS`: them `http://192.168.1.10:8000`
  - `DB_*`: dung thong tin MySQL that tren server

## 2) Cai dat backend va khoi tao he thong

Tu thu muc `be`:

- `python -m venv venv`
- `venv\Scripts\activate`
- `pip install -r ..\requirements.txt`
- `python manage.py migrate`
- `python manage.py createsuperuser`

## 3) Tao tai khoan cho day du vai tro

Dang nhap `http://192.168.1.10:8000/admin/` bang tai khoan superuser va tao user cho cac vai tro sau:

- Benh nhan (`BENH_NHAN`)
- Bac si (`BAC_SI`)
- Admin he thong (`ADMIN`)
- Nhan vien le tan (`NHAN_VIEN` + `LE_TAN`)
- Nhan vien ban thuoc (`NHAN_VIEN` + `BAN_THUOC`)
- Nhan vien ke toan (`NHAN_VIEN` + `KE_TOAN`)
- Nhan vien quan ly kho (`NHAN_VIEN` + `KHO`)

Khuyen nghi tao toi thieu 1 tai khoan test cho moi vai tro.

## 4) Khoi dong server LAN

Tu thu muc `be`:

- `start_lan_server.bat 0.0.0.0 8000`

Script se:

- chay `collectstatic`
- khoi dong ASGI server `daphne` tai `0.0.0.0:8000`

## 5) Truy cap tu client

Tren moi may client trong LAN:

- Mo trinh duyet: `http://192.168.1.10:8000`
- Dang nhap bang tung tai khoan vai tro
- Moi may co the gan cho 1 bo phan: le tan, bac si, ban thuoc, ke toan, quan ly kho, admin

## 6) Checklist xac nhan "client day du chuc nang nhu server"

### Kiem tra chung (tat ca vai tro)

- Dang nhap / dang xuat / F5 khong mat phien bat thuong
- Dashboard hien dung theo vai tro
- Du lieu tao o client A thay duoc o client B
- Khong goi duoc API vuot quyen

### Kiem tra theo vai tro

- Benh nhan: xem ho so, lich hen, mua thuoc, theo doi thong bao/chat neu co
- Bac si: tiep nhan lich kham, cap nhat benh an, ke don
- Le tan: tao/quan ly lich hen, tiep nhan benh nhan
- Ban thuoc: xu ly don/toa, ban thuoc theo quyen
- Ke toan: nghiep vu thanh toan, tong hop so lieu tai chinh
- Quan ly kho: nhap/xuat kho, cap nhat ton kho
- Admin: quan tri nguoi dung, cau hinh he thong, xem tong quan bao cao

Neu vai tro nao dang nhap duoc nhung khong hien dung dashboard/chuc nang, can kiem tra lai du lieu vai tro/chuc vu cua tai khoan do trong DB.

## 7) Van hanh on dinh

- Khong dung `runserver` de van hanh that
- Neu dung WebSocket/Celery, dam bao Redis chay tren server
- Dat lich backup database hang ngay
- Giu server luon mo de client truy cap lien tuc
