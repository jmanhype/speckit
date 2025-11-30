/**
 * Confidence indicator component for recommendations.
 * Shows visual indicator of prediction confidence (high/medium/low).
 */

interface ConfidenceIndicatorProps {
  level: 'low' | 'medium' | 'high';
  score: number;
  className?: string;
}

const levelConfig = {
  low: {
    color: 'bg-yellow-100 border-yellow-300 text-yellow-900',
    icon: '⚠️',
    label: 'Low Confidence',
    description: 'Limited historical data available',
  },
  medium: {
    color: 'bg-blue-100 border-blue-300 text-blue-900',
    icon: '📊',
    label: 'Medium Confidence',
    description: 'Some historical data available',
  },
  high: {
    color: 'bg-green-100 border-green-300 text-green-900',
    icon: '✓',
    label: 'High Confidence',
    description: 'Strong historical data',
  },
};

export function ConfidenceIndicator({
  level,
  score,
  className = '',
}: ConfidenceIndicatorProps) {
  const config = levelConfig[level];

  return (
    <div
      className={`inline-flex items-center gap-2 px-3 py-1 rounded-md border ${config.color} ${className}`}
      title={config.description}
    >
      <span className="text-sm" role="img" aria-label={config.label}>
        {config.icon}
      </span>
      <div className="flex flex-col">
        <span className="text-xs font-semibold">{config.label}</span>
        <span className="text-xs opacity-75">{(score * 100).toFixed(0)}%</span>
      </div>
    </div>
  );
}
