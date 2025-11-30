/**
 * Settings page (placeholder).
 */

import { Link } from 'react-router-dom';
import { Card } from '../components/Card';

export function SettingsPage() {
  return (
    <div>
      <h1 className="text-3xl font-bold text-gray-900 mb-6">Settings</h1>

      <div className="grid gap-4 md:grid-cols-2">
        <Link to="/settings/square">
          <Card hover padding>
            <h3 className="text-lg font-semibold mb-2">
              Square Integration
            </h3>
            <p className="text-gray-600">
              Connect and manage your Square account integration
            </p>
          </Card>
        </Link>

        <Card padding className="opacity-50">
          <h3 className="text-lg font-semibold mb-2">Account Settings</h3>
          <p className="text-gray-600">Coming soon</p>
        </Card>
      </div>
    </div>
  );
}
