export interface ApiResponse<T> {
    success: boolean;
    message?: string;
    data: T;
}

// Login request
export interface LoginRequest {
    email: string;
    password: string;
}

// Register request
export interface RegisterRequest {
    email: string;
    password: string;
    full_name: string;
    organization_name: string | null;
}

// Token response
export interface TokenResponse {
    user_id: number;
    user_email: string;
    access_token: string;
    refresh_token: string;
    token_type: string;
}

// Organization info
export interface OrganizationInfo {
    id: number;
    name: string;
}

// User Response
export interface UserResponse {
    id: number;
    email: string;
    full_name: string;
    role: "admin" | "manager" | "user";
    organization: OrganizationInfo | null;
    created_at: string;
    updated_at: string;
}