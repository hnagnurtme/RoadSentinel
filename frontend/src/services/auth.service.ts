import type { ApiResponse, LoginRequest, RegisterRequest, TokenResponse, UserResponse } from "@/types/index";

export const authService = {
    async login(request: LoginRequest): Promise<ApiResponse<TokenResponse>> {
        if (!request.email || !request.password) {
            throw new Error("Email and password are required");
        }

        return {
            success: true,
            message: "Login successful",
            data: {
                user_id: 1,
                user_email: request.email,
                access_token: "mock_access_token",
                refresh_token: "mock_refresh_token",
                token_type: "Bearer"
            }
        }
    },

    async register (request: RegisterRequest): Promise<ApiResponse<UserResponse>> {

        return {
            success: true,
            message: "Registration successful",
            data: {
                id: Math.floor(Math.random() * 1000),
                email: request.email,
                full_name: request.full_name,
                role: "user",
                organization: request.organization_name ? { id: 1, name: request.organization_name } : null,
                created_at: new Date().toISOString(),
                updated_at: new Date().toISOString()
            }
        }
    }
}