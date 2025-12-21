import axios, { AxiosError } from "axios";
import type { InternalAxiosRequestConfig } from "axios";
// Remove circular import
// import { useStore } from "../store/useStore";

// Store injection to break circular dependency
// Store injection to break circular dependency
interface Store {
  getState: () => {
    logout: () => void;
    setTokens: (access_token: string, refresh_token: string) => void;
  };
}

let store: Store | null = null;
export const injectStore = (_store: Store) => {
  store = _store;
};

export const API_URL =
  import.meta.env.VITE_API_URL || "http://localhost:8000/api/v1";

const api = axios.create({
  baseURL: API_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

api.interceptors.request.use((config) => {
  // Use localStorage directly to avoid circular dependency issues and ensure token availability
  const token = localStorage.getItem("access_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

let isRefreshing = false;
let failedQueue: Array<{
  resolve: (token: string) => void;
  reject: (error: unknown) => void;
}> = [];

const processQueue = (error: unknown, token: string | null = null) => {
  failedQueue.forEach((prom) => {
    if (error) {
      prom.reject(error);
    } else {
      prom.resolve(token!);
    }
  });
  failedQueue = [];
};

api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & {
      _retry?: boolean;
    };

    if (error.response?.status === 401 && !originalRequest._retry) {
      if (isRefreshing) {
        return new Promise(function (resolve, reject) {
          failedQueue.push({ resolve, reject });
        })
          .then((token) => {
            originalRequest.headers.Authorization = `Bearer ${token}`;
            return api(originalRequest);
          })
          .catch((err) => {
            return Promise.reject(err);
          });
      }

      originalRequest._retry = true;
      isRefreshing = true;

      // Use injected store's getState
      const refreshToken = localStorage.getItem("refresh_token");

      if (!refreshToken) {
        store?.getState().logout();
        return Promise.reject(error);
      }

      try {
        const response = await axios.post(
          `${
            import.meta.env.VITE_API_URL || "http://localhost:8000/api/v1"
          }/auth/refresh`,
          { refresh_token: refreshToken }
        );

        const { access_token, refresh_token: newRefreshToken } = response.data;

        // Use injected store
        store?.getState().setTokens(access_token, newRefreshToken);

        api.defaults.headers.common.Authorization = `Bearer ${access_token}`;
        originalRequest.headers.Authorization = `Bearer ${access_token}`;

        processQueue(null, access_token);

        return api(originalRequest);
      } catch (err) {
        processQueue(err, null);
        store?.getState().logout();
        return Promise.reject(err);
      } finally {
        isRefreshing = false;
      }
    }

    return Promise.reject(error);
  }
);

export default api;
