/**
 * GDPR Data Export Component (Article 15 - Right to Access)
 *
 * Allows vendors to export all their personal data in machine-readable JSON format
 * as required by GDPR Article 15.
 */

import React, { useState } from 'react';

interface DataExportProps {
  vendorId: string;
}

export const DataExport: React.FC<DataExportProps> = ({ vendorId }) => {
  const [isExporting, setIsExporting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastExportDate, setLastExportDate] = useState<string | null>(null);

  const handleExport = async () => {
    setIsExporting(true);
    setError(null);

    try {
      const token = localStorage.getItem('token');

      const response = await fetch('/api/v1/vendors/me/data-export', {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to export data');
      }

      // Get filename from Content-Disposition header
      const contentDisposition = response.headers.get('Content-Disposition');
      let filename = 'marketprep_data_export.json';

      if (contentDisposition) {
        const filenameMatch = contentDisposition.match(/filename="?(.+)"?/);
        if (filenameMatch) {
          filename = filenameMatch[1];
        }
      }

      // Download the file
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);

      setLastExportDate(new Date().toISOString());

    } catch (err) {
      console.error('Export error:', err);
      setError(err instanceof Error ? err.message : 'An unknown error occurred');
    } finally {
      setIsExporting(false);
    }
  };

  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <h2 className="text-2xl font-bold mb-4">Export Your Data</h2>

      <div className="mb-6">
        <p className="text-gray-700 mb-4">
          Under GDPR Article 15, you have the right to access all personal data we hold about you.
          Click the button below to download a complete copy of your data in JSON format.
        </p>

        <div className="bg-blue-50 border border-blue-200 rounded-md p-4 mb-4">
          <h3 className="font-semibold text-blue-900 mb-2">Your export will include:</h3>
          <ul className="list-disc list-inside text-blue-800 space-y-1">
            <li>Profile information (name, email, business details)</li>
            <li>All products and inventory data</li>
            <li>Sales transactions and history</li>
            <li>Recommendations and predictions</li>
            <li>Square POS connection metadata (tokens excluded)</li>
            <li>Consent records and data processing history</li>
            <li>Audit logs of account activities</li>
          </ul>
        </div>

        {lastExportDate && (
          <div className="bg-green-50 border border-green-200 rounded-md p-3 mb-4">
            <p className="text-green-800 text-sm">
              Last export: {new Date(lastExportDate).toLocaleString()}
            </p>
          </div>
        )}

        {error && (
          <div className="bg-red-50 border border-red-200 rounded-md p-3 mb-4">
            <p className="text-red-800 text-sm">{error}</p>
          </div>
        )}
      </div>

      <button
        onClick={handleExport}
        disabled={isExporting}
        className={`
          w-full md:w-auto px-6 py-3 rounded-md font-semibold
          transition-colors duration-200
          ${isExporting
            ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
            : 'bg-blue-600 text-white hover:bg-blue-700'
          }
        `}
      >
        {isExporting ? (
          <span className="flex items-center justify-center">
            <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-gray-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            Generating Export...
          </span>
        ) : (
          'Download My Data'
        )}
      </button>

      <div className="mt-4 text-sm text-gray-600">
        <p className="mb-2">
          <strong>Privacy Note:</strong> Your data export is generated on-demand and is not stored on our servers.
        </p>
        <p>
          <strong>Format:</strong> The export is in JSON format, which can be opened with any text editor or imported into other applications.
        </p>
      </div>
    </div>
  );
};
