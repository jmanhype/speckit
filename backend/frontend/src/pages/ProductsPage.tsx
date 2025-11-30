/**
 * Products page with catalog management.
 */

import { useState, useEffect } from 'react';
import { apiClient } from '../lib/api-client';
import { Button } from '../components/Button';
import { Card } from '../components/Card';
import { formatCurrency, formatDate } from '../lib/utils';

interface Product {
  id: string;
  name: string;
  description?: string;
  price: number;
  category?: string;
  is_active: boolean;
  is_seasonal: boolean;
  square_item_id?: string;
  square_synced_at?: string;
}

export function ProductsPage() {
  const [products, setProducts] = useState<Product[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isSyncing, setIsSyncing] = useState(false);
  const [syncMessage, setSyncMessage] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string>('all');

  useEffect(() => {
    fetchProducts();
  }, []);

  const fetchProducts = async () => {
    try {
      const data = await apiClient.get<Product[]>(
        '/api/v1/products?active_only=false&limit=100'
      );
      setProducts(data);
    } catch (error) {
      console.error('Failed to fetch products:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSync = async () => {
    setIsSyncing(true);
    setSyncMessage('');

    try {
      const data = await apiClient.post<{
        created: number;
        updated: number;
        total: number;
      }>('/api/v1/products/sync');

      setSyncMessage(
        `Sync complete: ${data.created} created, ${data.updated} updated`
      );
      await fetchProducts();
    } catch (error: any) {
      setSyncMessage(`Sync failed: ${error.message}`);
    } finally {
      setIsSyncing(false);
    }
  };

  // Get unique categories
  const categories = Array.from(
    new Set(
      products
        .map((p) => p.category)
        .filter((c) => c !== null && c !== undefined)
    )
  );

  // Filter products by category
  const filteredProducts =
    selectedCategory === 'all'
      ? products
      : products.filter((p) => p.category === selectedCategory);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-64">
        <div className="spinner h-8 w-8"></div>
      </div>
    );
  }

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-3xl font-bold text-gray-900">Products</h1>
        <Button onClick={handleSync} isLoading={isSyncing} size="sm">
          Sync from Square
        </Button>
      </div>

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

      {/* Category Filter */}
      {categories.length > 0 && (
        <div className="mb-6">
          <div className="flex flex-wrap gap-2">
            <button
              onClick={() => setSelectedCategory('all')}
              className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                selectedCategory === 'all'
                  ? 'bg-primary-600 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              All ({products.length})
            </button>
            {categories.map((category) => (
              <button
                key={category}
                onClick={() => setSelectedCategory(category as string)}
                className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                  selectedCategory === category
                    ? 'bg-primary-600 text-white'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                {category} (
                {products.filter((p) => p.category === category).length})
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Products Grid */}
      {filteredProducts.length === 0 ? (
        <Card padding>
          <div className="text-center py-12">
            <p className="text-gray-600 mb-4">
              No products found.
              {products.length === 0 && ' Sync from Square to get started!'}
            </p>
            {products.length === 0 && (
              <Button onClick={handleSync} isLoading={isSyncing}>
                Sync from Square
              </Button>
            )}
          </div>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredProducts.map((product) => (
            <Card key={product.id} padding>
              <div className="flex justify-between items-start mb-2">
                <h3 className="font-semibold text-gray-900">{product.name}</h3>
                {!product.is_active && (
                  <span className="badge bg-gray-200 text-gray-600">
                    Inactive
                  </span>
                )}
                {product.is_seasonal && (
                  <span className="badge badge-info">Seasonal</span>
                )}
              </div>

              {product.description && (
                <p className="text-sm text-gray-600 mb-3 truncate-2-lines">
                  {product.description}
                </p>
              )}

              <div className="space-y-2">
                <div className="flex justify-between items-center">
                  <span className="text-sm text-gray-600">Price</span>
                  <span className="font-semibold text-green-600">
                    {formatCurrency(product.price)}
                  </span>
                </div>

                {product.category && (
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-gray-600">Category</span>
                    <span className="text-sm font-medium">
                      {product.category}
                    </span>
                  </div>
                )}

                {product.square_item_id && (
                  <div className="pt-2 border-t">
                    <div className="flex items-center justify-between">
                      <span className="text-xs text-gray-500">
                        Square Product
                      </span>
                      {product.square_synced_at && (
                        <span className="text-xs text-gray-500">
                          Synced {formatDate(new Date(product.square_synced_at))}
                        </span>
                      )}
                    </div>
                  </div>
                )}
              </div>
            </Card>
          ))}
        </div>
      )}

      {/* Product Count */}
      <div className="mt-6 text-center text-sm text-gray-600">
        Showing {filteredProducts.length} of {products.length} products
      </div>
    </div>
  );
}
