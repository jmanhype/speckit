/**
 * Feedback form for recommendation accuracy.
 * Allows vendors to submit actual results vs predictions.
 */

import { useState } from 'react';
import { apiClient } from '../lib/api-client';
import { Button } from './Button';

interface FeedbackFormProps {
  recommendationId: string;
  recommendedQuantity: number;
  productName: string;
  onSuccess?: () => void;
  onCancel?: () => void;
}

export function FeedbackForm({
  recommendationId,
  recommendedQuantity,
  productName,
  onSuccess,
  onCancel,
}: FeedbackFormProps) {
  const [formData, setFormData] = useState({
    actual_quantity_brought: recommendedQuantity,
    actual_quantity_sold: 0,
    actual_revenue: 0,
    rating: 3,
    comments: '',
  });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [message, setMessage] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setMessage('');

    try {
      await apiClient.post('/api/v1/feedback', {
        recommendation_id: recommendationId,
        ...formData,
      });

      setMessage('Feedback submitted successfully!');

      if (onSuccess) {
        setTimeout(onSuccess, 1000);
      }
    } catch (error: any) {
      setMessage(`Failed to submit feedback: ${error.message}`);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>
  ) => {
    const { name, value, type } = e.target;

    if (type === 'number') {
      setFormData((prev) => ({ ...prev, [name]: parseFloat(value) || 0 }));
    } else {
      setFormData((prev) => ({ ...prev, [name]: value }));
    }
  };

  // Calculate variance for preview
  const variance = formData.actual_quantity_sold - recommendedQuantity;
  const variancePercentage =
    recommendedQuantity > 0
      ? ((variance / recommendedQuantity) * 100).toFixed(1)
      : '0.0';

  const isAccurate = Math.abs(parseFloat(variancePercentage)) <= 20;
  const isOverstocked = parseFloat(variancePercentage) < -20;
  const isUnderstocked = parseFloat(variancePercentage) > 20;

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-4">
        <p className="text-sm font-medium text-blue-900 mb-1">
          {productName}
        </p>
        <p className="text-sm text-blue-700">
          Recommended: {recommendedQuantity} units
        </p>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Actual Quantity Brought *
        </label>
        <input
          type="number"
          name="actual_quantity_brought"
          value={formData.actual_quantity_brought}
          onChange={handleChange}
          required
          min="0"
          className="input"
          placeholder="How many units did you bring?"
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Actual Quantity Sold *
        </label>
        <input
          type="number"
          name="actual_quantity_sold"
          value={formData.actual_quantity_sold}
          onChange={handleChange}
          required
          min="0"
          max={formData.actual_quantity_brought}
          className="input"
          placeholder="How many units did you sell?"
        />
      </div>

      {formData.actual_quantity_sold > 0 && (
        <div className="bg-gray-50 border border-gray-200 rounded-lg p-3">
          <p className="text-sm font-medium text-gray-700 mb-1">
            Variance Analysis
          </p>
          <div className="grid grid-cols-2 gap-2 text-sm">
            <div>
              <span className="text-gray-600">Variance:</span>{' '}
              <span
                className={`font-semibold ${
                  variance > 0
                    ? 'text-green-600'
                    : variance < 0
                    ? 'text-red-600'
                    : 'text-gray-600'
                }`}
              >
                {variance > 0 ? '+' : ''}
                {variance} units
              </span>
            </div>
            <div>
              <span className="text-gray-600">Percentage:</span>{' '}
              <span
                className={`font-semibold ${
                  parseFloat(variancePercentage) > 0
                    ? 'text-green-600'
                    : parseFloat(variancePercentage) < 0
                    ? 'text-red-600'
                    : 'text-gray-600'
                }`}
              >
                {parseFloat(variancePercentage) > 0 ? '+' : ''}
                {variancePercentage}%
              </span>
            </div>
          </div>

          {isAccurate && (
            <p className="mt-2 text-xs text-green-600 font-medium">
              ✓ Within acceptable range (±20%)
            </p>
          )}
          {isOverstocked && (
            <p className="mt-2 text-xs text-orange-600 font-medium">
              ⚠ Overstocked (brought too much)
            </p>
          )}
          {isUnderstocked && (
            <p className="mt-2 text-xs text-red-600 font-medium">
              ⚠ Understocked (could have sold more)
            </p>
          )}
        </div>
      )}

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Actual Revenue ($)
        </label>
        <input
          type="number"
          name="actual_revenue"
          value={formData.actual_revenue}
          onChange={handleChange}
          min="0"
          step="0.01"
          className="input"
          placeholder="Total revenue from sales"
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Rating *
        </label>
        <div className="flex items-center gap-2">
          {[1, 2, 3, 4, 5].map((star) => (
            <button
              key={star}
              type="button"
              onClick={() =>
                setFormData((prev) => ({ ...prev, rating: star }))
              }
              className={`text-2xl ${
                star <= formData.rating
                  ? 'text-yellow-400'
                  : 'text-gray-300'
              } hover:text-yellow-400 transition-colors`}
            >
              ★
            </button>
          ))}
          <span className="ml-2 text-sm text-gray-600">
            {formData.rating} star{formData.rating !== 1 ? 's' : ''}
          </span>
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Comments (optional)
        </label>
        <textarea
          name="comments"
          value={formData.comments}
          onChange={handleChange}
          rows={3}
          className="input"
          placeholder="Any additional feedback about this recommendation?"
        />
      </div>

      {message && (
        <div
          className={`p-3 rounded-md ${
            message.includes('success')
              ? 'bg-green-50 text-green-800'
              : 'bg-red-50 text-red-800'
          }`}
        >
          {message}
        </div>
      )}

      <div className="flex gap-3 justify-end">
        {onCancel && (
          <Button type="button" onClick={onCancel} variant="secondary">
            Cancel
          </Button>
        )}
        <Button type="submit" isLoading={isSubmitting}>
          Submit Feedback
        </Button>
      </div>
    </form>
  );
}
