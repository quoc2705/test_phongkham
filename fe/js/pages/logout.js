// js/pages/logout.js
console.log('logout.js loaded');

function handleLogout() {
    console.log('Logging out...');
    
    // Gọi API logout nếu có refresh token
    const refreshToken = localStorage.getItem('refresh_token');
    const accessToken = localStorage.getItem('access_token');
    
    if (refreshToken && accessToken) {
        // Logout route theo DRF router: /api/users/logout/
        fetch('/api/users/logout/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${accessToken}`
            },
            body: JSON.stringify({
                refresh: refreshToken
            })
        }).catch(err => console.error('Logout API error:', err));
    }
    
    // Xóa localStorage
    localStorage.clear();
    
    // Chuyển về trang login
    window.location.href = '/login/';
}

// Export to global
window.handleLogout = handleLogout;