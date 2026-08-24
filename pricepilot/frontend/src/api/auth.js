import { api } from "./client";

export const authApi = {
  register: (data) => api.post("/auth/register/", data),
  login: (email, password) => api.rawPost("/auth/login/", { email, password }),
  me: () => api.get("/auth/me/"),
};
