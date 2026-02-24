import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { UserResponse } from '@/types';

interface AuthState {
    user: UserResponse | null;
    accessToken: string | null;
    refreshToken: string | null;
    isAuthenticated: boolean;
    login: ( user: UserResponse, accessToken: string, refreshToken: string ) => void;
    logout: () => void;
}

export const useAuthStore = create<AuthState>()(
    persist(
        ( set ) => ( {
            user: null,
            accessToken: null,
            refreshToken: null,
            isAuthenticated: false,
            login: ( user, accessToken, refreshToken ) => {
                localStorage.setItem( 'authToken', accessToken );
                set( { user, accessToken, refreshToken, isAuthenticated: true } );
            },
            logout: () => {
                localStorage.removeItem( 'authToken' );
                set( { user: null, accessToken: null, refreshToken: null, isAuthenticated: false } );
            },
        } ),
        {
            name: 'auth-storage',
        }
    )
);
