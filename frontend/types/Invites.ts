export interface InviteResponse {
  id: string;
  org_id: string;
  email: string;
  role: string;
  expires_at: string;
  accepted_at: string | null;
  created_at: string;
  org_name: string;
  invited_by_email: string;
}

export interface InvitePublicResponse {
  org_name: string;
  email: string;
  role: string;
  is_valid: boolean;
}
