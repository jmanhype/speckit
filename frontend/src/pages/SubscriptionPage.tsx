/**
 * Subscription management and upgrade page
 *
 * Features:
 * - View current subscription tier
 * - Compare tier features
 * - Upgrade/downgrade subscription
 * - View usage and limits
 * - Manage payment methods
 */

import React, { useState, useEffect } from 'react';
import { apiClient } from '../lib/api-client';

interface SubscriptionTier {
  name: string;
  price_monthly: number;
  price_yearly: number;
  features: string[];
  limits: {
    recommendations: number | null;
    products: number | null;
    venues: number | null;
  };
  popular?: boolean;
}

const TIERS: SubscriptionTier[] = [
  {
    name: 'Free',
    price_monthly: 0,
    price_yearly: 0,
    features: [
      'Up to 50 recommendations per month',
      'Up to 20 products',
      'Up to 2 venues',
      'Basic weather integration',
      'Email support',
    ],
    limits: {
      recommendations: 50,
      products: 20,
      venues: 2,
    },
  },
  {
    name: 'Pro',
    price_monthly: 29,
    price_yearly: 290, // 2 months free
    features: [
      'Up to 500 recommendations per month',
      'Up to 100 products',
      'Up to 10 venues',
      'Advanced weather forecasting',
      'Event detection',
      'Priority email support',
      'Export to CSV',
    ],
    limits: {
      recommendations: 500,
      products: 100,
      venues: 10,
    },
    popular: true,
  },
  {
    name: 'Enterprise',
    price_monthly: 99,
    price_yearly: 990,
    features: [
      'Unlimited recommendations',
      'Unlimited products',
      'Unlimited venues',
      'Custom ML model training',
      'Dedicated account manager',
      '24/7 phone support',
      'API access',
      'White-label option',
    ],
    limits: {
      recommendations: null,
      products: null,
      venues: null,
    },
  },
];

interface CurrentSubscription {
  tier: string;
  status: string;
  current_period_end: string;
  usage: {
    recommendations: number;
    products: number;
    venues: number;
  };
}

export const SubscriptionPage: React.FC = () => {
  const [currentSubscription, setCurrentSubscription] = useState<CurrentSubscription | null>(null);
  const [billingPeriod, setBillingPeriod] = useState<'monthly' | 'yearly'>('monthly');
  const [loading, setLoading] = useState(true);
  const [upgrading, setUpgrading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchSubscription();
  }, []);

  const fetchSubscription = async () => {
    try {
      const response = await apiClient.get('/subscriptions/current');
      setCurrentSubscription(response.data);
    } catch (err: any) {
      if (err.response?.status === 404) {
        // No subscription yet (free tier)
        setCurrentSubscription({
          tier: 'Free',
          status: 'active',
          current_period_end: '',
          usage: { recommendations: 0, products: 0, venues: 0 },
        });
      } else {
        setError('Failed to load subscription');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleUpgrade = async (tierName: string) => {
    if (upgrading) return;

    setUpgrading(true);
    setError(null);

    try {
      // Create Stripe checkout session
      const response = await apiClient.post('/subscriptions/create-checkout', {
        tier: tierName.toLowerCase(),
        billing_period: billingPeriod,
      });

      // Redirect to Stripe checkout
      window.location.href = response.data.checkout_url;
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to start upgrade process');
      setUpgrading(false);
    }
  };

  const getUsagePercentage = (used: number, limit: number | null): number => {
    if (limit === null) return 0; // Unlimited
    return Math.min((used / limit) * 100, 100);
  };

  if (loading) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="flex justify-center items-center h-64">
          <div className="text-gray-600">Loading subscription...</div>
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8">
      <h1 className="text-3xl font-bold mb-8">Subscription & Billing</h1>

      {error && (
        <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg">
          <p className="text-red-700">{error}</p>
        </div>
      )}

      {/* Current Subscription */}
      {currentSubscription && (
        <div className="mb-8 p-6 bg-white rounded-lg shadow-md">
          <h2 className="text-xl font-semibold mb-4">Current Plan</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <p className="text-sm text-gray-600">Tier</p>
              <p className="text-2xl font-bold text-blue-600">{currentSubscription.tier}</p>
              <p className="text-sm text-gray-500 mt-1">Status: {currentSubscription.status}</p>
            </div>

            {/* Usage Stats */}
            <div>
              <p className="text-sm text-gray-600 mb-3">Usage This Month</p>
              <div className="space-y-3">
                <div>
                  <div className="flex justify-between text-sm mb-1">
                    <span>Recommendations</span>
                    <span>
                      {currentSubscription.usage.recommendations} /{' '}
                      {TIERS.find((t) => t.name === currentSubscription.tier)?.limits.recommendations || '∞'}
                    </span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div
                      className="bg-blue-600 h-2 rounded-full"
                      style={{
                        width: `${getUsagePercentage(
                          currentSubscription.usage.recommendations,
                          TIERS.find((t) => t.name === currentSubscription.tier)?.limits.recommendations || null
                        )}%`,
                      }}
                    ></div>
                  </div>
                </div>

                <div>
                  <div className="flex justify-between text-sm mb-1">
                    <span>Products</span>
                    <span>
                      {currentSubscription.usage.products} /{' '}
                      {TIERS.find((t) => t.name === currentSubscription.tier)?.limits.products || '∞'}
                    </span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div
                      className="bg-green-600 h-2 rounded-full"
                      style={{
                        width: `${getUsagePercentage(
                          currentSubscription.usage.products,
                          TIERS.find((t) => t.name === currentSubscription.tier)?.limits.products || null
                        )}%`,
                      }}
                    ></div>
                  </div>
                </div>

                <div>
                  <div className="flex justify-between text-sm mb-1">
                    <span>Venues</span>
                    <span>
                      {currentSubscription.usage.venues} /{' '}
                      {TIERS.find((t) => t.name === currentSubscription.tier)?.limits.venues || '∞'}
                    </span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div
                      className="bg-purple-600 h-2 rounded-full"
                      style={{
                        width: `${getUsagePercentage(
                          currentSubscription.usage.venues,
                          TIERS.find((t) => t.name === currentSubscription.tier)?.limits.venues || null
                        )}%`,
                      }}
                    ></div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Billing Period Toggle */}
      <div className="flex justify-center mb-8">
        <div className="inline-flex rounded-lg border border-gray-300 bg-white p-1">
          <button
            onClick={() => setBillingPeriod('monthly')}
            className={`px-6 py-2 rounded-md text-sm font-medium transition-colors ${
              billingPeriod === 'monthly'
                ? 'bg-blue-600 text-white'
                : 'text-gray-700 hover:bg-gray-100'
            }`}
          >
            Monthly
          </button>
          <button
            onClick={() => setBillingPeriod('yearly')}
            className={`px-6 py-2 rounded-md text-sm font-medium transition-colors ${
              billingPeriod === 'yearly'
                ? 'bg-blue-600 text-white'
                : 'text-gray-700 hover:bg-gray-100'
            }`}
          >
            Yearly
            <span className="ml-2 text-xs bg-green-100 text-green-800 px-2 py-1 rounded">
              Save 16%
            </span>
          </button>
        </div>
      </div>

      {/* Pricing Tiers */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        {TIERS.map((tier) => {
          const isCurrent = currentSubscription?.tier === tier.name;
          const price = billingPeriod === 'monthly' ? tier.price_monthly : tier.price_yearly / 12;

          return (
            <div
              key={tier.name}
              className={`relative p-6 rounded-lg border-2 ${
                tier.popular
                  ? 'border-blue-600 shadow-lg'
                  : isCurrent
                  ? 'border-green-600'
                  : 'border-gray-200'
              } bg-white`}
            >
              {tier.popular && (
                <div className="absolute top-0 left-1/2 transform -translate-x-1/2 -translate-y-1/2">
                  <span className="bg-blue-600 text-white text-xs font-bold px-3 py-1 rounded-full">
                    POPULAR
                  </span>
                </div>
              )}

              {isCurrent && (
                <div className="absolute top-0 left-1/2 transform -translate-x-1/2 -translate-y-1/2">
                  <span className="bg-green-600 text-white text-xs font-bold px-3 py-1 rounded-full">
                    CURRENT PLAN
                  </span>
                </div>
              )}

              <div className="text-center mb-6">
                <h3 className="text-2xl font-bold text-gray-900">{tier.name}</h3>
                <div className="mt-4">
                  <span className="text-4xl font-bold">${price.toFixed(0)}</span>
                  <span className="text-gray-600">/month</span>
                </div>
                {billingPeriod === 'yearly' && tier.price_yearly > 0 && (
                  <p className="text-sm text-gray-500 mt-1">
                    ${tier.price_yearly}/year (billed annually)
                  </p>
                )}
              </div>

              <ul className="space-y-3 mb-6">
                {tier.features.map((feature, index) => (
                  <li key={index} className="flex items-start">
                    <svg
                      className="w-5 h-5 text-green-500 mr-2 flex-shrink-0"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                    </svg>
                    <span className="text-sm text-gray-700">{feature}</span>
                  </li>
                ))}
              </ul>

              <button
                onClick={() => handleUpgrade(tier.name)}
                disabled={isCurrent || upgrading}
                className={`w-full py-3 px-4 rounded-md font-medium transition-colors ${
                  isCurrent
                    ? 'bg-gray-100 text-gray-500 cursor-not-allowed'
                    : tier.popular
                    ? 'bg-blue-600 text-white hover:bg-blue-700'
                    : 'bg-gray-800 text-white hover:bg-gray-900'
                } disabled:opacity-50`}
              >
                {isCurrent ? 'Current Plan' : upgrading ? 'Processing...' : 'Choose Plan'}
              </button>
            </div>
          );
        })}
      </div>

      {/* FAQ */}
      <div className="bg-white p-6 rounded-lg shadow-md">
        <h2 className="text-xl font-semibold mb-4">Frequently Asked Questions</h2>
        <div className="space-y-4">
          <div>
            <h3 className="font-medium text-gray-900">Can I change plans anytime?</h3>
            <p className="text-sm text-gray-600 mt-1">
              Yes! You can upgrade or downgrade at any time. Upgrades are prorated immediately, and downgrades take
              effect at the end of your current billing period.
            </p>
          </div>
          <div>
            <h3 className="font-medium text-gray-900">What happens if I exceed my limits?</h3>
            <p className="text-sm text-gray-600 mt-1">
              You'll receive a notification when you reach 80% of your limit. If you exceed your limit, you'll need
              to upgrade to continue using the service.
            </p>
          </div>
          <div>
            <h3 className="font-medium text-gray-900">Is there a free trial?</h3>
            <p className="text-sm text-gray-600 mt-1">
              The Free plan is available indefinitely. Paid plans include a 14-day money-back guarantee.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
