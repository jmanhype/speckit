"""
Webhook handlers for external services

Handles:
- Stripe payment webhooks
- Square inventory webhooks (if applicable)
"""

from fastapi import APIRouter, Request, HTTPException, Depends, Header
from sqlalchemy.orm import Session
import stripe

from src.database import get_db
from src.config import settings
from src.services.stripe_service import StripeService
from src.models.subscription import Subscription, Invoice
from src.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/stripe")
async def stripe_webhook(
    request: Request,
    db: Session = Depends(get_db),
    stripe_signature: str = Header(None, alias="Stripe-Signature"),
):
    """
    Handle Stripe webhook events

    Processes:
    - invoice.payment_succeeded
    - invoice.payment_failed
    - customer.subscription.updated
    - customer.subscription.deleted
    - payment_method.attached
    - payment_method.detached

    Security:
    - Verifies webhook signature
    - Logs all events
    - Idempotent processing
    """
    payload = await request.body()

    # Verify webhook signature
    try:
        event = stripe.Webhook.construct_event(
            payload,
            stripe_signature,
            settings.stripe_webhook_secret if hasattr(settings, 'stripe_webhook_secret') else None,
        )
    except ValueError as e:
        logger.error(f"Invalid Stripe webhook payload: {e}")
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError as e:
        logger.error(f"Invalid Stripe webhook signature: {e}")
        raise HTTPException(status_code=400, detail="Invalid signature")

    # Log event
    logger.info(f"Received Stripe webhook: {event['type']}")

    # Process event
    stripe_service = StripeService(db)

    try:
        if event['type'] == 'invoice.payment_succeeded':
            await handle_invoice_payment_succeeded(event, stripe_service, db)

        elif event['type'] == 'invoice.payment_failed':
            await handle_invoice_payment_failed(event, stripe_service, db)

        elif event['type'] == 'customer.subscription.updated':
            await handle_subscription_updated(event, stripe_service, db)

        elif event['type'] == 'customer.subscription.deleted':
            await handle_subscription_deleted(event, stripe_service, db)

        elif event['type'] == 'payment_method.attached':
            logger.info(f"Payment method attached: {event['data']['object']['id']}")

        elif event['type'] == 'payment_method.detached':
            logger.info(f"Payment method detached: {event['data']['object']['id']}")

        else:
            logger.debug(f"Unhandled Stripe webhook type: {event['type']}")

    except Exception as e:
        logger.error(f"Error processing Stripe webhook {event['type']}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Webhook processing failed")

    return {"status": "success"}


async def handle_invoice_payment_succeeded(event, stripe_service: StripeService, db: Session):
    """Handle successful invoice payment"""
    invoice_data = event['data']['object']
    stripe_invoice_id = invoice_data['id']

    logger.info(f"Invoice payment succeeded: {stripe_invoice_id}")

    # Find or create invoice record
    invoice = db.query(Invoice).filter(Invoice.stripe_invoice_id == stripe_invoice_id).first()

    if invoice:
        # Update existing invoice
        invoice.status = 'paid'
        invoice.paid = True
        invoice.amount_paid = invoice.amount_due
        invoice.paid_at = datetime.utcnow()
        db.commit()
    else:
        # Create new invoice record
        # Find subscription by Stripe subscription ID
        stripe_subscription_id = invoice_data['subscription']
        subscription = db.query(Subscription).filter(
            Subscription.stripe_subscription_id == stripe_subscription_id
        ).first()

        if subscription:
            await stripe_service.create_invoice(
                subscription.id,
                stripe.Invoice.retrieve(stripe_invoice_id),
            )

    logger.info(f"Invoice {stripe_invoice_id} marked as paid")


async def handle_invoice_payment_failed(event, stripe_service: StripeService, db: Session):
    """Handle failed invoice payment"""
    invoice_data = event['data']['object']
    stripe_invoice_id = invoice_data['id']

    logger.warning(f"Invoice payment failed: {stripe_invoice_id}")

    # Update invoice status
    invoice = db.query(Invoice).filter(Invoice.stripe_invoice_id == stripe_invoice_id).first()
    if invoice:
        invoice.status = 'uncollectible'
        invoice.paid = False
        db.commit()

    # Update subscription status if needed
    stripe_subscription_id = invoice_data['subscription']
    subscription = db.query(Subscription).filter(
        Subscription.stripe_subscription_id == stripe_subscription_id
    ).first()

    if subscription:
        subscription.status = 'past_due'
        db.commit()

        logger.warning(f"Subscription {subscription.id} marked as past_due due to failed payment")


async def handle_subscription_updated(event, stripe_service: StripeService, db: Session):
    """Handle subscription update"""
    subscription_data = event['data']['object']
    stripe_subscription_id = subscription_data['id']

    logger.info(f"Subscription updated: {stripe_subscription_id}")

    # Find and update subscription
    subscription = db.query(Subscription).filter(
        Subscription.stripe_subscription_id == stripe_subscription_id
    ).first()

    if subscription:
        from datetime import datetime

        subscription.status = subscription_data['status']
        subscription.current_period_start = datetime.fromtimestamp(subscription_data['current_period_start'])
        subscription.current_period_end = datetime.fromtimestamp(subscription_data['current_period_end'])
        subscription.cancel_at_period_end = subscription_data['cancel_at_period_end']

        if subscription_data.get('canceled_at'):
            subscription.canceled_at = datetime.fromtimestamp(subscription_data['canceled_at'])

        db.commit()
        logger.info(f"Subscription {subscription.id} updated: status={subscription.status}")


async def handle_subscription_deleted(event, stripe_service: StripeService, db: Session):
    """Handle subscription cancellation"""
    subscription_data = event['data']['object']
    stripe_subscription_id = subscription_data['id']

    logger.info(f"Subscription deleted: {stripe_subscription_id}")

    # Find and update subscription
    subscription = db.query(Subscription).filter(
        Subscription.stripe_subscription_id == stripe_subscription_id
    ).first()

    if subscription:
        from datetime import datetime

        subscription.status = 'canceled'
        subscription.canceled_at = datetime.utcnow()
        db.commit()

        logger.info(f"Subscription {subscription.id} canceled")


# Additional webhook endpoints can be added here
# For example, Square webhooks for inventory sync
