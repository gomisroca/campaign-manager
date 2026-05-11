export interface OrgResponse {
  id: string;
  name: string;
  slug: string;
  logo_url: string | null;
  plan: string;
  subscription_status: string | null;
  created_at: string;
}

export interface OrgWithRoleResponse {
  id: string;
  name: string;
  slug: string;
  logo_url: string | null;
  plan: string;
  role: string;
}

export interface MemberResponse {
  user_id: string;
  org_id: string;
  role: string;
  joined_at: string;
  email: string;
  full_name: string | null;
  avatar_url: string | null;
}
