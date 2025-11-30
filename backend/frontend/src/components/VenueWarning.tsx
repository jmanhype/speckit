/**
 * Venue warning component.
 * Displays warnings for new or stale venues with limited data.
 */

interface VenueWarningProps {
  confidenceLevel: 'low' | 'medium' | 'high';
  venueName?: string;
  className?: string;
}

export function VenueWarning({
  confidenceLevel,
  venueName,
  className = '',
}: VenueWarningProps) {
  // Only show warning for low or medium confidence
  if (confidenceLevel === 'high') {
    return null;
  }

  const isNewVenue = confidenceLevel === 'low';

  return (
    <div
      className={`bg-yellow-50 border border-yellow-200 rounded-md p-3 ${className}`}
    >
      <div className="flex items-start gap-2">
        <span className="text-yellow-600 text-lg" role="img" aria-label="warning">
          ⚠️
        </span>
        <div className="flex-1">
          <h4 className="text-sm font-semibold text-yellow-900">
            {isNewVenue ? 'New Venue' : 'Limited Historical Data'}
          </h4>
          <p className="text-xs text-yellow-800 mt-1">
            {isNewVenue ? (
              <>
                This is your first time at <strong>{venueName || 'this venue'}</strong>.
                Recommendations are based on general patterns and may not be accurate.
                After a few visits, our predictions will improve.
              </>
            ) : (
              <>
                Limited sales history at <strong>{venueName || 'this venue'}</strong>.
                Recommendations may be less accurate. Continue tracking sales to improve
                predictions.
              </>
            )}
          </p>
        </div>
      </div>
    </div>
  );
}
