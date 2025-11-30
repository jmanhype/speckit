"""
ML model training and retraining service

Handles:
- Initial model training from historical sales data
- Periodic retraining with new data
- Feedback-driven model improvement
- Model versioning and rollback
"""

import pickle
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sqlalchemy.orm import Session
from sqlalchemy import func

from src.models.sale import Sale
from src.models.recommendation import Recommendation
from src.models.recommendation_feedback import RecommendationFeedback
from src.models.product import Product
from src.logging_config import get_logger

logger = get_logger(__name__)


class ModelTrainer:
    """
    Service for training and retraining ML recommendation models

    Features:
    - Train from historical sales data
    - Retrain with feedback data
    - Model versioning
    - Performance tracking
    - Automatic model selection (keeps best performing model)
    """

    def __init__(
        self,
        db: Session,
        model_dir: Optional[Path] = None,
    ):
        """
        Initialize model trainer

        Args:
            db: Database session
            model_dir: Directory to save models (default: backend/models/)
        """
        self.db = db
        self.model_dir = model_dir or Path(__file__).parent.parent.parent / "models"
        self.model_dir.mkdir(parents=True, exist_ok=True)

    def train_model_for_vendor(
        self,
        vendor_id: str,
        min_sales_records: int = 30,
        test_size: float = 0.2,
    ) -> Optional[Dict[str, Any]]:
        """
        Train new model for vendor from historical data

        Args:
            vendor_id: Vendor UUID
            min_sales_records: Minimum sales records required
            test_size: Fraction of data for testing

        Returns:
            Training results or None if insufficient data
        """
        logger.info(f"Starting model training for vendor {vendor_id}")

        # Fetch sales data
        sales = (
            self.db.query(Sale)
            .filter(Sale.vendor_id == vendor_id)
            .order_by(Sale.sale_date.asc())
            .all()
        )

        if len(sales) < min_sales_records:
            logger.warning(
                f"Insufficient sales data for vendor {vendor_id}: "
                f"{len(sales)} records (need {min_sales_records})"
            )
            return None

        # Prepare features and labels
        X, y, feature_names = self._prepare_training_data(sales)

        if len(X) == 0:
            logger.warning(f"No valid training data for vendor {vendor_id}")
            return None

        # Split train/test
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=42
        )

        # Train model
        model = RandomForestRegressor(
            n_estimators=100,
            max_depth=10,
            min_samples_split=5,
            min_samples_leaf=2,
            random_state=42,
            n_jobs=-1,
        )

        model.fit(X_train, y_train)

        # Evaluate
        y_pred = model.predict(X_test)
        metrics = self._calculate_metrics(y_test, y_pred)

        # Save model
        model_path = self._save_model(
            vendor_id=vendor_id,
            model=model,
            feature_names=feature_names,
            metrics=metrics,
        )

        logger.info(
            f"Model trained for vendor {vendor_id}: MAE={metrics['mae']:.2f}, "
            f"R2={metrics['r2']:.3f}, saved to {model_path}"
        )

        return {
            "vendor_id": vendor_id,
            "model_path": str(model_path),
            "metrics": metrics,
            "training_samples": len(X_train),
            "test_samples": len(X_test),
            "feature_names": feature_names,
            "trained_at": datetime.utcnow().isoformat(),
        }

    def retrain_with_feedback(
        self,
        vendor_id: str,
        min_feedback_records: int = 10,
    ) -> Optional[Dict[str, Any]]:
        """
        Retrain model using feedback data

        Incorporates actual outcomes from vendor feedback to improve predictions.

        Args:
            vendor_id: Vendor UUID
            min_feedback_records: Minimum feedback records required

        Returns:
            Retraining results or None if insufficient feedback
        """
        logger.info(f"Starting feedback-driven retraining for vendor {vendor_id}")

        # Fetch feedback with actual sales data
        feedback_records = (
            self.db.query(RecommendationFeedback)
            .join(Recommendation)
            .filter(
                Recommendation.vendor_id == vendor_id,
                RecommendationFeedback.actual_quantity_sold.isnot(None),
            )
            .all()
        )

        if len(feedback_records) < min_feedback_records:
            logger.warning(
                f"Insufficient feedback for vendor {vendor_id}: "
                f"{len(feedback_records)} records (need {min_feedback_records})"
            )
            return None

        # Prepare training data from feedback
        X, y, feature_names = self._prepare_feedback_training_data(feedback_records)

        if len(X) == 0:
            logger.warning(f"No valid feedback training data for vendor {vendor_id}")
            return None

        # Split train/test
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )

        # Train new model
        model = RandomForestRegressor(
            n_estimators=150,  # More trees for feedback learning
            max_depth=12,
            min_samples_split=3,
            min_samples_leaf=1,
            random_state=42,
            n_jobs=-1,
        )

        model.fit(X_train, y_train)

        # Evaluate
        y_pred = model.predict(X_test)
        metrics = self._calculate_metrics(y_test, y_pred)

        # Compare with existing model
        existing_model_path = self._get_latest_model_path(vendor_id)
        should_replace = True

        if existing_model_path and existing_model_path.exists():
            old_model_metrics = self._load_model_metadata(vendor_id).get("metrics", {})
            old_mae = old_model_metrics.get("mae", float("inf"))

            # Only replace if new model is better
            if metrics["mae"] > old_mae * 1.1:  # Allow 10% tolerance
                logger.info(
                    f"New model not better than existing (MAE {metrics['mae']:.2f} vs {old_mae:.2f}) - keeping old model"
                )
                should_replace = False

        if should_replace:
            # Save new model
            model_path = self._save_model(
                vendor_id=vendor_id,
                model=model,
                feature_names=feature_names,
                metrics=metrics,
                version_tag="feedback",
            )

            logger.info(
                f"Model retrained with feedback for vendor {vendor_id}: "
                f"MAE={metrics['mae']:.2f}, R2={metrics['r2']:.3f}"
            )
        else:
            model_path = existing_model_path

        return {
            "vendor_id": vendor_id,
            "model_path": str(model_path),
            "metrics": metrics,
            "feedback_records_used": len(X_train) + len(X_test),
            "model_replaced": should_replace,
            "retrained_at": datetime.utcnow().isoformat(),
        }

    def _prepare_training_data(
        self, sales: list[Sale]
    ) -> Tuple[np.ndarray, np.ndarray, list[str]]:
        """
        Prepare features and labels from sales data

        Args:
            sales: List of Sale records

        Returns:
            Tuple of (features, labels, feature_names)
        """
        features = []
        labels = []

        for sale in sales:
            if not sale.quantity or sale.quantity <= 0:
                continue

            # Extract features (simplified - in production would use full feature engineering)
            feature_vector = [
                sale.sale_date.weekday(),  # Day of week
                sale.sale_date.month,  # Month
                sale.sale_date.day,  # Day of month
                float(sale.total_amount or 0),  # Sale amount
            ]

            features.append(feature_vector)
            labels.append(sale.quantity)

        feature_names = ["weekday", "month", "day", "total_amount"]

        return np.array(features), np.array(labels), feature_names

    def _prepare_feedback_training_data(
        self, feedback_records: list[RecommendationFeedback]
    ) -> Tuple[np.ndarray, np.ndarray, list[str]]:
        """
        Prepare features and labels from feedback data

        Args:
            feedback_records: List of feedback records

        Returns:
            Tuple of (features, labels, feature_names)
        """
        features = []
        labels = []

        for feedback in feedback_records:
            if not feedback.actual_quantity_sold or feedback.actual_quantity_sold <= 0:
                continue

            recommendation = feedback.recommendation

            # Extract features from recommendation context
            market_date = recommendation.market_date
            feature_vector = [
                market_date.weekday(),
                market_date.month,
                market_date.day,
                float(recommendation.recommended_quantity or 0),
                float(feedback.rating or 3),  # User rating as signal
            ]

            features.append(feature_vector)
            labels.append(feedback.actual_quantity_sold)

        feature_names = ["weekday", "month", "day", "recommended_qty", "rating"]

        return np.array(features), np.array(labels), feature_names

    def _calculate_metrics(
        self, y_true: np.ndarray, y_pred: np.ndarray
    ) -> Dict[str, float]:
        """Calculate model performance metrics"""
        return {
            "mae": float(mean_absolute_error(y_true, y_pred)),
            "rmse": float(np.sqrt(mean_squared_error(y_true, y_pred))),
            "r2": float(r2_score(y_true, y_pred)),
            "mape": float(np.mean(np.abs((y_true - y_pred) / y_true)) * 100),
        }

    def _save_model(
        self,
        vendor_id: str,
        model: RandomForestRegressor,
        feature_names: list[str],
        metrics: Dict[str, float],
        version_tag: str = "base",
    ) -> Path:
        """
        Save model to disk with metadata

        Args:
            vendor_id: Vendor UUID
            model: Trained model
            feature_names: Feature names
            metrics: Performance metrics
            version_tag: Version tag

        Returns:
            Path to saved model
        """
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        model_filename = f"{vendor_id}_{version_tag}_{timestamp}.pkl"
        model_path = self.model_dir / model_filename

        # Save model
        with open(model_path, "wb") as f:
            pickle.dump(model, f)

        # Save metadata
        metadata = {
            "vendor_id": vendor_id,
            "version_tag": version_tag,
            "feature_names": feature_names,
            "metrics": metrics,
            "trained_at": datetime.utcnow().isoformat(),
        }

        metadata_path = model_path.with_suffix(".json")
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)

        return model_path

    def _get_latest_model_path(self, vendor_id: str) -> Optional[Path]:
        """Get path to latest model for vendor"""
        models = list(self.model_dir.glob(f"{vendor_id}_*.pkl"))
        if not models:
            return None
        return max(models, key=lambda p: p.stat().st_mtime)

    def _load_model_metadata(self, vendor_id: str) -> Dict[str, Any]:
        """Load metadata for latest model"""
        model_path = self._get_latest_model_path(vendor_id)
        if not model_path:
            return {}

        metadata_path = model_path.with_suffix(".json")
        if not metadata_path.exists():
            return {}

        with open(metadata_path) as f:
            return json.load(f)


# Background task for periodic retraining
def retrain_all_vendors_with_feedback(db: Session) -> Dict[str, Any]:
    """
    Retrain models for all vendors with sufficient feedback

    Run this as a scheduled task (e.g., weekly)

    Args:
        db: Database session

    Returns:
        Summary of retraining results
    """
    logger.info("Starting periodic model retraining with feedback")

    trainer = ModelTrainer(db)

    # Get all vendors with feedback
    vendors_with_feedback = (
        db.query(RecommendationFeedback.vendor_id)
        .distinct()
        .all()
    )

    results = {
        "total_vendors": len(vendors_with_feedback),
        "retrained": 0,
        "skipped": 0,
        "failed": 0,
        "details": [],
    }

    for (vendor_id,) in vendors_with_feedback:
        try:
            result = trainer.retrain_with_feedback(vendor_id)

            if result:
                results["retrained"] += 1
                results["details"].append({
                    "vendor_id": vendor_id,
                    "status": "retrained",
                    "mae": result["metrics"]["mae"],
                })
            else:
                results["skipped"] += 1
                results["details"].append({
                    "vendor_id": vendor_id,
                    "status": "skipped_insufficient_feedback",
                })

        except Exception as e:
            logger.error(f"Failed to retrain model for vendor {vendor_id}: {e}", exc_info=True)
            results["failed"] += 1
            results["details"].append({
                "vendor_id": vendor_id,
                "status": "failed",
                "error": str(e),
            })

    logger.info(
        f"Periodic retraining complete: {results['retrained']} retrained, "
        f"{results['skipped']} skipped, {results['failed']} failed"
    )

    return results
