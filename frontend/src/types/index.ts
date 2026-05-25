export interface User {
  id: string;
  email: string;
  name: string;
  is_active: boolean;
  is_system_admin: boolean;
  last_project_id: string | null;
  wecom_mobile?: string | null;
  wecom_userid?: string | null;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export interface ProjectBrief {
  id: string;
  name: string;
  role: string;
  is_project_admin: boolean;
}

export interface MeResponse {
  user: User;
  projects: ProjectBrief[];
}

export interface Project {
  id: string;
  name: string;
  is_enabled: boolean;
  created_at: string;
}

export interface ProjectMember {
  id: string;
  project_id: string;
  user_id: string;
  role: string;
  is_project_admin: boolean;
  user?: User;
}
