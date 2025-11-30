/**
 * Square integration settings page.
 */

import { useState, useEffect } from 'react';
import { apiClient } from '../lib/api-client';
import { Button } from '../components/Button';
import { Card } from '../components/Card';

interface ConnectionStatus {
  is_connected: boolean;
  merchant_id?: string;
  connected_at?: string;
  scopes?: string[];
}

export function SquareSettingsPage() {
  const [status, setStatus] = useState<ConnectionStatus | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSyncing, setIsSyncing] = useState(false);
  const [syncMessage, setSyncMessage] = useState('');

  // Fetch connection status on mount
  useEffect(() => {
    fetchStatus();
  }, []);

  const fetchStatus = async () => {
    try {
      const data = await apiClient.get<ConnectionStatus>(
        '/api/v1/square/status'
      );
      setStatus(data);
    } catch (error) {
      console.error('Failed to fetch status:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleConnect = async () => {
    try {
      const data = await apiClient.get<{
        authorization_url: string;
        state: string;
      }>('/api/v1/square/connect');

      // Redirect to Square OAuth
      window.location.href = data.authorization_url;
    } catch (error) {
      console.error('Failed to initiate OAuth:', error);
    }
  };

  const handleDisconnect = async () => {
    if (!confirm('Are you sure you want to disconnect Square?')) {
      return;
    }

    try {
      await apiClient.delete('/api/v1/square/disconnect');
      setStatus({ is_connected: false });
      setSyncMessage('Square disconnected successfully');
    } catch (error) {
      console.error('Failed to disconnect:', error);
    }
  };

  const handleSyncProducts = async () => {
    setIsSyncing(true);
    setSyncMessage('');

    try {
      const data = await apiClient.post<{
        created: number;
        updated: number;
        total: number;
      }>('/api/v1/products/sync');

      setSyncMessage(
        `Product sync complete: ${data.created} created, ${data.updated} updated`
      );
    } catch (error: any) {
      setSyncMessage(`Sync failed: ${error.message}`);
    } finally {
      setIsSyncing(false);
    }
  };

  const handleSyncSales = async () => {
    setIsSyncing(true);
    setSyncMessage('');

    try {
      const data = await apiClient.post<{
        created: number;
        updated: number;
        total: number;
      }>('/api/v1/sales/sync?days_back=30');

      setSyncMessage(
        `Sales sync complete: ${data.created} created, ${data.updated} updated`
      );
    } catch (error: any) {
      setSyncMessage(`Sync failed: ${error.message}`);
    } finally {
      setIsSyncing(false);
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
    <div className="max-w-2xl mx-auto">
      <h1 className="text-3xl font-bold text-gray-900 mb-6">
        Square Integration
      </h1>

      {/* Connection Status Card */}
      <Card className="mb-6" padding>
        <h2 className="text-xl font-semibold mb-4">Connection Status</h2>

        {status?.is_connected ? (
          <div className="space-y-4">
            <div className="flex items-center">
              <div className="h-3 w-3 bg-green-500 rounded-full mr-3"></div>
              <span className="text-green-700 font-medium">Connected</span>
            </div>

            {status.merchant_id && (
              <div>
                <p className="text-sm text-gray-600">Merchant ID</p>
                <p className="font-mono text-sm">{status.merchant_id}</p>
              </div>
            )}

            {status.connected_at && (
              <div>
                <p className="text-sm text-gray-600">Connected On</p>
                <p className="text-sm">
                  {new Date(status.connected_at).toLocaleString()}
                </p>
              </div>
            )}

            {status.scopes && status.scopes.length > 0 && (
              <div>
                <p className="text-sm text-gray-600 mb-2">Permissions</p>
                <div className="flex flex-wrap gap-2">
                  {status.scopes.map((scope) => (
                    <span
                      key={scope}
                      className="badge badge-info"
                    >
                      {scope}
                    </span>
                  ))}
                </div>
              </div>
            )}

            <div className="pt-4">
              <Button variant="danger" onClick={handleDisconnect}>
                Disconnect Square
              </Button>
            </div>
          </div>
        ) : (
          <div className="space-y-4">
            <div className="flex items-center">
              <div className="h-3 w-3 bg-gray-300 rounded-full mr-3"></div>
              <span className="text-gray-600">Not Connected</span>
            </div>

            <p className="text-gray-600">
              Connect your Square account to sync products and sales data.
            </p>

            <Button onClick={handleConnect}>Connect Square</Button>
          </div>
        )}
      </Card>

      {/* Sync Controls Card */}
      {status?.is_connected && (
        <Card padding>
          <h2 className="text-xl font-semibold mb-4">Sync Data</h2>

          <p className="text-gray-600 mb-4">
            Sync your products and sales from Square.
          </p>

          {syncMessage && (
            <div
              className={`p-3 rounded-md mb-4 ${
                syncMessage.includes('failed')
                  ? 'bg-red-50 text-red-800'
                  : 'bg-green-50 text-green-800'
              }`}
            >
              {syncMessage}
            </div>
          )}

          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <div>
                <p className="font-medium">Products</p>
                <p className="text-sm text-gray-600">
                  Sync catalog items from Square
                </p>
              </div>
              <Button
                onClick={handleSyncProducts}
                isLoading={isSyncing}
                size="sm"
              >
                Sync Products
              </Button>
            </div>

            <div className="border-t pt-3"></div>

            <div className="flex items-center justify-between">
              <div>
                <p className="font-medium">Sales</p>
                <p className="text-sm text-gray-600">
                  Sync orders from last 30 days
                </p>
              </div>
              <Button
                onClick={handleSyncSales}
                isLoading={isSyncing}
                size="sm"
              >
                Sync Sales
              </Button>
            </div>
          </div>
        </Card>
      )}
    </div>
  );
}
