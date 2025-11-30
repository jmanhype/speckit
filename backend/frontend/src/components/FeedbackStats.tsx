/**
 * Feedback statistics display.
 * Shows overall recommendation accuracy metrics.
 */

import { useEffect, useState } from 'react';
import { apiClient } from '../lib/api-client';
import { Card } from './Card';

interface FeedbackStatsData {
  total_feedback_count: number;
  avg_rating: number | null;
  accuracy_rate: number | null;
  overstock_rate: number | null;
  understock_rate: number | null;
  avg_variance_percentage: number | null;
}

interface FeedbackStatsProps {
  daysBack?: number;
  className?: string;
}

export function FeedbackStats({
  daysBack = 30,
  className = '',
}: FeedbackStatsProps) {
  const [stats, setStats] = useState<FeedbackStatsData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    fetchStats();
  }, [daysBack]);

  const fetchStats = async () => {
    try {
      const data = await apiClient.get<FeedbackStatsData>(
        `/api/v1/feedback/stats?days_back=${daysBack}`
      );
      setStats(data);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  if (isLoading) {
    return (
      <Card padding className={className}>
        <div className="flex items-center justify-center h-32">
          <div className="spinner h-8 w-8"></div>
        </div>
      </Card>
    );
  }

  if (error) {
    return (
      <Card padding className={className}>
        <p className="text-red-600">Failed to load stats: {error}</p>
      </Card>
    );
  }

  if (!stats || stats.total_feedback_count === 0) {
    return (
      <Card padding className={className}>
        <p className="text-gray-600 text-center py-8">
          No feedback data yet. Submit feedback on recommendations to see
          accuracy stats!
        </p>
      </Card>
    );
  }

  return (
    <Card padding className={className}>
      <h3 className="text-lg font-semibold text-gray-900 mb-4">
        Recommendation Accuracy
        <span className="text-sm font-normal text-gray-500 ml-2">
          (Last {daysBack} days)
        </span>
      </h3>

      <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
        {/* Total Feedback */}
        <div className="bg-blue-50 rounded-lg p-3">
          <p className="text-sm text-blue-600 font-medium mb-1">
            Total Feedback
          </p>
          <p className="text-2xl font-bold text-blue-900">
            {stats.total_feedback_count}
          </p>
        </div>

        {/* Average Rating */}
        {stats.avg_rating !== null && (
          <div className="bg-yellow-50 rounded-lg p-3">
            <p className="text-sm text-yellow-600 font-medium mb-1">
              Avg Rating
            </p>
            <p className="text-2xl font-bold text-yellow-900">
              {stats.avg_rating.toFixed(1)} ★
            </p>
          </div>
        )}

        {/* Accuracy Rate */}
        {stats.accuracy_rate !== null && (
          <div className="bg-green-50 rounded-lg p-3">
            <p className="text-sm text-green-600 font-medium mb-1">
              Accuracy Rate
            </p>
            <p className="text-2xl font-bold text-green-900">
              {stats.accuracy_rate.toFixed(0)}%
            </p>
            <p className="text-xs text-green-700 mt-1">Within ±20%</p>
          </div>
        )}

        {/* Overstock Rate */}
        {stats.overstock_rate !== null && (
          <div className="bg-orange-50 rounded-lg p-3">
            <p className="text-sm text-orange-600 font-medium mb-1">
              Overstock Rate
            </p>
            <p className="text-2xl font-bold text-orange-900">
              {stats.overstock_rate.toFixed(0)}%
            </p>
            <p className="text-xs text-orange-700 mt-1">Too much inventory</p>
          </div>
        )}

        {/* Understock Rate */}
        {stats.understock_rate !== null && (
          <div className="bg-red-50 rounded-lg p-3">
            <p className="text-sm text-red-600 font-medium mb-1">
              Understock Rate
            </p>
            <p className="text-2xl font-bold text-red-900">
              {stats.understock_rate.toFixed(0)}%
            </p>
            <p className="text-xs text-red-700 mt-1">Ran out of stock</p>
          </div>
        )}

        {/* Average Variance */}
        {stats.avg_variance_percentage !== null && (
          <div className="bg-gray-50 rounded-lg p-3">
            <p className="text-sm text-gray-600 font-medium mb-1">
              Avg Variance
            </p>
            <p
              className={`text-2xl font-bold ${
                stats.avg_variance_percentage > 0
                  ? 'text-green-900'
                  : stats.avg_variance_percentage < 0
                  ? 'text-red-900'
                  : 'text-gray-900'
              }`}
            >
              {stats.avg_variance_percentage > 0 ? '+' : ''}
              {stats.avg_variance_percentage.toFixed(1)}%
            </p>
            <p className="text-xs text-gray-700 mt-1">From recommended</p>
          </div>
        )}
      </div>

      {/* Interpretation */}
      <div className="mt-4 pt-4 border-t border-gray-200">
        <p className="text-xs text-gray-600">
          {stats.accuracy_rate !== null && stats.accuracy_rate >= 70 && (
            <span className="text-green-600 font-medium">
              ✓ Good accuracy!
            </span>
          )}
          {stats.accuracy_rate !== null &&
            stats.accuracy_rate < 70 &&
            stats.accuracy_rate >= 50 && (
              <span className="text-yellow-600 font-medium">
                ⚠ Moderate accuracy - model is learning from your feedback.
              </span>
            )}
          {stats.accuracy_rate !== null && stats.accuracy_rate < 50 && (
            <span className="text-red-600 font-medium">
              ⚠ Low accuracy - please continue providing feedback to improve
              predictions.
            </span>
          )}
        </p>
      </div>
    </Card>
  );
}
