/**
 * Event notification component.
 * Displays alerts for nearby events that may impact sales.
 */

interface EventNotificationProps {
  eventName: string;
  eventDate?: string;
  expectedAttendance: number;
  isSpecial: boolean;
  location?: string;
  className?: string;
}

export function EventNotification({
  eventName,
  eventDate,
  expectedAttendance,
  isSpecial,
  location,
  className = '',
}: EventNotificationProps) {
  // Choose color based on event significance
  const colorClass = isSpecial
    ? 'bg-purple-50 border-purple-300 text-purple-900'
    : 'bg-blue-50 border-blue-300 text-blue-900';

  const icon = isSpecial ? '⭐' : '📅';

  return (
    <div className={`border rounded-lg p-4 ${colorClass} ${className}`}>
      <div className="flex items-start gap-3">
        <span className="text-2xl" role="img" aria-label="event">
          {icon}
        </span>
        <div className="flex-1">
          <div className="flex items-start justify-between">
            <div>
              <h4 className="font-semibold text-sm">
                {isSpecial ? 'Special Event Detected' : 'Local Event'}
              </h4>
              <p className="text-lg font-bold mt-1">{eventName}</p>
            </div>
            {isSpecial && (
              <span className="badge bg-purple-200 text-purple-900 text-xs px-2 py-1">
                High Impact
              </span>
            )}
          </div>

          <div className="mt-2 space-y-1 text-sm">
            {location && (
              <div className="flex items-center gap-2">
                <span>📍</span>
                <span>{location}</span>
              </div>
            )}

            <div className="flex items-center gap-2">
              <span>👥</span>
              <span>{expectedAttendance.toLocaleString()} expected attendees</span>
            </div>

            <p className="mt-2 text-xs opacity-75">
              {isSpecial
                ? 'This large event may significantly increase foot traffic. Consider bringing extra inventory.'
                : 'This nearby event may attract additional customers.'}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
