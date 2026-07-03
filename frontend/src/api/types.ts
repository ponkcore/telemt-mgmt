// TypeScript types matching the admin API response models (api/schemas.py).
// Per ARCH-001@0.1.1 §3 C3 — all JSON contracts mirrored here.

// -- Auth models ---------------------------------------------------------------

export interface LoginRequest {
  username: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

// -- User models ---------------------------------------------------------------

export interface UserResponse {
  name: string;
  is_disabled: boolean;
  source: string;
  created_at: string | null;
  is_active: boolean;
  ip_count: number | null;
  connections: number | null;
}

export interface UserListResponse {
  items: UserResponse[];
  total: number;
  page: number;
  per_page: number;
}

export interface UserActionResponse {
  username: string;
  is_disabled: boolean;
}

// -- Link models ---------------------------------------------------------------

export interface LinkCreate {
  label: string;
}

export interface LinkResponse {
  id: number;
  label: string;
  telemt_username: string;
  proxy_link: string;
  is_active: boolean;
  created_at: string | null;
}

export interface LinkListResponse {
  items: LinkResponse[];
}

export interface LinkDeleteResponse {
  id: number;
  deleted: boolean;
}

// -- Stats models --------------------------------------------------------------

export interface StatsResponse {
  active_users: number;
  total_connections: number;
  total_traffic: number;
}

export interface LabelStats {
  label: string;
  telemt_username: string;
  connections: number;
  ip_count: number;
}

export interface LabelStatsListResponse {
  items: LabelStats[];
}

// -- Health model --------------------------------------------------------------

export interface HealthResponse {
  status: string;
}
