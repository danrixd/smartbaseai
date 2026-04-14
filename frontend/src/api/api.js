import axios from 'axios';

const api = axios.create({
  // Use env base URL when provided, otherwise fall back to local FastAPI server.
  // Trim any trailing slash so requests don't end up with duplicate slashes.
  baseURL: (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000').replace(/\/$/, ''),
  headers: {
    'Content-Type': 'application/json',
  },
});

// Surface the resolved base URL in the browser console to simplify debugging
// misconfigured environments that can lead to 404 errors when posting chat
// messages.
console.log('API base URL:', api.defaults.baseURL);

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Session-timeout handler: when the backend rejects a request with 401 or
// any "Token expired" / "Invalid token" error, clear the local session state
// and bounce the user back to the login page. Without this, expired tokens
// silently produce 401s all over the app with no recovery path.
api.interceptors.response.use(
  (res) => res,
  (err) => {
    const status = err.response?.status;
    const detail = err.response?.data?.detail || '';
    const expired =
      status === 401 ||
      /token expired|invalid token/i.test(detail);
    if (expired && typeof window !== 'undefined') {
      const path = window.location.pathname;
      // Don't bounce if we're already on the login page (prevents infinite loop)
      if (path !== '/login') {
        localStorage.removeItem('access_token');
        localStorage.removeItem('role');
        localStorage.removeItem('tenant_id');
        localStorage.removeItem('active_tenant');
        localStorage.removeItem('username');
        // Preserve where the user was so we can bounce back after re-login
        sessionStorage.setItem('post_login_redirect', path + window.location.search);
        window.location.assign('/login');
      }
    }
    return Promise.reject(err);
  },
);

export default api;
