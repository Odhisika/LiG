import { api } from "./client";

function toQuery(params) {
  const entries = Object.entries(params || {}).filter(([, v]) => v !== undefined && v !== "");
  if (!entries.length) return "";
  return "?" + new URLSearchParams(entries).toString();
}

export const dashboardApi = {
  summary: () => api.get("/dashboard/summary/"),
  activity: (params) => api.get(`/dashboard/activity/${toQuery(params)}`),
};

export const pricingApi = {
  list: () => api.get("/pricing-rules/"),
  create: (data) => api.post("/pricing-rules/", data),
  update: (id, data) => api.patch(`/pricing-rules/${id}/`, data),
  remove: (id) => api.delete(`/pricing-rules/${id}/`),
  defaultMarkup: () => api.get("/pricing-rules/default-markup/"),
  setDefaultMarkup: (markup_percent) =>
    api.put("/pricing-rules/default-markup/", { markup_percent }),
};

export const historyApi = {
  list: (params) => api.get(`/history/${toQuery(params)}`),
};

export const notificationsApi = {
  list: (params) => api.get(`/notifications/${toQuery(params)}`),
};

export const analyticsApi = {
  summary: (params) => api.get(`/analytics/summary/${toQuery(params)}`),
};

export const discoveryApi = {
  list: (params) => api.get(`/discoveries/${toQuery(params)}`),
  import: (id, overrides) => api.post(`/discoveries/${id}/import/`, overrides || {}),
  dismiss: (id) => api.post(`/discoveries/${id}/dismiss/`, {}),
};
