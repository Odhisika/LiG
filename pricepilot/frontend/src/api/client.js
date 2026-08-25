const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api";

const ACCESS_KEY = "pp_access";
const REFRESH_KEY = "pp_refresh";

export function getAccessToken() {
  return localStorage.getItem(ACCESS_KEY);
}

export function getRefreshToken() {
  return localStorage.getItem(REFRESH_KEY);
}

export function setTokens({ access, refresh }) {
  if (access) localStorage.setItem(ACCESS_KEY, access);
  if (refresh) localStorage.setItem(REFRESH_KEY, refresh);
}

export function clearTokens() {
  localStorage.removeItem(ACCESS_KEY);
  localStorage.removeItem(REFRESH_KEY);
}

// Set by AuthContext on mount so the client can react to a refresh
// failure (expired/invalid refresh token) without importing React state
// into this plain module.
let onAuthFailure = () => {};
export function registerAuthFailureHandler(fn) {
  onAuthFailure = fn;
}

async function refreshAccessToken() {
  const refresh = getRefreshToken();
  if (!refresh) return false;

  const response = await fetch(`${API_BASE_URL}/auth/refresh/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh }),
  });

  if (!response.ok) return false;

  const data = await response.json();
  setTokens({ access: data.access });
  return true;
}

class ApiError extends Error {
  constructor(message, status, detail) {
    super(message);
    this.status = status;
    this.detail = detail;
  }
}

/**
 * Core request function. Unwraps the backend's {"data", "error"} envelope
 * automatically. On a 401, tries exactly one silent token refresh + retry
 * before giving up — most API calls in this app don't need to think
 * about auth at all beyond that.
 */
async function request(path, { method = "GET", body, isRetry = false, raw = false } = {}) {
  const headers = { "Content-Type": "application/json" };
  const token = getAccessToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const response = await fetch(`${API_BASE_URL}${path}`, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });

  if (response.status === 401 && !isRetry && !raw) {
    const refreshed = await refreshAccessToken();
    if (refreshed) {
      return request(path, { method, body, isRetry: true, raw });
    }
    clearTokens();
    onAuthFailure();
    throw new ApiError("Session expired — please log in again.", 401);
  }

  if (response.status === 204) return null;

  let payload = null;
  try {
    payload = await response.json();
  } catch {
    // No body (e.g. some error responses) — fine, handled below.
  }

  if (!response.ok) {
    const message =
      payload?.error?.message ||
      payload?.detail ||
      `Request failed (${response.status})`;
    throw new ApiError(message, response.status, payload?.error?.detail);
  }

  // raw=true is for the two unwrapped simplejwt endpoints (login/refresh);
  // everything else goes through our own envelope.
  return raw ? payload : payload?.data;
}

export const api = {
  get: (path) => request(path),
  post: (path, body) => request(path, { method: "POST", body }),
  put: (path, body) => request(path, { method: "PUT", body }),
  patch: (path, body) => request(path, { method: "PATCH", body }),
  delete: (path) => request(path, { method: "DELETE" }),
  rawPost: (path, body) => request(path, { method: "POST", body, raw: true }),
};

export { ApiError };
