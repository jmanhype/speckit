"""
Contract tests for Stripe integration

Tests Stripe API adapter behavior without hitting live API.
Uses mocks to verify contract compliance.
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime

from src.services.stripe_service import StripeService


class TestStripeCustomerContract:
    """Test Stripe customer creation contract"""

    @patch('stripe.Customer.create')
    def test_create_customer_contract(self, mock_create, db):
        """Test customer creation follows Stripe API contract"""
        # Mock Stripe response
        mock_create.return_value = Mock(id="cus_test123")

        service = StripeService(db)
        customer_id = service.create_customer(
            vendor_id="vendor-123",
            email="test@example.com",
            name="Test Vendor"
        )

        # Verify contract
        mock_create.assert_called_once_with(
            email="test@example.com",
            name="Test Vendor",
            metadata={'vendor_id': "vendor-123"}
        )
        assert customer_id == "cus_test123"


class TestStripeSubscriptionContract:
    """Test Stripe subscription contract"""

    @patch('stripe.Subscription.create')
    def test_create_subscription_contract(self, mock_create, db):
        """Test subscription creation follows contract"""
        mock_create.return_value = Mock(
            id="sub_test123",
            status="active",
            current_period_start=datetime.utcnow().timestamp(),
            current_period_end=datetime.utcnow().timestamp()
        )

        service = StripeService(db)
        subscription = service.create_subscription(
            vendor_id="vendor-123",
            stripe_customer_id="cus_test123",
            price_id="price_pro_monthly"
        )

        # Verify contract compliance
        mock_create.assert_called_once()
        args = mock_create.call_args[1]
        assert args['customer'] == "cus_test123"
        assert len(args['items']) == 1
        assert args['items'][0]['price'] == "price_pro_monthly"


# Additional contract tests for:
# - Payment method attachment
# - Invoice creation
# - Usage recording
# - Subscription cancellation
# - Webhook signature verification
