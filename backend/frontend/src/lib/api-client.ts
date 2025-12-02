/**
 * Base API client with authentication interceptor.
 *
 * Features:
 * - Automatic JWT token attachment
 * - Token refresh on 401 responses
 * - Request/response interceptors
 * - Error handling
 * - TypeScript type safety
 */

import axios, {
  AxiosInstance,
  AxiosRequestConfig,
  AxiosResponse,
  AxiosError,
  InternalAxiosRequestConfig,
} from 'axios';

/**
 * API error response interface.
 */
export interface ApiErrorResponse {
  error_id: string;
  message: string;
  details?: string | Record<string, any>;
}

/**
 * Token storage interface.
 */
interface TokenStorage {
  getAccessToken: () => string | null;
  getRefreshToken: () => string | null;
  setTokens: (accessToken: string, refreshToken: string) => void;
  clearTokens: () => void;
}

/**
 * Default token storage using localStorage.
 */
const defaultTokenStorage: TokenStorage = {
  getAccessToken: () => localStorage.getItem('access_token'),
  getRefreshToken: () => localStorage.getItem('refresh_token'),
  setTokens: (accessToken: string, refreshToken: string) => {
    localStorage.setItem('access_token', accessToken);
    localStorage.setItem('refresh_token', refreshToken);
  },
  clearTokens: () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
  },
};

/**
 * API client configuration.
 */
export interface ApiClientConfig {
  baseURL?: string;
  tokenStorage?: TokenStorage;
  onAuthError?: () => void;
}

/**
 * Create configured API client with authentication.
 */
export class ApiClient {
  private client: AxiosInstance;
  private tokenStorage: TokenStorage;
  private onAuthError?: () => void;
  private isRefreshing = false;
  private refreshSubscribers: Array<(token: string) => void> = [];

  constructor(config: ApiClientConfig = {}) {
    const {
      baseURL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',
      tokenStorage = defaultTokenStorage,
      onAuthError,
    } = config;

    this.tokenStorage = tokenStorage;
    this.onAuthError = onAuthError;

    // Create axios instance
    this.client = axios.create({
      baseURL,
      headers: {
        'Content-Type': 'application/json',
      },
      timeout: 30000, // 30 seconds
    });

    // Setup interceptors
    this.setupRequestInterceptor();
    this.setupResponseInterceptor();
  }

  /**
   * Setup request interceptor to attach auth token.
   */
  private setupRequestInterceptor(): void {
    this.client.interceptors.request.use(
      (config: InternalAxiosRequestConfig) => {
        const token = this.tokenStorage.getAccessToken();

        if (token && config.headers) {
          config.headers.Authorization = `Bearer ${token}`;
        }

        return config;
      },
      (error: AxiosError) => {
        return Promise.reject(error);
      }
    );
  }

  /**
   * Setup response interceptor for token refresh.
   */
  private setupResponseInterceptor(): void {
    this.client.interceptors.response.use(
      (response: AxiosResponse) => response,
      async (error: AxiosError) => {
        const originalRequest = error.config as InternalAxiosRequestConfig & {
          _retry?: boolean;
        };

        // Handle 401 Unauthorized
        if (error.response?.status === 401 && !originalRequest._retry) {
          if (this.isRefreshing) {
            // Wait for token refresh
            return new Promise((resolve) => {
              this.refreshSubscribers.push((token: string) => {
                if (originalRequest.headers) {
                  originalRequest.headers.Authorization = `Bearer ${token}`;
                }
                resolve(this.client(originalRequest));
              });
            });
          }

          originalRequest._retry = true;
          this.isRefreshing = true;

          try {
            const refreshToken = this.tokenStorage.getRefreshToken();

            if (!refreshToken) {
              throw new Error('No refresh token available');
            }

            // Refresh access token
            const response = await this.client.post('/api/v1/auth/refresh', {
              refresh_token: refreshToken,
            });

            const { access_token } = response.data;

            // Update stored token
            const currentRefreshToken = this.tokenStorage.getRefreshToken();
            if (currentRefreshToken) {
              this.tokenStorage.setTokens(access_token, currentRefreshToken);
            }

            // Retry failed requests with new token
            this.refreshSubscribers.forEach((callback) =>
              callback(access_token)
            );
            this.refreshSubscribers = [];

            // Retry original request
            if (originalRequest.headers) {
              originalRequest.headers.Authorization = `Bearer ${access_token}`;
            }

            return this.client(originalRequest);
          } catch (refreshError) {
            // Refresh failed - clear tokens and notify
            this.tokenStorage.clearTokens();
            this.onAuthError?.();

            return Promise.reject(refreshError);
          } finally {
            this.isRefreshing = false;
          }
        }

        return Promise.reject(error);
      }
    );
  }

  /**
   * GET request.
   */
  async get<T = any>(url: string, config?: AxiosRequestConfig): Promise<T> {
    const response = await this.client.get<T>(url, config);
    return response.data;
  }

  /**
   * POST request.
   */
  async post<T = any>(
    url: string,
    data?: any,
    config?: AxiosRequestConfig
  ): Promise<T> {
    const response = await this.client.post<T>(url, data, config);
    return response.data;
  }

  /**
   * PUT request.
   */
  async put<T = any>(
    url: string,
    data?: any,
    config?: AxiosRequestConfig
  ): Promise<T> {
    const response = await this.client.put<T>(url, data, config);
    return response.data;
  }

  /**
   * PATCH request.
   */
  async patch<T = any>(
    url: string,
    data?: any,
    config?: AxiosRequestConfig
  ): Promise<T> {
    const response = await this.client.patch<T>(url, data, config);
    return response.data;
  }

  /**
   * DELETE request.
   */
  async delete<T = any>(url: string, config?: AxiosRequestConfig): Promise<T> {
    const response = await this.client.delete<T>(url, config);
    return response.data;
  }

  /**
   * Get axios instance for advanced usage.
   */
  getAxiosInstance(): AxiosInstance {
    return this.client;
  }
}

/**
 * Default API client instance.
 */
export const apiClient = new ApiClient({
  onAuthError: () => {
    // Redirect to login on auth error
    window.location.href = '/auth/login';
  },
});

/**
 * API error class.
 */
export class ApiError extends Error {
  public errorId?: string;
  public statusCode?: number;
  public details?: string | Record<string, any>;

  constructor(
    message: string,
    statusCode?: number,
    errorId?: string,
    details?: string | Record<string, any>
  ) {
    super(message);
    this.name = 'ApiError';
    this.statusCode = statusCode;
    this.errorId = errorId;
    this.details = details;
  }

  /**
   * Create ApiError from AxiosError.
   */
  static fromAxiosError(error: AxiosError<ApiErrorResponse>): ApiError {
    const response = error.response?.data;
    const message = response?.message || error.message || 'An error occurred';
    const statusCode = error.response?.status;
    const errorId = response?.error_id;
    const details = response?.details;

    return new ApiError(message, statusCode, errorId, details);
  }
}
