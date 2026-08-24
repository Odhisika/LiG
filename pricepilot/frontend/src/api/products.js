import { api } from "./client";

function toQuery(params) {
  const entries = Object.entries(params || {}).filter(([, v]) => v !== undefined && v !== "");
  if (!entries.length) return "";
  return "?" + new URLSearchParams(entries).toString();
}

export const productsApi = {
  list: (params) => api.get(`/products/${toQuery(params)}`),
  categories: () => api.get("/products/categories/"),
  create: (data) => api.post("/products/", data),
  update: (id, data) => api.patch(`/products/${id}/`, data),
  remove: (id) => api.delete(`/products/${id}/`),
};
