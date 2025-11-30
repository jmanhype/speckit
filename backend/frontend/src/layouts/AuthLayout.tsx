/**
 * Auth layout for login/registration pages.
 */

import { Outlet } from 'react-router-dom';

export function AuthLayout() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-green-50 to-green-100">
      <div className="flex items-center justify-center min-h-screen px-4">
        <div className="w-full max-w-md">
          <div className="text-center mb-8">
            <h1 className="text-4xl font-bold text-green-600">MarketPrep</h1>
            <p className="text-gray-600 mt-2">Farmers Market Inventory AI</p>
          </div>
          <Outlet />
        </div>
      </div>
    </div>
  );
}
