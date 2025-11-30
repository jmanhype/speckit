/**
 * Retention Policy Configuration UI
 *
 * Allows vendors to configure data retention policies per data type.
 */

import React, { useState, useEffect } from 'react';

interface RetentionPolicy {
  id: string;
  data_type: string;
  retention_days: number;
  description: string;
  legal_basis: string;
  auto_delete_enabled: boolean;
  anonymize_instead: boolean;
  is_active: boolean;
  effective_date: string;
}

interface RetentionStatus {
  data_type: string;
  retention_days: number;
  cutoff_date: string;
  affected_records: number;
  auto_delete: boolean;
  anonymize_instead: boolean;
}

interface Props {
  vendorId: string;
}

export const RetentionPolicySettings: React.FC<Props> = ({ vendorId }) => {
  const [policies, setPolicies] = useState<RetentionPolicy[]>([]);
  const [status, setStatus] = useState<RetentionStatus[]>([]);
  const [loading, setLoading] = useState(true);
  const [editingPolicy, setEditingPolicy] = useState<string | null>(null);
  const [showCreateForm, setShowCreateForm] = useState(false);

  // Form state
  const [formData, setFormData] = useState({
    data_type: 'sales',
    retention_days: 365,
    description: '',
    legal_basis: 'contract',
    auto_delete_enabled: true,
    anonymize_instead: false,
  });

  useEffect(() => {
    loadPolicies();
    loadStatus();
  }, [vendorId]);

  const loadPolicies = async () => {
    try {
      const response = await fetch(`/api/v1/retention/policies?vendor_id=${vendorId}`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
        },
      });

      if (response.ok) {
        const data = await response.json();
        setPolicies(data.policies || []);
      }
    } catch (error) {
      console.error('Error loading policies:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadStatus = async () => {
    try {
      const response = await fetch(`/api/v1/retention/status?vendor_id=${vendorId}`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
        },
      });

      if (response.ok) {
        const data = await response.json();
        setStatus(data.policies || []);
      }
    } catch (error) {
      console.error('Error loading status:', error);
    }
  };

  const handleCreatePolicy = async (e: React.FormEvent) => {
    e.preventDefault();

    try {
      const response = await fetch('/api/v1/retention/policies', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
        },
        body: JSON.stringify({
          vendor_id: vendorId,
          ...formData,
        }),
      });

      if (response.ok) {
        setShowCreateForm(false);
        setFormData({
          data_type: 'sales',
          retention_days: 365,
          description: '',
          legal_basis: 'contract',
          auto_delete_enabled: true,
          anonymize_instead: false,
        });
        loadPolicies();
        loadStatus();
      } else {
        alert('Failed to create policy');
      }
    } catch (error) {
      console.error('Error creating policy:', error);
      alert('Error creating policy');
    }
  };

  const handleUpdatePolicy = async (policyId: string, updates: Partial<RetentionPolicy>) => {
    try {
      const response = await fetch(`/api/v1/retention/policies/${policyId}`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
        },
        body: JSON.stringify(updates),
      });

      if (response.ok) {
        setEditingPolicy(null);
        loadPolicies();
        loadStatus();
      } else {
        alert('Failed to update policy');
      }
    } catch (error) {
      console.error('Error updating policy:', error);
      alert('Error updating policy');
    }
  };

  const handleDeletePolicy = async (policyId: string) => {
    if (!confirm('Are you sure you want to deactivate this retention policy?')) {
      return;
    }

    try {
      const response = await fetch(`/api/v1/retention/policies/${policyId}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
        },
      });

      if (response.ok) {
        loadPolicies();
        loadStatus();
      } else {
        alert('Failed to delete policy');
      }
    } catch (error) {
      console.error('Error deleting policy:', error);
      alert('Error deleting policy');
    }
  };

  const dataTypeLabels: Record<string, string> = {
    sales: 'Sales Data',
    recommendations: 'Recommendations',
    audit_logs: 'Audit Logs',
    products: 'Product Data',
  };

  const legalBasisLabels: Record<string, string> = {
    contract: 'Contract Performance',
    legal_obligation: 'Legal Obligation',
    legitimate_interest: 'Legitimate Interest',
    consent: 'User Consent',
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto p-6">
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-gray-900 mb-2">
          Data Retention Policies
        </h2>
        <p className="text-gray-600">
          Configure how long different types of data are retained before automatic deletion or anonymization.
        </p>
      </div>

      {/* Retention Status Overview */}
      {status.length > 0 && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
          <h3 className="text-lg font-semibold text-blue-900 mb-3">
            Current Retention Status
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {status.map((item) => (
              <div key={item.data_type} className="bg-white rounded-lg p-4 border border-blue-100">
                <div className="font-medium text-gray-900 mb-1">
                  {dataTypeLabels[item.data_type] || item.data_type}
                </div>
                <div className="text-sm text-gray-600">
                  <div>Retention: {item.retention_days} days</div>
                  <div>Affected records: {item.affected_records}</div>
                  {item.anonymize_instead && (
                    <div className="text-amber-600 mt-1">
                      ⚠️ Will be anonymized instead of deleted
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Create Policy Button */}
      <div className="mb-6">
        <button
          onClick={() => setShowCreateForm(!showCreateForm)}
          className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors"
        >
          {showCreateForm ? 'Cancel' : '+ Create New Policy'}
        </button>
      </div>

      {/* Create Policy Form */}
      {showCreateForm && (
        <form onSubmit={handleCreatePolicy} className="bg-white border border-gray-200 rounded-lg p-6 mb-6">
          <h3 className="text-lg font-semibold mb-4">Create Retention Policy</h3>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Data Type
              </label>
              <select
                value={formData.data_type}
                onChange={(e) => setFormData({ ...formData, data_type: e.target.value })}
                className="w-full border border-gray-300 rounded-lg px-3 py-2"
                required
              >
                <option value="sales">Sales Data</option>
                <option value="recommendations">Recommendations</option>
                <option value="audit_logs">Audit Logs</option>
                <option value="products">Product Data</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Retention Days
              </label>
              <input
                type="number"
                value={formData.retention_days}
                onChange={(e) => setFormData({ ...formData, retention_days: parseInt(e.target.value) })}
                className="w-full border border-gray-300 rounded-lg px-3 py-2"
                min="1"
                required
              />
            </div>

            <div className="md:col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Description
              </label>
              <textarea
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                className="w-full border border-gray-300 rounded-lg px-3 py-2"
                rows={3}
                required
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Legal Basis
              </label>
              <select
                value={formData.legal_basis}
                onChange={(e) => setFormData({ ...formData, legal_basis: e.target.value })}
                className="w-full border border-gray-300 rounded-lg px-3 py-2"
                required
              >
                <option value="contract">Contract Performance</option>
                <option value="legal_obligation">Legal Obligation</option>
                <option value="legitimate_interest">Legitimate Interest</option>
                <option value="consent">User Consent</option>
              </select>
            </div>

            <div className="flex items-center space-x-6">
              <label className="flex items-center">
                <input
                  type="checkbox"
                  checked={formData.auto_delete_enabled}
                  onChange={(e) => setFormData({ ...formData, auto_delete_enabled: e.target.checked })}
                  className="mr-2"
                />
                <span className="text-sm text-gray-700">Auto-delete enabled</span>
              </label>

              <label className="flex items-center">
                <input
                  type="checkbox"
                  checked={formData.anonymize_instead}
                  onChange={(e) => setFormData({ ...formData, anonymize_instead: e.target.checked })}
                  className="mr-2"
                />
                <span className="text-sm text-gray-700">Anonymize instead of delete</span>
              </label>
            </div>
          </div>

          <div className="flex justify-end space-x-3">
            <button
              type="button"
              onClick={() => setShowCreateForm(false)}
              className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
            >
              Create Policy
            </button>
          </div>
        </form>
      )}

      {/* Policies List */}
      <div className="space-y-4">
        {policies.length === 0 ? (
          <div className="text-center py-8 text-gray-500">
            No retention policies configured yet.
          </div>
        ) : (
          policies.map((policy) => (
            <div key={policy.id} className="bg-white border border-gray-200 rounded-lg p-6">
              <div className="flex justify-between items-start mb-4">
                <div>
                  <h4 className="text-lg font-semibold text-gray-900">
                    {dataTypeLabels[policy.data_type] || policy.data_type}
                  </h4>
                  <p className="text-sm text-gray-600 mt-1">{policy.description}</p>
                </div>
                <div className="flex space-x-2">
                  <button
                    onClick={() => setEditingPolicy(policy.id === editingPolicy ? null : policy.id)}
                    className="text-blue-600 hover:text-blue-800 text-sm"
                  >
                    {editingPolicy === policy.id ? 'Cancel' : 'Edit'}
                  </button>
                  <button
                    onClick={() => handleDeletePolicy(policy.id)}
                    className="text-red-600 hover:text-red-800 text-sm"
                  >
                    Deactivate
                  </button>
                </div>
              </div>

              {editingPolicy === policy.id ? (
                <div className="grid grid-cols-2 gap-4 mt-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Retention Days
                    </label>
                    <input
                      type="number"
                      defaultValue={policy.retention_days}
                      onChange={(e) => {
                        const value = parseInt(e.target.value);
                        handleUpdatePolicy(policy.id, { retention_days: value });
                      }}
                      className="w-full border border-gray-300 rounded-lg px-3 py-2"
                    />
                  </div>
                </div>
              ) : (
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-4">
                  <div>
                    <div className="text-sm text-gray-600">Retention Period</div>
                    <div className="font-medium text-gray-900">{policy.retention_days} days</div>
                  </div>
                  <div>
                    <div className="text-sm text-gray-600">Legal Basis</div>
                    <div className="font-medium text-gray-900">
                      {legalBasisLabels[policy.legal_basis] || policy.legal_basis}
                    </div>
                  </div>
                  <div>
                    <div className="text-sm text-gray-600">Auto-Delete</div>
                    <div className="font-medium text-gray-900">
                      {policy.auto_delete_enabled ? (
                        <span className="text-green-600">Enabled</span>
                      ) : (
                        <span className="text-amber-600">Disabled</span>
                      )}
                    </div>
                  </div>
                  <div>
                    <div className="text-sm text-gray-600">Action</div>
                    <div className="font-medium text-gray-900">
                      {policy.anonymize_instead ? 'Anonymize' : 'Delete'}
                    </div>
                  </div>
                </div>
              )}

              {!policy.is_active && (
                <div className="mt-3 text-sm text-red-600 bg-red-50 px-3 py-2 rounded">
                  ⚠️ This policy is inactive
                </div>
              )}
            </div>
          ))
        )}
      </div>

      {/* Compliance Notice */}
      <div className="mt-8 bg-gray-50 border border-gray-200 rounded-lg p-4">
        <h4 className="font-semibold text-gray-900 mb-2">Compliance Information</h4>
        <ul className="text-sm text-gray-600 space-y-1">
          <li>• Retention policies must comply with GDPR Article 5 (storage limitation)</li>
          <li>• Data should not be kept longer than necessary for its purpose</li>
          <li>• Legal holds will prevent automated deletion</li>
          <li>• All deletions are logged for audit purposes</li>
        </ul>
      </div>
    </div>
  );
};

export default RetentionPolicySettings;
