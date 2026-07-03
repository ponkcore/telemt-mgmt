// API client with JWT token management.
// Per ADR-002@0.1.0: JWT stored in localStorage, auto-attach Authorization header,
// redirect to /login on 401.

import axios, { type AxiosInstance, type AxiosResponse } from "axios";

import type {
  HealthResponse,
  LabelStatsListResponse,
  LinkCreate,
  LinkDeleteResponse,
  LinkListResponse,
  LinkResponse,
  LoginRequest,
  StatsResponse,
  TokenResponse,
  UserActionResponse,
  UserListResponse,
} from "./types";

const TOKEN_KEY = "telemt_admin_token";

const apiClient: AxiosInstance = axios.create({
  baseURL: "/api",
  timeout: 15000,
  headers: { "Content-Type": "application/json" },
});

// Request interceptor: auto-attach Authorization header.
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem(TOKEN_KEY);
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error),
);

// Response interceptor: redirect to /login on 401 (AC5).
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (axios.isAxiosError(error) && error.response?.status === 401) {
      localStorage.removeItem(TOKEN_KEY);
      if (window.location.pathname !== "/login") {
        window.location.href = "/login";
      }
    }
    return Promise.reject(error);
  },
);

// -- Auth ----------------------------------------------------------------------

async function login(data: LoginRequest): Promise<TokenResponse> {
  const res: AxiosResponse<TokenResponse> = await apiClient.post(
    "/auth/login",
    data,
  );
  localStorage.setItem(TOKEN_KEY, res.data.access_token);
  return res.data;
}

function logout(): void {
  localStorage.removeItem(TOKEN_KEY);
}

function isAuthenticated(): boolean {
  return localStorage.getItem(TOKEN_KEY) !== null;
}

// -- Users ---------------------------------------------------------------------

async function getUsers(
  page: number,
  perPage: number,
): Promise<UserListResponse> {
  const res: AxiosResponse<UserListResponse> = await apiClient.get("/users", {
    params: { page, per_page: perPage },
  });
  return res.data;
}

async function disableUser(username: string): Promise<UserActionResponse> {
  const res: AxiosResponse<UserActionResponse> = await apiClient.post(
    `/users/${encodeURIComponent(username)}/disable`,
  );
  return res.data;
}

async function enableUser(username: string): Promise<UserActionResponse> {
  const res: AxiosResponse<UserActionResponse> = await apiClient.post(
    `/users/${encodeURIComponent(username)}/enable`,
  );
  return res.data;
}

// -- Links ---------------------------------------------------------------------

async function getLinks(): Promise<LinkListResponse> {
  const res: AxiosResponse<LinkListResponse> = await apiClient.get("/links");
  return res.data;
}

async function createLink(data: LinkCreate): Promise<LinkResponse> {
  const res: AxiosResponse<LinkResponse> = await apiClient.post("/links", data);
  return res.data;
}

async function deleteLink(id: number): Promise<LinkDeleteResponse> {
  const res: AxiosResponse<LinkDeleteResponse> = await apiClient.delete(
    `/links/${id}`,
  );
  return res.data;
}

// -- Stats ---------------------------------------------------------------------

async function getStats(): Promise<StatsResponse> {
  const res: AxiosResponse<StatsResponse> = await apiClient.get("/stats");
  return res.data;
}

async function getLabelStats(): Promise<LabelStatsListResponse> {
  const res: AxiosResponse<LabelStatsListResponse> = await apiClient.get(
    "/stats/labels",
  );
  return res.data;
}

// -- Health --------------------------------------------------------------------

async function getHealth(): Promise<HealthResponse> {
  const res: AxiosResponse<HealthResponse> = await apiClient.get("/health");
  return res.data;
}

export const api = {
  login,
  logout,
  isAuthenticated,
  getUsers,
  disableUser,
  enableUser,
  getLinks,
  createLink,
  deleteLink,
  getStats,
  getLabelStats,
  getHealth,
};
