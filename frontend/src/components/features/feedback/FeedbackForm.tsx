/**
 * Feedback form component
 *
 * Allows vendors to provide feedback on recommendations:
 * - Actual quantity brought/sold
 * - Revenue generated
 * - Star rating
 * - Comments
 */

import React, { useState } from 'react';
import { apiClient } from '../../../lib/api-client';

interface FeedbackFormProps {
  recommendationId: string;
  productName: string;
  recommendedQuantity: number;
  onSubmitSuccess?: () => void;
  onCancel?: () => void;
}

export const FeedbackForm: React.FC<FeedbackFormProps> = ({
  recommendationId,
  productName,
  recommendedQuantity,
  onSubmitSuccess,
  onCancel,
}) => {
  const [formData, setFormData] = useState({
    actual_quantity_brought: '',
    actual_quantity_sold: '',
    actual_revenue: '',
    rating: 0,
    comments: '',
  });

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsSubmitting(true);

    try {
      await apiClient.post('/feedback', {
        recommendation_id: recommendationId,
        actual_quantity_brought: formData.actual_quantity_brought ? parseInt(formData.actual_quantity_brought) : null,
        actual_quantity_sold: formData.actual_quantity_sold ? parseInt(formData.actual_quantity_sold) : null,
        actual_revenue: formData.actual_revenue ? parseFloat(formData.actual_revenue) : null,
        rating: formData.rating || null,
        comments: formData.comments || null,
      });

      if (onSubmitSuccess) {
        onSubmitSuccess();
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to submit feedback');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleRatingClick = (rating: number) => {
    setFormData({ ...formData, rating });
  };

  return (
    <div className="bg-white p-6 rounded-lg shadow-md">
      <h2 className="text-2xl font-semibold mb-4">
        Feedback for {productName}
      </h2>

      <div className="mb-4 p-3 bg-blue-50 rounded">
        <p className="text-sm text-gray-700">
          <span className="font-medium">Recommended quantity:</span> {recommendedQuantity}
        </p>
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded">
          <p className="text-sm text-red-700">{error}</p>
        </div>
      )}

      <form onSubmit={handleSubmit}>
        {/* Quantity Brought */}
        <div className="mb-4">
          <label htmlFor="actual_quantity_brought" className="block text-sm font-medium text-gray-700 mb-1">
            How many did you bring?
          </label>
          <input
            type="number"
            id="actual_quantity_brought"
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            value={formData.actual_quantity_brought}
            onChange={(e) => setFormData({ ...formData, actual_quantity_brought: e.target.value })}
            min="0"
          />
        </div>

        {/* Quantity Sold */}
        <div className="mb-4">
          <label htmlFor="actual_quantity_sold" className="block text-sm font-medium text-gray-700 mb-1">
            How many did you sell? <span className="text-red-500">*</span>
          </label>
          <input
            type="number"
            id="actual_quantity_sold"
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            value={formData.actual_quantity_sold}
            onChange={(e) => setFormData({ ...formData, actual_quantity_sold: e.target.value })}
            required
            min="0"
          />
          <p className="mt-1 text-xs text-gray-500">
            This helps improve future recommendations
          </p>
        </div>

        {/* Revenue */}
        <div className="mb-4">
          <label htmlFor="actual_revenue" className="block text-sm font-medium text-gray-700 mb-1">
            Total revenue ($)
          </label>
          <input
            type="number"
            id="actual_revenue"
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            value={formData.actual_revenue}
            onChange={(e) => setFormData({ ...formData, actual_revenue: e.target.value })}
            min="0"
            step="0.01"
            placeholder="0.00"
          />
        </div>

        {/* Star Rating */}
        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            How helpful was this recommendation?
          </label>
          <div className="flex gap-2">
            {[1, 2, 3, 4, 5].map((star) => (
              <button
                key={star}
                type="button"
                onClick={() => handleRatingClick(star)}
                className={`text-3xl focus:outline-none transition-colors ${
                  star <= formData.rating ? 'text-yellow-400' : 'text-gray-300'
                } hover:text-yellow-400`}
                aria-label={`Rate ${star} stars`}
              >
                ★
              </button>
            ))}
          </div>
          {formData.rating > 0 && (
            <p className="mt-1 text-sm text-gray-600">
              {formData.rating} star{formData.rating !== 1 ? 's' : ''}
            </p>
          )}
        </div>

        {/* Comments */}
        <div className="mb-6">
          <label htmlFor="comments" className="block text-sm font-medium text-gray-700 mb-1">
            Additional comments
          </label>
          <textarea
            id="comments"
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            rows={4}
            value={formData.comments}
            onChange={(e) => setFormData({ ...formData, comments: e.target.value })}
            placeholder="Share any insights that could improve future recommendations..."
          />
        </div>

        {/* Actions */}
        <div className="flex justify-end gap-3">
          {onCancel && (
            <button
              type="button"
              onClick={onCancel}
              className="px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50 transition-colors"
              disabled={isSubmitting}
            >
              Cancel
            </button>
          )}
          <button
            type="submit"
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            disabled={isSubmitting || !formData.actual_quantity_sold}
          >
            {isSubmitting ? 'Submitting...' : 'Submit Feedback'}
          </button>
        </div>
      </form>
    </div>
  );
};
