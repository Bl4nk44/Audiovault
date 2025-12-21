import api from "./api";
import type { LoginCredentials, RegisterCredentials } from "../types";

export const login = async (credentials: LoginCredentials) => {
  const response = await api.post("/auth/login", credentials);
  return response.data;
};

export const register = async (data: RegisterCredentials) => {
  const response = await api.post("/auth/register", data);
  return response.data;
};

export const getMe = async () => {
  const response = await api.get("/auth/me");
  return response.data;
};
