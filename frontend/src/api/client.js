// Central place for every network call the app makes. Reading the API base
// from an env var (falling back to the current production URL) means we
// never again hardcode 'https://taxautomationapp.onrender.com' in 18
// different components.
export const API_BASE = process.env.REACT_APP_API_URL || 'https://taxautomationapp.onrender.com';

const TOKEN_KEY = 'authToken';

export function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token) {
  if (token) {
    localStorage.setItem(TOKEN_KEY, token);
  } else {
    localStorage.removeItem(TOKEN_KEY);
  }
}

// Low-level fetch wrapper: resolves the path against API_BASE and attaches
// the auth token. Use this directly for routes that return a file (blob).
export async function apiFetch(path, options = {}) {
  const token = getToken();
  const headers = { ...(options.headers || {}) };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  // Don't set Content-Type for FormData uploads -- the browser needs to add
  // its own multipart boundary.
  if (options.body && !(options.body instanceof FormData) && !headers['Content-Type']) {
    headers['Content-Type'] = 'application/json';
  }

  const response = await fetch(`${API_BASE}${path}`, { ...options, headers });

  if (response.status === 401) {
    // Token missing/expired -- drop it so the app falls back to the login screen.
    setToken(null);
  }

  return response;
}

// Convenience wrapper for JSON APIs: throws on non-2xx so callers can just
// try/catch instead of checking response.ok everywhere.
export async function apiJson(path, options = {}) {
  const response = await apiFetch(path, options);
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const error = new Error(data.error || `Request failed (${response.status})`);
    error.status = response.status;
    error.data = data;
    throw error;
  }
  return data;
}
