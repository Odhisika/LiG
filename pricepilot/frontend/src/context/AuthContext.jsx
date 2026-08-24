import { createContext, useContext, useEffect, useState, useCallback } from "react";
import {
  clearTokens,
  getAccessToken,
  registerAuthFailureHandler,
  setTokens,
} from "../api/client";
import { authApi } from "../api/auth";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  const logout = useCallback(() => {
    clearTokens();
    setUser(null);
  }, []);

  useEffect(() => {
    registerAuthFailureHandler(() => setUser(null));

    async function bootstrap() {
      if (getAccessToken()) {
        try {
          const me = await authApi.me();
          setUser(me);
        } catch {
          clearTokens();
        }
      }
      setLoading(false);
    }
    bootstrap();
  }, []);

  async function login(email, password) {
    const tokens = await authApi.login(email, password);
    setTokens(tokens);
    const me = await authApi.me();
    setUser(me);
  }

  async function register(email, password, fullName) {
    await authApi.register({ email, password, full_name: fullName });
    await login(email, password);
  }

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
