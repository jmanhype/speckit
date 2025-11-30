/**
 * React Router configuration with lazy loading for optimal performance.
 *
 * Routes:
 * - / - Dashboard (protected)
 * - /login - Login page
 * - /products - Product management (protected)
 * - /recommendations - AI recommendations (protected)
 * - /settings - Account settings (protected)
 */

import { createBrowserRouter, Navigate } from 'react-router-dom';
import { lazy, Suspense } from 'react';

// Layouts - Eagerly loaded as they're needed on every route
import { AuthLayout } from './layouts/AuthLayout';
import { DashboardLayout } from './layouts/DashboardLayout';

// Auth guard component - Eagerly loaded
import { ProtectedRoute } from './components/ProtectedRoute';

// Lazy-loaded pages for code splitting
const LoginPage = lazy(() => import('./pages/LoginPage').then(m => ({ default: m.LoginPage })));
const DashboardPage = lazy(() => import('./pages/DashboardPage').then(m => ({ default: m.DashboardPage })));
const ProductsPage = lazy(() => import('./pages/ProductsPage').then(m => ({ default: m.ProductsPage })));
const RecommendationsPage = lazy(() => import('./pages/RecommendationsPage').then(m => ({ default: m.RecommendationsPage })));
const SettingsPage = lazy(() => import('./pages/SettingsPage').then(m => ({ default: m.SettingsPage })));
const SquareSettingsPage = lazy(() => import('./pages/SquareSettingsPage').then(m => ({ default: m.SquareSettingsPage })));

// Loading fallback component
const PageLoader = () => (
  <div className="flex items-center justify-center min-h-screen">
    <div className="spinner h-8 w-8"></div>
  </div>
);

// Wrapper component for Suspense boundaries
const LazyPage = ({ children }: { children: React.ReactNode }) => (
  <Suspense fallback={<PageLoader />}>{children}</Suspense>
);

/**
 * Application router configuration with lazy loading.
 */
export const router = createBrowserRouter([
  {
    path: '/',
    element: <ProtectedRoute />,
    children: [
      {
        element: <DashboardLayout />,
        children: [
          {
            index: true,
            element: (
              <LazyPage>
                <DashboardPage />
              </LazyPage>
            ),
          },
          {
            path: 'products',
            element: (
              <LazyPage>
                <ProductsPage />
              </LazyPage>
            ),
          },
          {
            path: 'recommendations',
            element: (
              <LazyPage>
                <RecommendationsPage />
              </LazyPage>
            ),
          },
          {
            path: 'settings',
            element: (
              <LazyPage>
                <SettingsPage />
              </LazyPage>
            ),
          },
          {
            path: 'settings/square',
            element: (
              <LazyPage>
                <SquareSettingsPage />
              </LazyPage>
            ),
          },
        ],
      },
    ],
  },
  {
    path: '/auth',
    element: <AuthLayout />,
    children: [
      {
        path: 'login',
        element: (
          <LazyPage>
            <LoginPage />
          </LazyPage>
        ),
      },
    ],
  },
  {
    path: '*',
    element: <Navigate to="/" replace />,
  },
]);

/**
 * Route paths for type-safe navigation.
 */
export const ROUTES = {
  HOME: '/',
  LOGIN: '/auth/login',
  PRODUCTS: '/products',
  RECOMMENDATIONS: '/recommendations',
  SETTINGS: '/settings',
} as const;

export type RouteKey = keyof typeof ROUTES;
