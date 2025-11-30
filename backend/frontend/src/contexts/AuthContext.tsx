/**
 * Authentication context provider.
 *
 * Manages:
 * - Login/logout
 * - Token storage
 * - Current vendor state
 * - Authentication status
 */

import {
  createContext,
  useContext,
  useState,
  useEffect,
  ReactNode,
} from 'react';
import { apiClient, ApiError } from '../lib/api-client';

/**
 * Vendor interface from backend.
 */
export interface Vendor {
  id: string;
  email: string;
  business_name: string;
  subscription_tier: string;
  subscription_status: string;
}

/**
 * Login response from backend.
 */
interface LoginResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  vendor: Vendor;
}

/**
 * Auth context interface.
 */
interface AuthContextType {
  vendor: Vendor | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
}

/**
 * Auth context.
 */
const AuthContext = createContext<AuthContextType | undefined>(undefined);

/**
 * Auth provider props.
 */
interface AuthProviderProps {
  children: ReactNode;
}

/**
 * Auth context provider component.
 */
export function AuthProvider({ children }: AuthProviderProps) {
  const [vendor, setVendor] = useState<Vendor | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  /**
   * Check if user is authenticated on mount.
   */
  useEffect(() => {
    const checkAuth = async () => {
      const accessToken = localStorage.getItem('access_token');

      if (!accessToken) {
        setIsLoading(false);
        return;
      }

      try {
        // Verify token by fetching vendor profile
        // This will use the token from localStorage via apiClient interceptor
        const response = await apiClient.get<Vendor>('/api/v1/auth/me');
        setVendor(response);
      } catch (error) {
        // Token invalid or expired - clear storage
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        setVendor(null);
      } finally {
        setIsLoading(false);
      }
    };

    checkAuth();
  }, []);

  /**
   * Login with email and password.
   */
  const login = async (email: string, password: string): Promise<void> => {
    try {
      const response = await apiClient.post<LoginResponse>(
        '/api/v1/auth/login',
        {
          email,
          password,
        }
      );

      // Store tokens
      localStorage.setItem('access_token', response.access_token);
      localStorage.setItem('refresh_token', response.refresh_token);

      // Set vendor
      setVendor(response.vendor);
    } catch (error: any) {
      // Re-throw with user-friendly message
      if (error.response?.status === 401) {
        throw new Error('Invalid email or password');
      }

      throw new Error(
        error.response?.data?.message || 'Login failed. Please try again.'
      );
    }
  };

  /**
   * Logout user.
   */
  const logout = (): void => {
    // Clear tokens
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');

    // Clear vendor
    setVendor(null);

    // Redirect to login
    window.location.href = '/auth/login';
  };

  const value: AuthContextType = {
    vendor,
    isAuthenticated: vendor !== null,
    isLoading,
    login,
    logout,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

/**
 * Hook to use auth context.
 */
export function useAuth(): AuthContextType {
  const context = useContext(AuthContext);

  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }

  return context;
}
