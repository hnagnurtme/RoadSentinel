import { api } from './api';
import type { ApiResponse, LoginRequest, RegisterRequest, TokenResponse, UserResponse } from '@/types/index';

export const authService = {
    async login ( request: LoginRequest ): Promise<ApiResponse<TokenResponse>> {
        const response = await api.post<ApiResponse<TokenResponse>>( '/auth/login', request );
        return response.data;
    },

    async register ( request: RegisterRequest ): Promise<ApiResponse<TokenResponse>> {
        const response = await api.post<ApiResponse<TokenResponse>>( '/auth/register', request );
        return response.data;
    },

    async refresh ( refreshToken: string ): Promise<ApiResponse<TokenResponse>> {
        const response = await api.post<ApiResponse<TokenResponse>>( '/auth/refresh', {
            refresh_token: refreshToken,
        } );
        return response.data;
    },

    async logout (): Promise<void> {
        await api.post( '/auth/logout' );
    },

    async getMe (): Promise<ApiResponse<UserResponse>> {
        const response = await api.get<ApiResponse<UserResponse>>( '/users/me' );
        return response.data;
    },
};