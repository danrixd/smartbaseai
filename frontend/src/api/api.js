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

export default api;
