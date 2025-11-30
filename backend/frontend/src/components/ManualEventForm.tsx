/**
 * Manual event entry form.
 * Allows vendors to manually add local events that may impact sales.
 */

import { useState } from 'react';
import { apiClient } from '../lib/api-client';
import { Button } from './Button';

interface ManualEventFormProps {
  onSuccess?: () => void;
  onCancel?: () => void;
}

export function ManualEventForm({ onSuccess, onCancel }: ManualEventFormProps) {
  const [formData, setFormData] = useState({
    name: '',
    event_date: '',
    location: '',
    expected_attendance: 100,
    is_special: false,
    description: '',
  });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [message, setMessage] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setMessage('');

    try {
      await apiClient.post('/api/v1/events', formData);
      setMessage('Event created successfully!');

      // Reset form
      setFormData({
        name: '',
        event_date: '',
        location: '',
        expected_attendance: 100,
        is_special: false,
        description: '',
      });

      if (onSuccess) {
        onSuccess();
      }
    } catch (error: any) {
      setMessage(`Failed to create event: ${error.message}`);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>
  ) => {
    const { name, value, type } = e.target;

    if (type === 'checkbox') {
      const checked = (e.target as HTMLInputElement).checked;
      setFormData((prev) => ({ ...prev, [name]: checked }));
    } else if (type === 'number') {
      setFormData((prev) => ({ ...prev, [name]: parseInt(value) || 0 }));
    } else {
      setFormData((prev) => ({ ...prev, [name]: value }));
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Event Name *
        </label>
        <input
          type="text"
          name="name"
          value={formData.name}
          onChange={handleChange}
          required
          className="input"
          placeholder="e.g., Summer Music Festival"
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Event Date & Time *
        </label>
        <input
          type="datetime-local"
          name="event_date"
          value={formData.event_date}
          onChange={handleChange}
          required
          className="input"
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Location
        </label>
        <input
          type="text"
          name="location"
          value={formData.location}
          onChange={handleChange}
          className="input"
          placeholder="e.g., City Park"
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Expected Attendance
        </label>
        <input
          type="number"
          name="expected_attendance"
          value={formData.expected_attendance}
          onChange={handleChange}
          min="1"
          className="input"
        />
      </div>

      <div className="flex items-center gap-2">
        <input
          type="checkbox"
          name="is_special"
          id="is_special"
          checked={formData.is_special}
          onChange={handleChange}
          className="w-4 h-4 rounded border-gray-300"
        />
        <label htmlFor="is_special" className="text-sm text-gray-700">
          Mark as special/major event (high impact on sales)
        </label>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Description (optional)
        </label>
        <textarea
          name="description"
          value={formData.description}
          onChange={handleChange}
          rows={3}
          className="input"
          placeholder="Additional details about the event..."
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
          <Button
            type="button"
            onClick={onCancel}
            variant="secondary"
          >
            Cancel
          </Button>
        )}
        <Button type="submit" isLoading={isSubmitting}>
          Create Event
        </Button>
      </div>
    </form>
  );
}
