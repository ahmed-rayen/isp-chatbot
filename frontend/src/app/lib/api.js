// frontend/src/app/lib/api.js

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api';

export async function apiFetch(path, options = {}) {
  const token = sessionStorage.getItem('access_token');
  const url = path.startsWith('http') ? path : `${API_BASE}${path}`;
  
  // 1. Initial Request
  let res = await fetch(url, {
    ...options,
    credentials: "include", // MUST BE INCLUDED to send the httpOnly refresh cookie
    headers: {
      ...options.headers,
      ...(token ? { Authorization: `Bearer ${token}` } : {})
    }
  });

  // 2. Intercept 401 Unauthorized
  if (res.status === 401) {
    // Attempt silent refresh
    const refreshRes = await fetch(`${API_BASE}/auth/refresh`, {
      method: "POST",
      credentials: "include" // MUST BE INCLUDED to send the httpOnly refresh cookie
    });

    if (!refreshRes.ok) {
      // Refresh failed (cookie expired or revoked). Force re-login.
      sessionStorage.clear();
      if (typeof window !== 'undefined') {
        window.location.href = '/login';
      }
      throw new Error("Session expired. Please log in again.");
    }

    // 3. Get new access token and save it
    const { access_token } = await refreshRes.json();
    sessionStorage.setItem('access_token', access_token);

    // 4. Retry original request with the new token
    res = await fetch(url, {
      ...options,
      credentials: "include",
      headers: {
        ...options.headers,
        Authorization: `Bearer ${access_token}`
      }
    });
  }

  return res;
}