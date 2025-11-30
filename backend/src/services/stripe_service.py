"""
Stripe integration service

Handles all Stripe API interactions for subscription billing.
"""

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional, Dict, Any, List

import stripe
from sqlalchemy.orm import Session

from src.config import settings
from src.models.subscription import Subscription, Invoice, PaymentMethod, UsageRecord
from src.logging_config import get_logger

logger = get_logger(__name__)

# Initialize Stripe
stripe.api_key = settings.stripe_secret_key if hasattr(settings, 'stripe_secret_key') else None


class StripeService:
    """
    Stripe API integration for subscription management

    Handles:
    - Customer creation
    - Subscription management
    - Payment method management
    - Invoice handling
    - Webhook processing
    """

    def __init__(self, db: Session):
        self.db = db

    async def create_customer(
        self,
        vendor_id: str,
        email: str,
        name: str,
        metadata: Optional[Dict[str, str]] = None,
    ) -> str:
        """
        Create a Stripe customer

        Args:
            vendor_id: Internal vendor ID
            email: Customer email
            name: Customer name
            metadata: Additional metadata

        Returns:
            Stripe customer ID
        """
        try:
            customer_metadata = metadata or {}
            customer_metadata['vendor_id'] = vendor_id

            customer = stripe.Customer.create(
                email=email,
                name=name,
                metadata=customer_metadata,
            )

            logger.info(f"Created Stripe customer {customer.id} for vendor {vendor_id}")
            return customer.id

        except stripe.error.StripeError as e:
            logger.error(f"Stripe error creating customer: {e}")
            raise

    async def create_subscription(
        self,
        vendor_id: str,
        stripe_customer_id: str,
        price_id: str,
        trial_days: Optional[int] = None,
    ) -> Subscription:
        """
        Create a subscription

        Args:
            vendor_id: Internal vendor ID
            stripe_customer_id: Stripe customer ID
            price_id: Stripe price ID
            trial_days: Trial period in days (default: None)

        Returns:
            Subscription object
        """
        try:
            # Create Stripe subscription
            stripe_sub_params = {
                'customer': stripe_customer_id,
                'items': [{'price': price_id}],
                'expand': ['latest_invoice.payment_intent'],
            }

            if trial_days:
                stripe_sub_params['trial_period_days'] = trial_days

            stripe_subscription = stripe.Subscription.create(**stripe_sub_params)

            # Determine tier from price_id (you'd map this in settings)
            tier = self._get_tier_from_price_id(price_id)
            tier_limits = Subscription.get_tier_limits(tier)

            # Create local subscription record
            subscription = Subscription(
                vendor_id=vendor_id,
                stripe_subscription_id=stripe_subscription.id,
                stripe_customer_id=stripe_customer_id,
                stripe_price_id=price_id,
                tier=tier,
                status=stripe_subscription.status,
                current_period_start=datetime.fromtimestamp(stripe_subscription.current_period_start),
                current_period_end=datetime.fromtimestamp(stripe_subscription.current_period_end),
                trial_start=datetime.fromtimestamp(stripe_subscription.trial_start) if stripe_subscription.trial_start else None,
                trial_end=datetime.fromtimestamp(stripe_subscription.trial_end) if stripe_subscription.trial_end else None,
                recommendations_limit=tier_limits['recommendations_limit'],
                products_limit=tier_limits['products_limit'],
                venues_limit=tier_limits['venues_limit'],
            )

            self.db.add(subscription)
            self.db.commit()
            self.db.refresh(subscription)

            logger.info(f"Created subscription {subscription.id} for vendor {vendor_id}")
            return subscription

        except stripe.error.StripeError as e:
            logger.error(f"Stripe error creating subscription: {e}")
            raise

    async def cancel_subscription(
        self,
        subscription_id: str,
        cancel_at_period_end: bool = True,
    ) -> Subscription:
        """
        Cancel a subscription

        Args:
            subscription_id: Internal subscription ID
            cancel_at_period_end: If True, cancels at end of billing period (default: True)

        Returns:
            Updated subscription
        """
        subscription = self.db.query(Subscription).filter(Subscription.id == subscription_id).first()
        if not subscription:
            raise ValueError(f"Subscription {subscription_id} not found")

        try:
            if cancel_at_period_end:
                # Cancel at period end (user keeps access until then)
                stripe_subscription = stripe.Subscription.modify(
                    subscription.stripe_subscription_id,
                    cancel_at_period_end=True,
                )
                subscription.cancel_at_period_end = True
            else:
                # Cancel immediately
                stripe_subscription = stripe.Subscription.delete(subscription.stripe_subscription_id)
                subscription.status = "canceled"
                subscription.canceled_at = datetime.utcnow()

            self.db.commit()
            self.db.refresh(subscription)

            logger.info(f"Canceled subscription {subscription_id}")
            return subscription

        except stripe.error.StripeError as e:
            logger.error(f"Stripe error canceling subscription: {e}")
            raise

    async def add_payment_method(
        self,
        vendor_id: str,
        stripe_customer_id: str,
        stripe_payment_method_id: str,
        set_as_default: bool = True,
    ) -> PaymentMethod:
        """
        Add a payment method to a customer

        Args:
            vendor_id: Internal vendor ID
            stripe_customer_id: Stripe customer ID
            stripe_payment_method_id: Stripe payment method ID
            set_as_default: Set as default payment method (default: True)

        Returns:
            PaymentMethod object
        """
        try:
            # Attach payment method to customer
            stripe.PaymentMethod.attach(
                stripe_payment_method_id,
                customer=stripe_customer_id,
            )

            # Get payment method details
            pm = stripe.PaymentMethod.retrieve(stripe_payment_method_id)

            # If setting as default, update others
            if set_as_default:
                self.db.query(PaymentMethod).filter(
                    PaymentMethod.vendor_id == vendor_id,
                    PaymentMethod.is_default == True,
                ).update({'is_default': False})

                # Set as default in Stripe
                stripe.Customer.modify(
                    stripe_customer_id,
                    invoice_settings={'default_payment_method': stripe_payment_method_id},
                )

            # Create local record
            payment_method = PaymentMethod(
                vendor_id=vendor_id,
                stripe_payment_method_id=stripe_payment_method_id,
                stripe_customer_id=stripe_customer_id,
                type=pm.type,
                is_default=set_as_default,
            )

            # Add card details if card
            if pm.type == 'card':
                payment_method.card_brand = pm.card.brand
                payment_method.card_last4 = pm.card.last4
                payment_method.card_exp_month = pm.card.exp_month
                payment_method.card_exp_year = pm.card.exp_year

            self.db.add(payment_method)
            self.db.commit()
            self.db.refresh(payment_method)

            logger.info(f"Added payment method for vendor {vendor_id}")
            return payment_method

        except stripe.error.StripeError as e:
            logger.error(f"Stripe error adding payment method: {e}")
            raise

    async def create_invoice(
        self,
        subscription_id: str,
        stripe_invoice: stripe.Invoice,
    ) -> Invoice:
        """
        Create local invoice record from Stripe invoice

        Args:
            subscription_id: Internal subscription ID
            stripe_invoice: Stripe invoice object

        Returns:
            Invoice object
        """
        subscription = self.db.query(Subscription).filter(Subscription.id == subscription_id).first()
        if not subscription:
            raise ValueError(f"Subscription {subscription_id} not found")

        invoice = Invoice(
            vendor_id=subscription.vendor_id,
            subscription_id=subscription_id,
            stripe_invoice_id=stripe_invoice.id,
            stripe_payment_intent_id=stripe_invoice.payment_intent if stripe_invoice.payment_intent else None,
            invoice_number=stripe_invoice.number,
            amount_due=Decimal(str(stripe_invoice.amount_due / 100)),  # Convert cents to dollars
            amount_paid=Decimal(str(stripe_invoice.amount_paid / 100)),
            currency=stripe_invoice.currency,
            status=stripe_invoice.status,
            paid=stripe_invoice.paid,
            invoice_date=datetime.fromtimestamp(stripe_invoice.created),
            due_date=datetime.fromtimestamp(stripe_invoice.due_date) if stripe_invoice.due_date else None,
            paid_at=datetime.fromtimestamp(stripe_invoice.status_transitions.paid_at) if stripe_invoice.status_transitions.paid_at else None,
            period_start=datetime.fromtimestamp(stripe_invoice.period_start),
            period_end=datetime.fromtimestamp(stripe_invoice.period_end),
            invoice_pdf_url=stripe_invoice.invoice_pdf,
            hosted_invoice_url=stripe_invoice.hosted_invoice_url,
        )

        self.db.add(invoice)
        self.db.commit()
        self.db.refresh(invoice)

        logger.info(f"Created invoice {invoice.id} for subscription {subscription_id}")
        return invoice

    async def record_usage(
        self,
        subscription_id: str,
        usage_type: str,
        quantity: int = 1,
    ) -> UsageRecord:
        """
        Record usage for billing period

        Args:
            subscription_id: Internal subscription ID
            usage_type: Type of usage ("recommendations", "products", "api_calls")
            quantity: Quantity to record (default: 1)

        Returns:
            UsageRecord object
        """
        subscription = self.db.query(Subscription).filter(Subscription.id == subscription_id).first()
        if not subscription:
            raise ValueError(f"Subscription {subscription_id} not found")

        usage_record = UsageRecord(
            vendor_id=subscription.vendor_id,
            subscription_id=subscription_id,
            usage_type=usage_type,
            quantity=quantity,
            timestamp=datetime.utcnow(),
            billing_period_start=subscription.current_period_start,
            billing_period_end=subscription.current_period_end,
        )

        self.db.add(usage_record)
        self.db.commit()
        self.db.refresh(usage_record)

        logger.debug(f"Recorded usage: {usage_type} x{quantity} for subscription {subscription_id}")
        return usage_record

    async def get_usage_summary(
        self,
        subscription_id: str,
        usage_type: Optional[str] = None,
    ) -> Dict[str, int]:
        """
        Get usage summary for current billing period

        Args:
            subscription_id: Internal subscription ID
            usage_type: Optional usage type filter

        Returns:
            Dictionary with usage counts by type
        """
        subscription = self.db.query(Subscription).filter(Subscription.id == subscription_id).first()
        if not subscription:
            raise ValueError(f"Subscription {subscription_id} not found")

        query = self.db.query(UsageRecord).filter(
            UsageRecord.subscription_id == subscription_id,
            UsageRecord.billing_period_start == subscription.current_period_start,
        )

        if usage_type:
            query = query.filter(UsageRecord.usage_type == usage_type)

        usage_records = query.all()

        # Summarize by type
        summary = {}
        for record in usage_records:
            if record.usage_type not in summary:
                summary[record.usage_type] = 0
            summary[record.usage_type] += record.quantity

        return summary

    def _get_tier_from_price_id(self, price_id: str) -> str:
        """
        Map Stripe price ID to subscription tier

        In production, this would be configured in settings or database.
        """
        # Example mapping (configure these in settings)
        price_tier_map = {
            'price_free': 'free',
            'price_pro_monthly': 'pro',
            'price_pro_yearly': 'pro',
            'price_enterprise_monthly': 'enterprise',
            'price_enterprise_yearly': 'enterprise',
        }

        return price_tier_map.get(price_id, 'free')
