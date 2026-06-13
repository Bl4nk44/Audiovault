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

export const getRegistrationStatus = async (): Promise<{ enabled: boolean }> => {
  const response = await api.get("/auth/registration-status");
  return response.data;
};

export const setRegistrationEnabled = async (enabled: boolean): Promise<{ enabled: boolean }> => {
  const response = await api.put("/settings/registration", { enabled });
  return response.data;
};
