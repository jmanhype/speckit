/**
 * AI Recommendations page with enhanced weather display.
 */

import { useState, useEffect } from 'react';
import { apiClient } from '../lib/api-client';
import { Button } from '../components/Button';
import { Card } from '../components/Card';
import { WeatherDisplay } from '../components/WeatherDisplay';
import { ConfidenceIndicator } from '../components/ConfidenceIndicator';
import { VenueWarning } from '../components/VenueWarning';
import { EventNotification } from '../components/EventNotification';
import { FeedbackForm } from '../components/FeedbackForm';
import { FeedbackStats } from '../components/FeedbackStats';
import { formatCurrency, formatDate } from '../lib/utils';

interface Product {
  id: string;
  name: string;
  price: number;
  category?: string;
}

interface WeatherData {
  condition?: string;
  temp_f?: number;
  feels_like_f?: number;
  humidity?: number;
  description?: string;
}

interface Recommendation {
  id: string;
  market_date: string;
  product: Product;
  recommended_quantity: number;
  confidence_score: number;
  predicted_revenue?: number;
  weather_condition?: string;
  weather_data?: WeatherData;
  is_special_event: boolean;
  generated_at: string;
  venue_id?: string;
  venue_name?: string;
  is_seasonal?: boolean;
  confidence_level: 'low' | 'medium' | 'high';
}

export function RecommendationsPage() {
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isGenerating, setIsGenerating] = useState(false);
  const [marketDate, setMarketDate] = useState('');
  const [message, setMessage] = useState('');
  const [showFeedbackForm, setShowFeedbackForm] = useState<string | null>(null);
  const [showStats, setShowStats] = useState(true);

  useEffect(() => {
    fetchRecommendations();

    // Set default market date to next Saturday
    const nextSaturday = getNextSaturday();
    setMarketDate(nextSaturday.toISOString().split('T')[0]);
  }, []);

  const getNextSaturday = () => {
    const today = new Date();
    const daysUntilSaturday = (6 - today.getDay() + 7) % 7 || 7;
    const nextSat = new Date(today);
    nextSat.setDate(today.getDate() + daysUntilSaturday);
    return nextSat;
  };

  const fetchRecommendations = async () => {
    try {
      const data = await apiClient.get<Recommendation[]>(
        '/api/v1/recommendations?days_ahead=14'
      );
      setRecommendations(data);
    } catch (error) {
      console.error('Failed to fetch recommendations:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleGenerate = async () => {
    if (!marketDate) {
      setMessage('Please select a market date');
      return;
    }

    setIsGenerating(true);
    setMessage('');

    try {
      // Use default location (could be enhanced with geolocation)
      await apiClient.post('/api/v1/recommendations/generate', {
        market_date: marketDate,
        latitude: 37.7749, // San Francisco (example)
        longitude: -122.4194,
      });

      setMessage('Recommendations generated successfully!');
      await fetchRecommendations();
    } catch (error: any) {
      setMessage(`Generation failed: ${error.message}`);
    } finally {
      setIsGenerating(false);
    }
  };

  const groupByDate = (recs: Recommendation[]) => {
    const grouped: { [key: string]: Recommendation[] } = {};

    recs.forEach((rec) => {
      if (!grouped[rec.market_date]) {
        grouped[rec.market_date] = [];
      }
      grouped[rec.market_date].push(rec);
    });

    return grouped;
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-64">
        <div className="spinner h-8 w-8"></div>
      </div>
    );
  }

  const groupedRecs = groupByDate(recommendations);

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-3xl font-bold text-gray-900">
          AI Recommendations
        </h1>
      </div>

      {/* Generate Card */}
      <Card className="mb-6" padding>
        <h2 className="text-xl font-semibold mb-4">
          Generate Recommendations
        </h2>

        <p className="text-gray-600 mb-4">
          Get AI-powered inventory suggestions based on sales history,
          weather, and market events.
        </p>

        {message && (
          <div
            className={`p-3 rounded-md mb-4 ${
              message.includes('failed')
                ? 'bg-red-50 text-red-800'
                : 'bg-green-50 text-green-800'
            }`}
          >
            {message}
          </div>
        )}

        <div className="flex gap-4 items-end">
          <div className="flex-1">
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Market Date
            </label>
            <input
              type="date"
              value={marketDate}
              onChange={(e) => setMarketDate(e.target.value)}
              className="input"
            />
          </div>

          <Button onClick={handleGenerate} isLoading={isGenerating}>
            Generate Recommendations
          </Button>
        </div>
      </Card>

      {/* Feedback Stats */}
      {showStats && <FeedbackStats daysBack={30} className="mb-6" />}

      {/* Recommendations List */}
      {Object.keys(groupedRecs).length === 0 ? (
        <Card padding>
          <p className="text-gray-600 text-center py-8">
            No recommendations yet. Generate your first recommendations above!
          </p>
        </Card>
      ) : (
        <div className="space-y-6">
          {Object.keys(groupedRecs)
            .sort()
            .map((date) => {
              // Get weather data from first recommendation
              const firstRec = groupedRecs[date][0];
              const weatherData = firstRec?.weather_data || {
                condition: firstRec?.weather_condition,
              };

              return (
                <div key={date}>
                  <div className="flex items-center justify-between mb-3">
                    <h3 className="text-lg font-semibold">
                      {formatDate(new Date(date))}
                      {firstRec?.is_special_event && (
                        <span className="badge badge-warning ml-2">
                          Special Event
                        </span>
                      )}
                    </h3>
                  </div>

                  {/* Weather forecast for this date */}
                  {weatherData.condition && (
                    <WeatherDisplay
                      condition={weatherData.condition}
                      tempF={weatherData.temp_f}
                      feelsLikeF={weatherData.feels_like_f}
                      humidity={weatherData.humidity}
                      description={weatherData.description}
                      className="mb-4"
                    />
                  )}

                  {/* Venue warning for low/medium confidence */}
                  {firstRec?.confidence_level !== 'high' && (
                    <VenueWarning
                      confidenceLevel={firstRec.confidence_level}
                      venueName={firstRec.venue_name}
                      className="mb-4"
                    />
                  )}

                  {/* Event notification if special event detected */}
                  {firstRec?.is_special_event && weatherData && (
                    <EventNotification
                      eventName={weatherData.description || 'Special Event'}
                      expectedAttendance={200}
                      isSpecial={true}
                      className="mb-4"
                    />
                  )}

                  <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                    {groupedRecs[date].map((rec) => (
                      <Card key={rec.id} padding>
                      {showFeedbackForm === rec.id ? (
                        <FeedbackForm
                          recommendationId={rec.id}
                          recommendedQuantity={rec.recommended_quantity}
                          productName={rec.product.name}
                          onSuccess={() => {
                            setShowFeedbackForm(null);
                            setMessage('Feedback submitted successfully!');
                          }}
                          onCancel={() => setShowFeedbackForm(null)}
                        />
                      ) : (
                        <>
                          <div className="flex justify-between items-start mb-2">
                            <div className="flex-1">
                              <h4 className="font-semibold text-gray-900">
                                {rec.product.name}
                                {rec.is_seasonal && (
                                  <span className="ml-2 text-xs bg-purple-100 text-purple-800 px-2 py-0.5 rounded">
                                    Seasonal
                                  </span>
                                )}
                              </h4>
                            </div>
                            <ConfidenceIndicator
                              level={rec.confidence_level}
                              score={rec.confidence_score}
                            />
                          </div>

                      {rec.product.category && (
                        <p className="text-sm text-gray-600 mb-3">
                          {rec.product.category}
                        </p>
                      )}

                      {rec.venue_name && (
                        <p className="text-xs text-gray-500 mb-3">
                          📍 {rec.venue_name}
                        </p>
                      )}

                      <div className="space-y-2">
                        <div className="flex justify-between">
                          <span className="text-sm text-gray-600">
                            Recommended Quantity
                          </span>
                          <span className="font-semibold">
                            {rec.recommended_quantity}
                          </span>
                        </div>

                        {rec.predicted_revenue && (
                          <div className="flex justify-between">
                            <span className="text-sm text-gray-600">
                              Predicted Revenue
                            </span>
                            <span className="font-semibold text-green-600">
                              {formatCurrency(rec.predicted_revenue)}
                            </span>
                          </div>
                        )}

                        {rec.weather_condition && (
                          <div className="flex justify-between">
                            <span className="text-sm text-gray-600">
                              Weather
                            </span>
                            <span className="text-sm capitalize">
                              {rec.weather_condition}
                            </span>
                          </div>
                        )}
                      </div>

                      {/* Feedback button */}
                      <div className="mt-4 pt-4 border-t border-gray-200">
                        <button
                          onClick={() => setShowFeedbackForm(rec.id)}
                          className="text-sm text-blue-600 hover:text-blue-800 font-medium"
                        >
                          📝 Provide Feedback
                        </button>
                      </div>
                    </>
                  )}
                    </Card>
                  ))}
                  </div>
                </div>
              );
            })}
        </div>
      )}
    </div>
  );
}
