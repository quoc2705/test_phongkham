from django.shortcuts import render
from django.http import JsonResponse, HttpResponse
import os
from django.conf import settings

def index(request):
    """Render trang chủ frontend"""
    return render(request, 'index.html')

def login_view(request):
    """Render trang đăng nhập"""
    return render(request, 'login.html')

def serve_frontend(request, path=''):
    """Serve các file frontend tĩnh"""
    # Xác định đường dẫn file
    if path == '':
        file_path = os.path.join(settings.BASE_DIR, 'fe', 'index.html')
    else:
        file_path = os.path.join(settings.BASE_DIR, 'fe', path)
    
    # Kiểm tra file tồn tại
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Xác định Content-Type
        if file_path.endswith('.html'):
            content_type = 'text/html'
        elif file_path.endswith('.css'):
            content_type = 'text/css'
        elif file_path.endswith('.js'):
            content_type = 'application/javascript'
        elif file_path.endswith('.png'):
            content_type = 'image/png'
        elif file_path.endswith('.jpg') or file_path.endswith('.jpeg'):
            content_type = 'image/jpeg'
        elif file_path.endswith('.svg'):
            content_type = 'image/svg+xml'
        else:
            content_type = 'text/plain'
        
        return HttpResponse(content, content_type=content_type)
    else:
        return HttpResponse('File not found', status=404)

def api_documentation(request):
    """Trang documentation cho API"""
    return JsonResponse({
        'message': 'Phòng khám API System',
        'version': '1.0.0',
        'endpoints': {
            'authentication': {
                'register': '/api/auth/dang-ky/',
                'login': '/api/auth/dang-nhap/',
                'refresh_token': '/api/auth/lam-moi-token/',
            },
            'medicines': {
                'medicines': '/api/thuoc/thuoc/',
                'inventory': '/api/thuoc/kho-thuoc/',
                'vaccines': '/api/thuoc/vaccine/',
                'vaccine_inventory': '/api/thuoc/kho-vaccine/',
            },
            'appointments': '/api/lich-hen/',
            'medical_records': '/api/benh-an/',
            'orders': '/api/don-hang/',
            'notifications': '/api/thong-bao/',
            'reports': '/api/bao-cao/',
            'chat': '/api/tro-chuyen/',
        }
    })