/**
 * Dashboard layout with navigation.
 */

import { Outlet, NavLink } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { ROUTES } from '../router';
import { OfflineIndicator } from '../components/OfflineIndicator';

export function DashboardLayout() {
  const { vendor, logout } = useAuth();

  const navigation = [
    { name: 'Dashboard', path: ROUTES.HOME },
    { name: 'Products', path: ROUTES.PRODUCTS },
    { name: 'Recommendations', path: ROUTES.RECOMMENDATIONS },
    { name: 'Settings', path: ROUTES.SETTINGS },
  ];

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Offline indicator */}
      <OfflineIndicator />

      {/* Navigation */}
      <nav className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16">
            <div className="flex">
              {/* Logo */}
              <div className="flex-shrink-0 flex items-center">
                <span className="text-xl font-bold text-green-600">
                  MarketPrep
                </span>
              </div>

              {/* Navigation links */}
              <div className="hidden sm:ml-6 sm:flex sm:space-x-8">
                {navigation.map((item) => (
                  <NavLink
                    key={item.path}
                    to={item.path}
                    className={({ isActive }) =>
                      `inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium ${
                        isActive
                          ? 'border-green-500 text-gray-900'
                          : 'border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700'
                      }`
                    }
                  >
                    {item.name}
                  </NavLink>
                ))}
              </div>
            </div>

            {/* User menu */}
            <div className="flex items-center">
              <span className="text-sm text-gray-700 mr-4">
                {vendor?.business_name}
              </span>
              <button
                onClick={logout}
                className="text-sm text-gray-700 hover:text-gray-900"
              >
                Logout
              </button>
            </div>
          </div>
        </div>
      </nav>

      {/* Page content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <Outlet />
      </main>
    </div>
  );
}
