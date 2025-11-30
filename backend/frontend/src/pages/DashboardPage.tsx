/**
 * Dashboard page with key metrics.
 */

import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { apiClient } from '../lib/api-client';
import { Card } from '../components/Card';
import { useAuth } from '../contexts/AuthContext';
import { formatCurrency } from '../lib/utils';

interface SalesStats {
  total_sales: number;
  total_revenue: number;
  average_sale: number;
  period_start: string;
  period_end: string;
}

interface SquareStatus {
  is_connected: boolean;
  merchant_id?: string;
}

export function DashboardPage() {
  const { vendor } = useAuth();
  const [salesStats, setSalesStats] = useState<SalesStats | null>(null);
  const [squareStatus, setSquareStatus] = useState<SquareStatus | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const fetchDashboardData = async () => {
    try {
      // Fetch sales stats (last 30 days)
      const stats = await apiClient.get<SalesStats>(
        '/api/v1/sales/stats?days=30'
      );
      setSalesStats(stats);

      // Fetch Square connection status
      const status = await apiClient.get<SquareStatus>(
        '/api/v1/square/status'
      );
      setSquareStatus(status);
    } catch (error) {
      console.error('Failed to fetch dashboard data:', error);
    } finally {
      setIsLoading(false);
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-64">
        <div className="spinner h-8 w-8"></div>
      </div>
    );
  }

  return (
    <div>
      {/* Welcome Header */}
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-900">
          Welcome back, {vendor?.business_name}!
        </h1>
        <p className="text-gray-600 mt-2">
          Here's what's happening with your business
        </p>
      </div>

      {/* Quick Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <Card padding>
          <div className="text-sm text-gray-600 mb-1">Total Sales (30d)</div>
          <div className="text-2xl font-bold text-gray-900">
            {salesStats?.total_sales || 0}
          </div>
        </Card>

        <Card padding>
          <div className="text-sm text-gray-600 mb-1">Revenue (30d)</div>
          <div className="text-2xl font-bold text-green-600">
            {formatCurrency(salesStats?.total_revenue || 0)}
          </div>
        </Card>

        <Card padding>
          <div className="text-sm text-gray-600 mb-1">Average Sale</div>
          <div className="text-2xl font-bold text-gray-900">
            {formatCurrency(salesStats?.average_sale || 0)}
          </div>
        </Card>
      </div>

      {/* Connection Status */}
      {!squareStatus?.is_connected && (
        <Card className="mb-6 border-l-4 border-yellow-500" padding>
          <div className="flex items-start justify-between">
            <div>
              <h3 className="font-semibold text-gray-900 mb-1">
                Connect Square
              </h3>
              <p className="text-sm text-gray-600 mb-3">
                Sync your products and sales to get AI-powered recommendations
              </p>
              <Link
                to="/settings/square"
                className="text-sm text-primary-600 hover:text-primary-700 font-medium"
              >
                Connect Now →
              </Link>
            </div>
          </div>
        </Card>
      )}

      {/* Quick Actions */}
      <h2 className="text-xl font-semibold mb-4">Quick Actions</h2>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-6">
        <Link to="/recommendations">
          <Card hover padding>
            <div className="flex items-center mb-2">
              <div className="h-10 w-10 bg-primary-100 rounded-lg flex items-center justify-center mr-3">
                <span className="text-primary-600 text-xl">🤖</span>
              </div>
              <h3 className="font-semibold text-gray-900">
                AI Recommendations
              </h3>
            </div>
            <p className="text-sm text-gray-600">
              Get smart inventory predictions for your next market
            </p>
          </Card>
        </Link>

        <Link to="/products">
          <Card hover padding>
            <div className="flex items-center mb-2">
              <div className="h-10 w-10 bg-blue-100 rounded-lg flex items-center justify-center mr-3">
                <span className="text-blue-600 text-xl">📦</span>
              </div>
              <h3 className="font-semibold text-gray-900">Products</h3>
            </div>
            <p className="text-sm text-gray-600">
              Manage your product catalog
            </p>
          </Card>
        </Link>

        {squareStatus?.is_connected && (
          <Card padding className="cursor-pointer" hover>
            <div className="flex items-center mb-2">
              <div className="h-10 w-10 bg-green-100 rounded-lg flex items-center justify-center mr-3">
                <span className="text-green-600 text-xl">✓</span>
              </div>
              <h3 className="font-semibold text-gray-900">Square Connected</h3>
            </div>
            <p className="text-sm text-gray-600">
              Syncing products and sales data
            </p>
          </Card>
        )}
      </div>

      {/* Subscription Info */}
      <Card padding>
        <h3 className="font-semibold text-gray-900 mb-2">
          Subscription Status
        </h3>
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm text-gray-600">
              Plan: <span className="font-medium capitalize">{vendor?.subscription_tier}</span>
            </p>
            <p className="text-sm text-gray-600">
              Status: <span className="font-medium capitalize">{vendor?.subscription_status}</span>
            </p>
          </div>
          {vendor?.subscription_status === 'trial' && (
            <span className="badge badge-warning">Trial</span>
          )}
          {vendor?.subscription_status === 'active' && (
            <span className="badge badge-success">Active</span>
          )}
        </div>
      </Card>
    </div>
  );
}
