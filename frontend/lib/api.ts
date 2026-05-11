import { TokenResponse, UserResponse } from "@/types/Auth";
import { BillingStatus } from "@/types/Billing";
import { InvitePublicResponse, InviteResponse } from "@/types/Invites";
import { MemberResponse, OrgResponse, OrgWithRoleResponse } from "@/types/Orgs";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

// ── Types ─────────────────────────────────────────────────────────────────────
export interface ApiError {
  detail: string | Array<{ msg: string; loc: string[]; type: string }>;
}

// ── Token storage ─────────────────────────────────────────────────────────────
const ACCESS_TOKEN_KEY = "access_token";
const REFRESH_TOKEN_KEY = "refresh_token";

export const tokens = {
  getAccess: () => localStorage.getItem(ACCESS_TOKEN_KEY),
  getRefresh: () => localStorage.getItem(REFRESH_TOKEN_KEY),
  set: (access: string, refresh: string) => {
    localStorage.setItem(ACCESS_TOKEN_KEY, access);
    localStorage.setItem(REFRESH_TOKEN_KEY, refresh);
  },
  clear: () => {
    localStorage.removeItem(ACCESS_TOKEN_KEY);
    localStorage.removeItem(REFRESH_TOKEN_KEY);
  },
};

// ── Core fetch wrapper ────────────────────────────────────────────────────────
export async function request<T>(
  path: string,
  options: RequestInit = {},
  authenticated = true,
): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...((options.headers as Record<string, string>) ?? {}),
  };

  if (authenticated) {
    const token = tokens.getAccess();
    if (token) headers["Authorization"] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_BASE}/api/v1${path}`, {
    ...options,
    headers,
  });

  // Token expired - try to refresh once then retry the original request.
  if (res.status === 401 && authenticated) {
    const refreshed = await tryRefresh();
    if (refreshed) {
      headers["Authorization"] = `Bearer ${tokens.getAccess()}`;
      const retryRes = await fetch(`${API_BASE}/api/v1${path}`, {
        ...options,
        headers,
      });
      if (retryRes.ok) return retryRes.json() as Promise<T>;
    }

    tokens.clear();
    window.location.href = "/login";
    throw new Error("Session expired");
  }

  if (!res.ok) {
    const error: ApiError = await res
      .json()
      .catch(() => ({ detail: "Unknown error" }));
    if (Array.isArray(error.detail)) {
      const messages = error.detail
        .map((e: { msg: string }) => e.msg)
        .join(", ");
      throw new Error(messages);
    }
    throw new Error(error.detail);
  }

  // 204 No Content - nothing to parse
  if (res.status === 204) return undefined as T;

  return res.json() as Promise<T>;
}

async function tryRefresh(): Promise<boolean> {
  const refreshToken = tokens.getRefresh();
  if (!refreshToken) return false;

  try {
    const res = await fetch(`${API_BASE}/api/v1/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
    if (!res.ok) return false;
    const data: TokenResponse = await res.json();
    tokens.set(data.access_token, data.refresh_token);
    return true;
  } catch {
    return false;
  }
}

// ── Auth endpoints ────────────────────────────────────────────────────────────
export const authApi = {
  register: (email: string, password: string, full_name?: string) =>
    request<TokenResponse>(
      "/auth/register",
      {
        method: "POST",
        body: JSON.stringify({ email, password, full_name }),
      },
      false,
    ),

  login: (email: string, password: string) =>
    request<TokenResponse>(
      "/auth/login",
      {
        method: "POST",
        body: JSON.stringify({ email, password }),
      },
      false,
    ),

  me: () => request<UserResponse>("/auth/me"),

  forgotPassword: (email: string) =>
    request<void>(
      "/auth/forgot-password",
      {
        method: "POST",
        body: JSON.stringify({ email }),
      },
      false,
    ),
};

// ── Orgs endpoints ──────────────────────────────────────────────────────────────────────
export const orgsApi = {
  list: () => request<OrgWithRoleResponse[]>("/orgs"),

  create: (name: string, slug?: string) =>
    request<OrgResponse>("/orgs", {
      method: "POST",
      body: JSON.stringify({ name, slug }),
    }),

  get: (orgId: string) => request<OrgResponse>(`/orgs/${orgId}`),

  update: (orgId: string, data: { name?: string; logo_url?: string }) =>
    request<OrgResponse>(`/orgs/${orgId}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),

  delete: (orgId: string) =>
    request<void>(`/orgs/${orgId}`, { method: "DELETE" }),

  listMembers: (orgId: string) =>
    request<MemberResponse[]>(`/orgs/${orgId}/members`),

  updateMemberRole: (orgId: string, userId: string, role: string) =>
    request<MemberResponse>(`/orgs/${orgId}/members/${userId}`, {
      method: "PATCH",
      body: JSON.stringify({ role }),
    }),

  removeMember: (orgId: string, userId: string) =>
    request<void>(`/orgs/${orgId}/members/${userId}`, { method: "DELETE" }),
};

// ── Invites endpoints ────────────────────────────────────────────────────────────
export const invitesApi = {
  list: (orgId: string) => request<InviteResponse[]>(`/orgs/${orgId}/invites`),

  create: (orgId: string, email: string, role: string) =>
    request<InviteResponse>(`/orgs/${orgId}/invites`, {
      method: "POST",
      body: JSON.stringify({ email, role }),
    }),

  revoke: (orgId: string, inviteId: string) =>
    request<void>(`/orgs/${orgId}/invites/${inviteId}`, { method: "DELETE" }),

  getByToken: (token: string) =>
    request<InvitePublicResponse>(`/invites/${token}`, {}, false),

  accept: (token: string) =>
    request<{ org_id: string; role: string }>("/invites/accept", {
      method: "POST",
      body: JSON.stringify({ token }),
    }),
};

// ── Billing endpoints ────────────────────────────────────────────────────────────
export const billingApi = {
  getStatus: (orgId: string) =>
    request<BillingStatus>(`/orgs/${orgId}/billing`),

  createCheckout: (orgId: string) =>
    request<{ url: string }>(`/orgs/${orgId}/billing/checkout`, {
      method: "POST",
    }),

  createPortal: (orgId: string) =>
    request<{ url: string }>(`/orgs/${orgId}/billing/portal`, {
      method: "POST",
    }),
};
