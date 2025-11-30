/**
 * Account Deletion Component (GDPR Article 17 - Right to Erasure)
 *
 * Allows vendors to permanently delete their account with email confirmation
 * as required by GDPR Article 17.
 */

import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';

interface DeleteAccountProps {
  vendorId: string;
  vendorEmail: string;
}

export const DeleteAccount: React.FC<DeleteAccountProps> = ({ vendorId, vendorEmail }) => {
  const navigate = useNavigate();

  const [confirmEmail, setConfirmEmail] = useState('');
  const [reason, setReason] = useState('');
  const [isDeleting, setIsDeleting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showConfirmDialog, setShowConfirmDialog] = useState(false);

  const handleDelete = async () => {
    if (confirmEmail !== vendorEmail) {
      setError('Email confirmation does not match your account email');
      return;
    }

    setIsDeleting(true);
    setError(null);

    try {
      const token = localStorage.getItem('token');

      const response = await fetch('/api/v1/vendors/me', {
        method: 'DELETE',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({
          confirm_email: confirmEmail,
          reason: reason || undefined,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to delete account');
      }

      const result = await response.json();

      // Log out and redirect to goodbye page
      localStorage.removeItem('token');
      localStorage.removeItem('refreshToken');

      // Show success message before redirecting
      alert(`Account deletion completed. DSAR ID: ${result.dsar_id}. Your data has been ${result.anonymized ? 'anonymized' : 'deleted'}.`);

      // Redirect to home or goodbye page
      navigate('/goodbye', { replace: true });

    } catch (err) {
      console.error('Delete error:', err);
      setError(err instanceof Error ? err.message : 'An unknown error occurred');
      setIsDeleting(false);
    }
  };

  const handleInitiateDelete = () => {
    setShowConfirmDialog(true);
  };

  const handleCancelDelete = () => {
    setShowConfirmDialog(false);
    setConfirmEmail('');
    setReason('');
    setError(null);
  };

  return (
    <div className="bg-white rounded-lg shadow-md p-6 border-2 border-red-200">
      <h2 className="text-2xl font-bold text-red-700 mb-4">Delete Account</h2>

      <div className="mb-6">
        <div className="bg-red-50 border border-red-300 rounded-md p-4 mb-4">
          <h3 className="font-semibold text-red-900 mb-2">⚠️ Warning: This action cannot be undone</h3>
          <p className="text-red-800 mb-2">
            Deleting your account will permanently remove or anonymize all your data, including:
          </p>
          <ul className="list-disc list-inside text-red-800 space-y-1">
            <li>Your profile and account information</li>
            <li>All products and inventory data</li>
            <li>Sales history and transactions</li>
            <li>Recommendations and predictions</li>
            <li>Square POS connection (you'll need to re-authorize if you return)</li>
          </ul>
        </div>

        <div className="bg-yellow-50 border border-yellow-300 rounded-md p-4 mb-6">
          <h3 className="font-semibold text-yellow-900 mb-2">Before you go...</h3>
          <ul className="list-disc list-inside text-yellow-800 space-y-1">
            <li>Consider exporting your data first (use the "Export Your Data" option above)</li>
            <li>Check if you have any active subscriptions that need to be cancelled</li>
            <li>Some data may be retained for legal/compliance purposes (anonymized)</li>
            <li>Audit logs are preserved for security and compliance (personal identifiers removed)</li>
          </ul>
        </div>

        {!showConfirmDialog ? (
          <button
            onClick={handleInitiateDelete}
            className="w-full md:w-auto px-6 py-3 bg-red-600 text-white rounded-md font-semibold hover:bg-red-700 transition-colors duration-200"
          >
            I Want to Delete My Account
          </button>
        ) : (
          <div className="bg-gray-50 border border-gray-300 rounded-md p-6">
            <h3 className="font-bold text-gray-900 mb-4">Confirm Account Deletion</h3>

            <div className="space-y-4">
              <div>
                <label htmlFor="confirmEmail" className="block text-sm font-medium text-gray-700 mb-2">
                  Confirm your email address to continue:
                </label>
                <input
                  id="confirmEmail"
                  type="email"
                  value={confirmEmail}
                  onChange={(e) => setConfirmEmail(e.target.value)}
                  placeholder={vendorEmail}
                  className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-red-500 focus:border-transparent"
                  disabled={isDeleting}
                />
                <p className="text-sm text-gray-600 mt-1">
                  Type your email: <strong>{vendorEmail}</strong>
                </p>
              </div>

              <div>
                <label htmlFor="reason" className="block text-sm font-medium text-gray-700 mb-2">
                  Why are you leaving? (optional)
                </label>
                <textarea
                  id="reason"
                  value={reason}
                  onChange={(e) => setReason(e.target.value)}
                  placeholder="Help us improve by sharing your feedback..."
                  rows={3}
                  className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-red-500 focus:border-transparent"
                  disabled={isDeleting}
                />
              </div>

              {error && (
                <div className="bg-red-50 border border-red-200 rounded-md p-3">
                  <p className="text-red-800 text-sm">{error}</p>
                </div>
              )}

              <div className="flex flex-col sm:flex-row gap-3">
                <button
                  onClick={handleDelete}
                  disabled={isDeleting || confirmEmail !== vendorEmail}
                  className={`
                    flex-1 px-6 py-3 rounded-md font-semibold
                    transition-colors duration-200
                    ${isDeleting || confirmEmail !== vendorEmail
                      ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                      : 'bg-red-600 text-white hover:bg-red-700'
                    }
                  `}
                >
                  {isDeleting ? (
                    <span className="flex items-center justify-center">
                      <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-gray-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                      </svg>
                      Deleting Account...
                    </span>
                  ) : (
                    'Permanently Delete My Account'
                  )}
                </button>

                <button
                  onClick={handleCancelDelete}
                  disabled={isDeleting}
                  className="flex-1 px-6 py-3 bg-gray-200 text-gray-700 rounded-md font-semibold hover:bg-gray-300 transition-colors duration-200 disabled:opacity-50"
                >
                  Cancel
                </button>
              </div>
            </div>

            <div className="mt-4 text-sm text-gray-600">
              <p>
                <strong>GDPR Rights:</strong> This deletion is performed under GDPR Article 17 (Right to Erasure).
                A Data Subject Access Request (DSAR) will be created to track this deletion for compliance purposes.
              </p>
            </div>
          </div>
        )}
      </div>

      <div className="mt-6 text-sm text-gray-600 border-t pt-4">
        <p className="mb-2">
          <strong>Legal Holds:</strong> If your account is subject to a legal hold (e.g., pending investigation,
          active legal proceedings), deletion may be delayed or denied.
        </p>
        <p>
          <strong>Compliance:</strong> Some anonymized data may be retained to comply with legal obligations,
          such as financial records for tax purposes or audit logs for security investigations.
        </p>
      </div>
    </div>
  );
};
