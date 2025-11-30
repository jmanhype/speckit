/**
 * Weather display component for recommendations.
 * Shows weather forecast with icons and details.
 */

interface WeatherDisplayProps {
  condition?: string;
  tempF?: number;
  feelsLikeF?: number;
  humidity?: number;
  description?: string;
  className?: string;
}

const weatherIcons: { [key: string]: string } = {
  clear: '☀️',
  sunny: '☀️',
  clouds: '☁️',
  rain: '🌧️',
  rainy: '🌧️',
  snow: '❄️',
  thunderstorm: '⛈️',
  mist: '🌫️',
  fog: '🌫️',
};

const weatherColors: { [key: string]: string } = {
  clear: 'bg-yellow-50 border-yellow-200 text-yellow-900',
  sunny: 'bg-yellow-50 border-yellow-200 text-yellow-900',
  clouds: 'bg-gray-50 border-gray-200 text-gray-900',
  rain: 'bg-blue-50 border-blue-200 text-blue-900',
  rainy: 'bg-blue-50 border-blue-200 text-blue-900',
  snow: 'bg-cyan-50 border-cyan-200 text-cyan-900',
  thunderstorm: 'bg-purple-50 border-purple-200 text-purple-900',
  mist: 'bg-gray-50 border-gray-300 text-gray-700',
  fog: 'bg-gray-50 border-gray-300 text-gray-700',
};

export function WeatherDisplay({
  condition,
  tempF,
  feelsLikeF,
  humidity,
  description,
  className = '',
}: WeatherDisplayProps) {
  if (!condition) {
    return null;
  }

  const icon = weatherIcons[condition] || '🌤️';
  const colorClass = weatherColors[condition] || 'bg-gray-50 border-gray-200 text-gray-900';

  return (
    <div className={`border rounded-lg p-3 ${colorClass} ${className}`}>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-2xl" role="img" aria-label={condition}>
            {icon}
          </span>
          <div>
            <div className="font-semibold capitalize">{condition}</div>
            {description && (
              <div className="text-xs opacity-75 capitalize">{description}</div>
            )}
          </div>
        </div>

        {tempF !== undefined && (
          <div className="text-right">
            <div className="text-2xl font-bold">{Math.round(tempF)}°F</div>
            {feelsLikeF !== undefined && tempF !== feelsLikeF && (
              <div className="text-xs opacity-75">
                Feels like {Math.round(feelsLikeF)}°F
              </div>
            )}
          </div>
        )}
      </div>

      {humidity !== undefined && (
        <div className="mt-2 pt-2 border-t border-current border-opacity-20">
          <div className="flex items-center justify-between text-sm">
            <span className="opacity-75">Humidity</span>
            <span className="font-medium">{Math.round(humidity)}%</span>
          </div>
        </div>
      )}
    </div>
  );
}
