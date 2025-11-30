"""ML-powered recommendation service.

Generates inventory recommendations using:
- Historical sales patterns
- Weather forecasts
- Market events
- Seasonal trends
- Venue-specific patterns

Uses scikit-learn for predictive modeling.

Features graceful degradation:
- Falls back to historical averages if ML model fails
- Falls back to simple heuristics if no historical data
- Continues operation when model training fails
- Logs warnings but doesn't crash
"""
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Dict, Any, Optional
from uuid import UUID
from collections import defaultdict

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
from sqlalchemy.orm import Session
from sqlalchemy import func

from src.models.product import Product
from src.models.sale import Sale
from src.models.recommendation import Recommendation
from src.models.venue import Venue


logger = logging.getLogger(__name__)


class MLModelError(Exception):
    """Exception raised when ML model is unavailable."""
    pass


class VenueFeatureEngineer:
    """Engineer venue-specific features for ML model."""

    # Minimum sales required for venue confidence
    MIN_VENUE_SALES = 3
    HIGH_CONFIDENCE_SALES = 20

    # Stale venue threshold (months)
    STALE_VENUE_MONTHS = 6

    def __init__(self, vendor_id: UUID, db: Session):
        """Initialize venue feature engineer.

        Args:
            vendor_id: Vendor UUID
            db: Database session
        """
        self.vendor_id = vendor_id
        self.db = db

    def extract_venue_features(
        self,
        venue_id: UUID,
        product_id: UUID,
        market_date: datetime,
    ) -> Dict[str, float]:
        """Extract venue-specific performance features.

        Args:
            venue_id: Venue UUID
            product_id: Product UUID
            market_date: Target market date

        Returns:
            Dictionary of venue features
        """
        features = {}

        # Get sales history for this venue and product
        venue_sales = self._get_venue_product_sales(venue_id, product_id, market_date)

        if len(venue_sales) == 0:
            # New venue/product combination - use defaults
            features['venue_avg_sales'] = 0.0
            features['venue_max_sales'] = 0.0
            features['venue_sales_count'] = 0.0
            features['venue_last_sale_days_ago'] = 999.0  # Very old
        else:
            quantities = [s['quantity'] for s in venue_sales]
            features['venue_avg_sales'] = float(np.mean(quantities))
            features['venue_max_sales'] = float(np.max(quantities))
            features['venue_sales_count'] = float(len(venue_sales))

            # Days since last sale at this venue
            last_sale_date = max(s['date'] for s in venue_sales)
            days_ago = (market_date - last_sale_date).days
            features['venue_last_sale_days_ago'] = float(days_ago)

        return features

    def is_seasonal_product(
        self,
        product_id: UUID,
        month: int,
    ) -> bool:
        """Detect if product is seasonal.

        Args:
            product_id: Product UUID
            month: Month number (1-12)

        Returns:
            True if product is seasonal for this month
        """
        # Get sales by month for this product
        monthly_sales = self._get_monthly_sales_pattern(product_id)

        if len(monthly_sales) < 3:
            # Not enough data to determine seasonality
            return False

        # Calculate mean and std deviation
        sales_values = list(monthly_sales.values())
        mean_sales = np.mean(sales_values)
        std_sales = np.std(sales_values)

        # If this month's sales are > 1.5 std above mean, it's seasonal
        current_month_sales = monthly_sales.get(month, 0)

        if std_sales == 0:
            return False

        z_score = (current_month_sales - mean_sales) / std_sales
        return z_score > 1.5 or z_score < -1.5

    def calculate_venue_confidence(
        self,
        venue_id: UUID,
        product_id: UUID,
        market_date: datetime,
    ) -> float:
        """Calculate confidence score for venue prediction.

        Args:
            venue_id: Venue UUID
            product_id: Product UUID
            market_date: Target market date

        Returns:
            Confidence score (0.0 to 1.0)
        """
        # Get sales history
        venue_sales = self._get_venue_product_sales(venue_id, product_id, market_date)

        if len(venue_sales) == 0:
            # New venue - very low confidence
            return 0.3

        # Check if stale (last sale > 6 months ago)
        last_sale_date = max(s['date'] for s in venue_sales)
        months_since_sale = (market_date - last_sale_date).days / 30.0

        if months_since_sale > self.STALE_VENUE_MONTHS:
            # Stale venue - medium confidence
            return 0.5

        # Calculate confidence based on number of sales
        num_sales = len(venue_sales)

        if num_sales >= self.HIGH_CONFIDENCE_SALES:
            # High confidence
            return 0.85
        elif num_sales >= self.MIN_VENUE_SALES:
            # Medium-high confidence (linear interpolation)
            progress = (num_sales - self.MIN_VENUE_SALES) / (self.HIGH_CONFIDENCE_SALES - self.MIN_VENUE_SALES)
            return 0.6 + (0.25 * progress)
        else:
            # Low confidence
            return 0.4

    def generate_venue_embedding(self, venue_id: UUID) -> List[float]:
        """Generate numerical embedding for venue.

        Args:
            venue_id: Venue UUID

        Returns:
            List of embedding values
        """
        # Get venue details
        venue = self.db.query(Venue).filter(Venue.id == venue_id).first()

        if not venue:
            return [0.0] * 5

        # Create simple embedding based on venue characteristics
        embedding = []

        # Typical attendance (normalized)
        attendance = float(venue.typical_attendance or 100)
        embedding.append(min(attendance / 1000.0, 1.0))  # Normalize to 0-1

        # Location coordinates (if available)
        if venue.latitude and venue.longitude:
            embedding.append(float(venue.latitude) / 90.0)  # Normalize to 0-1
            embedding.append(float(venue.longitude) / 180.0)  # Normalize to 0-1
        else:
            embedding.append(0.5)
            embedding.append(0.5)

        # Total historical performance
        total_sales = self._get_venue_total_sales(venue_id)
        embedding.append(min(total_sales / 1000.0, 1.0))  # Normalize

        # Venue age (days since first sale)
        first_sale = self._get_venue_first_sale_date(venue_id)
        if first_sale:
            days_old = (datetime.utcnow() - first_sale).days
            embedding.append(min(days_old / 365.0, 1.0))  # Normalize to years
        else:
            embedding.append(0.0)

        return embedding

    def _get_venue_product_sales(
        self,
        venue_id: UUID,
        product_id: UUID,
        before_date: datetime,
        days_back: int = 180,
    ) -> List[Dict[str, Any]]:
        """Get sales history for a venue and product.

        Args:
            venue_id: Venue UUID
            product_id: Product UUID
            before_date: Look back before this date
            days_back: Number of days to look back

        Returns:
            List of sales with quantity info
        """
        start_date = before_date - timedelta(days=days_back)

        # Query sales at this venue
        sales = (
            self.db.query(Sale)
            .filter(
                Sale.vendor_id == self.vendor_id,
                Sale.square_location_id == str(venue_id),  # Link via Square location
                Sale.sale_date >= start_date,
                Sale.sale_date < before_date,
            )
            .order_by(Sale.sale_date.desc())
            .all()
        )

        # Extract quantities for this product
        product_sales = []

        for sale in sales:
            if not sale.line_items:
                continue

            for item in sale.line_items:
                # Match by product_id if available
                item_product_id = item.get('product_id')
                if item_product_id and str(item_product_id) == str(product_id):
                    quantity = int(item.get('quantity', '1'))
                    product_sales.append({
                        'date': sale.sale_date,
                        'quantity': quantity,
                    })

        return product_sales

    def _get_monthly_sales_pattern(
        self,
        product_id: UUID,
    ) -> Dict[int, float]:
        """Get average sales by month for a product.

        Args:
            product_id: Product UUID

        Returns:
            Dictionary mapping month (1-12) to average sales
        """
        # Get all sales for this product
        cutoff_date = datetime.utcnow() - timedelta(days=365)

        sales = (
            self.db.query(Sale)
            .filter(
                Sale.vendor_id == self.vendor_id,
                Sale.sale_date >= cutoff_date,
            )
            .all()
        )

        # Group by month
        monthly_totals = defaultdict(list)

        for sale in sales:
            if not sale.line_items:
                continue

            month = sale.sale_date.month

            for item in sale.line_items:
                item_product_id = item.get('product_id')
                if item_product_id and str(item_product_id) == str(product_id):
                    quantity = int(item.get('quantity', '1'))
                    monthly_totals[month].append(quantity)

        # Calculate averages
        monthly_averages = {}
        for month, quantities in monthly_totals.items():
            monthly_averages[month] = float(np.mean(quantities))

        return monthly_averages

    def _get_venue_total_sales(self, venue_id: UUID) -> float:
        """Get total sales count for a venue.

        Args:
            venue_id: Venue UUID

        Returns:
            Total sales count
        """
        count = (
            self.db.query(func.count(Sale.id))
            .filter(
                Sale.vendor_id == self.vendor_id,
                Sale.square_location_id == str(venue_id),
            )
            .scalar()
        )

        return float(count or 0)

    def _get_venue_first_sale_date(self, venue_id: UUID) -> Optional[datetime]:
        """Get date of first sale at venue.

        Args:
            venue_id: Venue UUID

        Returns:
            First sale date or None
        """
        first_sale = (
            self.db.query(Sale.sale_date)
            .filter(
                Sale.vendor_id == self.vendor_id,
                Sale.square_location_id == str(venue_id),
            )
            .order_by(Sale.sale_date.asc())
            .first()
        )

        return first_sale[0] if first_sale else None


class MLRecommendationService:
    """Service for generating ML-powered inventory recommendations."""

    # Model version for tracking
    MODEL_VERSION = "v1.0.0"

    # Minimum historical data required (in days)
    MIN_HISTORY_DAYS = 14

    def __init__(self, vendor_id: UUID, db: Session):
        """Initialize ML service.

        Args:
            vendor_id: Vendor UUID
            db: Database session
        """
        self.vendor_id = vendor_id
        self.db = db
        self.scaler = StandardScaler()
        self.model = RandomForestRegressor(
            n_estimators=100,
            max_depth=10,
            min_samples_split=5,
            random_state=42,
        )
        # Track whether model is trained
        self.model_trained = False
        self.scaler_fitted = False

        # Initialize venue feature engineer
        self.venue_engineer = VenueFeatureEngineer(vendor_id=vendor_id, db=db)

    def _extract_features(
        self,
        product_id: UUID,
        market_date: datetime,
        weather_data: Optional[Dict[str, Any]] = None,
        event_data: Optional[Dict[str, Any]] = None,
        venue_id: Optional[UUID] = None,
    ) -> pd.DataFrame:
        """Extract features for prediction.

        Args:
            product_id: Product UUID
            market_date: Target market date
            weather_data: Weather forecast data
            event_data: Event information
            venue_id: Venue UUID (optional)

        Returns:
            DataFrame with feature columns
        """
        features = {}

        # Temporal features
        features['day_of_week'] = market_date.weekday()  # 0=Monday, 6=Sunday
        features['month'] = market_date.month
        features['day_of_month'] = market_date.day
        features['week_of_year'] = market_date.isocalendar()[1]

        # Weather features (if available)
        if weather_data:
            features['temp_f'] = weather_data.get('temp_f', 70.0)
            features['feels_like_f'] = weather_data.get('feels_like_f', 70.0)
            features['humidity'] = weather_data.get('humidity', 50.0)
            features['is_sunny'] = 1 if weather_data.get('condition') == 'sunny' else 0
            features['is_rainy'] = 1 if weather_data.get('condition') == 'rainy' else 0
        else:
            # Default weather features
            features['temp_f'] = 70.0
            features['feels_like_f'] = 70.0
            features['humidity'] = 50.0
            features['is_sunny'] = 0
            features['is_rainy'] = 0

        # Event features
        if event_data:
            features['is_special_event'] = 1
            features['expected_attendance'] = event_data.get('expected_attendance', 100)
        else:
            features['is_special_event'] = 0
            features['expected_attendance'] = 100

        # Historical features (rolling averages from past sales)
        recent_sales = self._get_recent_sales_for_product(product_id, market_date)

        if len(recent_sales) > 0:
            features['avg_sales_last_7d'] = np.mean([s['quantity'] for s in recent_sales[:7]])
            features['avg_sales_last_14d'] = np.mean([s['quantity'] for s in recent_sales[:14]])
            features['max_sales_last_30d'] = max([s['quantity'] for s in recent_sales[:30]], default=0)
        else:
            features['avg_sales_last_7d'] = 0
            features['avg_sales_last_14d'] = 0
            features['max_sales_last_30d'] = 0

        # Venue-specific features (if venue provided)
        if venue_id:
            venue_features = self.venue_engineer.extract_venue_features(
                venue_id=venue_id,
                product_id=product_id,
                market_date=market_date,
            )
            features.update(venue_features)

            # Add venue embedding
            venue_embedding = self.venue_engineer.generate_venue_embedding(venue_id)
            for i, val in enumerate(venue_embedding):
                features[f'venue_emb_{i}'] = val
        else:
            # No venue - use default values
            features['venue_avg_sales'] = 0.0
            features['venue_max_sales'] = 0.0
            features['venue_sales_count'] = 0.0
            features['venue_last_sale_days_ago'] = 0.0
            for i in range(5):
                features[f'venue_emb_{i}'] = 0.0

        # Seasonal features
        is_seasonal = self.venue_engineer.is_seasonal_product(
            product_id=product_id,
            month=market_date.month,
        )
        features['is_seasonal'] = 1 if is_seasonal else 0

        # Get monthly average for this product
        monthly_pattern = self.venue_engineer._get_monthly_sales_pattern(product_id)
        month_avg = monthly_pattern.get(market_date.month, 0)
        features['month_avg_sales'] = month_avg

        # Calculate seasonal strength (how much this month deviates from average)
        if len(monthly_pattern) > 0:
            overall_avg = np.mean(list(monthly_pattern.values()))
            seasonal_strength = (month_avg - overall_avg) / (overall_avg + 1)  # Avoid division by zero
            features['seasonal_strength'] = seasonal_strength
        else:
            features['seasonal_strength'] = 0.0

        return pd.DataFrame([features])

    def _get_recent_sales_for_product(
        self,
        product_id: UUID,
        before_date: datetime,
        days_back: int = 90,
    ) -> List[Dict[str, Any]]:
        """Get recent sales data for a product.

        Args:
            product_id: Product UUID
            before_date: Look back before this date
            days_back: Number of days to look back

        Returns:
            List of sales with quantity info
        """
        start_date = before_date - timedelta(days=days_back)

        # Query sales with line items containing this product
        sales = (
            self.db.query(Sale)
            .filter(
                Sale.vendor_id == self.vendor_id,
                Sale.sale_date >= start_date,
                Sale.sale_date < before_date,
            )
            .order_by(Sale.sale_date.desc())
            .all()
        )

        # Extract quantities for this product from line items
        product_sales = []

        for sale in sales:
            if not sale.line_items:
                continue

            # Simple matching by product name (can be enhanced with product_id in line_items)
            for item in sale.line_items:
                # For now, estimate quantity from line items
                # In production, line_items should include product_id
                quantity = int(item.get('quantity', '1'))
                product_sales.append({
                    'date': sale.sale_date,
                    'quantity': quantity,
                })

        return product_sales

    def _train_model(self, product_id: UUID) -> bool:
        """Train ML model on historical data for a product.

        Args:
            product_id: Product UUID

        Returns:
            True if training successful, False otherwise
        """
        logger.info(f"Training model for product {product_id}")

        # Get historical sales data
        cutoff_date = datetime.utcnow() - timedelta(days=self.MIN_HISTORY_DAYS)

        sales = (
            self.db.query(Sale)
            .filter(
                Sale.vendor_id == self.vendor_id,
                Sale.sale_date >= cutoff_date,
            )
            .all()
        )

        if len(sales) < self.MIN_HISTORY_DAYS:
            logger.warning(f"Insufficient training data: {len(sales)} sales")
            return False

        # Prepare training data
        X_list = []
        y_list = []

        for sale in sales:
            # Extract features for this sale date
            features_df = self._extract_features(
                product_id=product_id,
                market_date=sale.sale_date,
                weather_data={
                    'temp_f': float(sale.weather_temp_f) if sale.weather_temp_f else 70.0,
                    'condition': sale.weather_condition or 'clear',
                },
            )

            # Target: total quantity sold (simplified)
            total_quantity = 0
            if sale.line_items:
                for item in sale.line_items:
                    total_quantity += int(item.get('quantity', '1'))

            X_list.append(features_df.values[0])
            y_list.append(total_quantity)

        if len(X_list) == 0:
            logger.warning("No training samples extracted")
            return False

        X = np.array(X_list)
        y = np.array(y_list)

        # Scale features
        try:
            X_scaled = self.scaler.fit_transform(X)
            self.scaler_fitted = True
        except Exception as e:
            logger.error(f"Failed to fit scaler: {e}")
            return False

        # Train model
        try:
            self.model.fit(X_scaled, y)
            self.model_trained = True
            logger.info(f"Model trained successfully on {len(X)} samples")
            return True
        except Exception as e:
            logger.error(f"Failed to train model: {e}")
            return False

    def _generate_fallback_recommendation(
        self,
        product_id: UUID,
        market_date: datetime,
        weather_data: Optional[Dict[str, Any]] = None,
        event_data: Optional[Dict[str, Any]] = None,
        venue_id: Optional[UUID] = None,
    ) -> int:
        """Generate fallback recommendation using simple heuristics.

        Used when ML model is unavailable or fails.

        Args:
            product_id: Product UUID
            market_date: Target market date
            weather_data: Weather forecast
            event_data: Event information
            venue_id: Venue UUID

        Returns:
            Recommended quantity
        """
        logger.warning(
            f"Using fallback heuristics for product {product_id} - "
            f"ML model unavailable"
        )

        # Get recent sales data
        recent_sales = self._get_recent_sales_for_product(
            product_id=product_id,
            before_date=market_date,
            days_back=30,
        )

        if len(recent_sales) == 0:
            # No sales history - use conservative default
            base_quantity = 5
        else:
            # Use average of recent sales
            quantities = [s['quantity'] for s in recent_sales]
            base_quantity = int(np.mean(quantities))

        # Apply event multiplier if applicable
        if event_data:
            attendance = event_data.get('expected_attendance', 100)
            if attendance >= 1000:
                base_quantity = int(base_quantity * 1.5)
            elif attendance >= 500:
                base_quantity = int(base_quantity * 1.3)

        # Apply weather adjustment (simple rules)
        if weather_data:
            condition = weather_data.get('condition', '')
            if condition == 'sunny':
                base_quantity = int(base_quantity * 1.1)
            elif condition in ['rainy', 'snow']:
                base_quantity = int(base_quantity * 0.8)

        # Ensure minimum of 1
        return max(1, base_quantity)

    def generate_recommendation(
        self,
        product_id: UUID,
        market_date: datetime,
        weather_data: Optional[Dict[str, Any]] = None,
        event_data: Optional[Dict[str, Any]] = None,
        venue_id: Optional[UUID] = None,
    ) -> Recommendation:
        """Generate recommendation for a product and market date with graceful degradation.

        Falls back to simple heuristics if ML model is unavailable.

        Args:
            product_id: Product UUID
            market_date: Target market date
            weather_data: Weather forecast
            event_data: Event information
            venue_id: Venue UUID (optional)

        Returns:
            Recommendation object
        """
        logger.info(f"Generating recommendation for product {product_id} on {market_date} at venue {venue_id}")

        # Track if using fallback
        using_fallback = False

        # Try ML prediction
        try:
            # Train model if not already trained
            if not self.model_trained:
                training_success = self._train_model(product_id)
                if not training_success:
                    logger.warning("Model training failed, using fallback heuristics")
                    using_fallback = True

            if not using_fallback:
                # Extract features (including venue and seasonal features)
                features_df = self._extract_features(
                    product_id=product_id,
                    market_date=market_date,
                    weather_data=weather_data,
                    event_data=event_data,
                    venue_id=venue_id,
                )

                # Scale features
                if not self.scaler_fitted:
                    logger.warning("Scaler not fitted, using fallback heuristics")
                    using_fallback = True
                else:
                    try:
                        X_scaled = self.scaler.transform(features_df.values)
                    except Exception as e:
                        logger.warning(f"Feature scaling failed: {e}, using fallback heuristics")
                        using_fallback = True

                # Make prediction
                if not using_fallback:
                    try:
                        predicted_quantity = self.model.predict(X_scaled)[0]
                        # Round to nearest integer and ensure minimum of 1
                        recommended_quantity = max(1, int(round(predicted_quantity)))
                    except Exception as e:
                        logger.error(f"Model prediction failed: {e}, using fallback heuristics")
                        using_fallback = True

        except Exception as e:
            logger.error(
                f"Unexpected error in ML prediction: {e} - using fallback heuristics",
                exc_info=True
            )
            using_fallback = True

        # Use fallback if ML failed
        if using_fallback:
            recommended_quantity = self._generate_fallback_recommendation(
                product_id=product_id,
                market_date=market_date,
                weather_data=weather_data,
                event_data=event_data,
                venue_id=venue_id,
            )

        # Calculate confidence score based on venue data availability and whether using fallback
        if using_fallback:
            # Lower confidence when using fallback heuristics
            confidence_score = Decimal("0.5")
        elif venue_id:
            confidence_score = Decimal(str(self.venue_engineer.calculate_venue_confidence(
                venue_id=venue_id,
                product_id=product_id,
                market_date=market_date,
            )))
        else:
            # No venue specified - use moderate confidence
            confidence_score = Decimal("0.65")

        # Get product for revenue calculation
        product = self.db.query(Product).filter(Product.id == product_id).first()

        predicted_revenue = None
        if product:
            predicted_revenue = Decimal(recommended_quantity) * product.price

        # Build historical features dict
        if using_fallback:
            # Get simple features for fallback
            recent_sales = self._get_recent_sales_for_product(
                product_id=product_id,
                before_date=market_date,
                days_back=30,
            )
            historical_features = {
                'avg_sales_last_30d': float(np.mean([s['quantity'] for s in recent_sales])) if recent_sales else 0.0,
                'using_fallback': True,
            }
        else:
            # ML features available
            historical_features = {
                'avg_sales_last_7d': float(features_df['avg_sales_last_7d'].values[0]),
                'avg_sales_last_14d': float(features_df['avg_sales_last_14d'].values[0]),
                'using_fallback': False,
            }

            # Add venue features if present
            if venue_id:
                historical_features.update({
                    'venue_avg_sales': float(features_df['venue_avg_sales'].values[0]),
                    'venue_sales_count': float(features_df['venue_sales_count'].values[0]),
                    'venue_last_sale_days_ago': float(features_df['venue_last_sale_days_ago'].values[0]),
                })

            # Add seasonal features
            historical_features.update({
                'is_seasonal': int(features_df['is_seasonal'].values[0]),
                'seasonal_strength': float(features_df['seasonal_strength'].values[0]),
                'month_avg_sales': float(features_df['month_avg_sales'].values[0]),
            })

        # Create recommendation
        recommendation = Recommendation(
            vendor_id=self.vendor_id,
            market_date=market_date,
            product_id=product_id,
            venue_id=venue_id,  # Store venue ID
            recommended_quantity=recommended_quantity,
            confidence_score=confidence_score,
            predicted_sales=recommended_quantity,  # Assume all sell
            predicted_revenue=predicted_revenue,
            weather_features=weather_data,
            event_features=event_data,
            historical_features=historical_features,
            model_version=self.MODEL_VERSION,
        )

        return recommendation

    def generate_recommendations_for_date(
        self,
        market_date: datetime,
        weather_data: Optional[Dict[str, Any]] = None,
        event_data: Optional[Dict[str, Any]] = None,
        venue_id: Optional[UUID] = None,
        limit: int = 10,
    ) -> List[Recommendation]:
        """Generate recommendations for all active products for a market date.

        Args:
            market_date: Target market date
            weather_data: Weather forecast
            event_data: Event information
            venue_id: Venue UUID (optional)
            limit: Maximum number of products to recommend

        Returns:
            List of recommendations
        """
        # Get active products
        products = (
            self.db.query(Product)
            .filter(
                Product.vendor_id == self.vendor_id,
                Product.is_active == True,
            )
            .limit(limit)
            .all()
        )

        recommendations = []

        for product in products:
            try:
                rec = self.generate_recommendation(
                    product_id=product.id,
                    market_date=market_date,
                    weather_data=weather_data,
                    event_data=event_data,
                    venue_id=venue_id,
                )
                recommendations.append(rec)
            except Exception as e:
                logger.error(f"Failed to generate recommendation for {product.id}: {e}")
                continue

        return recommendations

    def get_feedback_for_training(
        self,
        days_back: int = 90,
        min_rating: int = 3,
    ) -> List[Dict[str, Any]]:
        """Retrieve feedback data for model retraining.

        Fetches historical recommendations with vendor feedback to improve
        future predictions. This method can be used in a batch retraining job.

        Args:
            days_back: Number of days of feedback to retrieve
            min_rating: Minimum rating to include (1-5)

        Returns:
            List of training examples with features and actual outcomes

        Usage:
            ```python
            # In a periodic retraining job:
            ml_service = MLRecommendationService(vendor_id=vendor_id, db=db)
            training_data = ml_service.get_feedback_for_training(days_back=90)

            # Extract features and targets
            X = [example['features'] for example in training_data]
            y = [example['actual_quantity_sold'] for example in training_data]

            # Retrain model
            ml_service.scaler.fit(X)
            ml_service.model.fit(X_scaled, y)
            ```
        """
        from src.models.recommendation_feedback import RecommendationFeedback

        cutoff_date = datetime.utcnow() - timedelta(days=days_back)

        # Query recommendations with feedback
        feedback_records = (
            self.db.query(Recommendation, RecommendationFeedback)
            .join(
                RecommendationFeedback,
                Recommendation.id == RecommendationFeedback.recommendation_id,
            )
            .filter(
                Recommendation.vendor_id == self.vendor_id,
                Recommendation.market_date >= cutoff_date,
                RecommendationFeedback.actual_quantity_sold.isnot(None),
                RecommendationFeedback.rating >= min_rating,  # Only use rated feedback
            )
            .all()
        )

        training_examples = []

        for rec, feedback in feedback_records:
            # Extract original features used for prediction
            features = {}

            # Add all stored features
            if rec.weather_features:
                features.update(rec.weather_features)
            if rec.event_features:
                features.update(rec.event_features)
            if rec.historical_features:
                features.update(rec.historical_features)

            # Add temporal features
            features['day_of_week'] = rec.market_date.weekday()
            features['month'] = rec.market_date.month

            training_examples.append({
                'recommendation_id': str(rec.id),
                'product_id': str(rec.product_id),
                'market_date': rec.market_date,
                'features': features,
                'recommended_quantity': rec.recommended_quantity,
                'actual_quantity_sold': feedback.actual_quantity_sold,
                'actual_revenue': float(feedback.actual_revenue) if feedback.actual_revenue else None,
                'variance_percentage': float(feedback.variance_percentage) if feedback.variance_percentage else None,
                'was_accurate': feedback.was_accurate,
                'rating': feedback.rating,
            })

        logger.info(f"Retrieved {len(training_examples)} feedback examples for retraining")

        return training_examples
