import { api } from "./client";

export const suppliersApi = {
  list: () => api.get("/suppliers/"),
  create: (data) => api.post("/suppliers/", data),
  update: (id, data) => api.patch(`/suppliers/${id}/`, data),
  remove: (id) => api.delete(`/suppliers/${id}/`),
};
