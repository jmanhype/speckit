#!/usr/bin/env python
"""Generate test data for local development.

Creates sample products, sales, and recommendations for testing.

Usage:
    python scripts/generate_test_data.py
"""
import sys
from pathlib import Path
from datetime import datetime, timedelta
from decimal import Decimal
import random

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database import SessionLocal
from src.models.vendor import Vendor
from src.models.product import Product
from src.models.sale import Sale
from src.models.recommendation import Recommendation


def generate_test_data():
    """Generate comprehensive test data."""
    db = SessionLocal()

    try:
        # Get test vendor
        vendor = db.query(Vendor).filter(Vendor.email == "test@example.com").first()

        if not vendor:
            print("❌ Test user not found. Run create_test_user.py first.")
            sys.exit(1)

        print(f"📦 Generating test data for {vendor.business_name}...")
        print("")

        # Sample product data
        products_data = [
            {"name": "Organic Tomatoes", "price": 4.99, "category": "Vegetables"},
            {"name": "Fresh Strawberries", "price": 6.99, "category": "Fruit"},
            {"name": "Honey (16oz)", "price": 12.99, "category": "Pantry"},
            {"name": "Sourdough Bread", "price": 7.99, "category": "Bakery"},
            {"name": "Free-Range Eggs (dozen)", "price": 8.99, "category": "Dairy"},
            {"name": "Organic Lettuce", "price": 3.99, "category": "Vegetables"},
            {"name": "Blueberries", "price": 5.99, "category": "Fruit"},
            {"name": "Artisan Cheese", "price": 14.99, "category": "Dairy"},
            {"name": "Fresh Basil", "price": 2.99, "category": "Herbs"},
            {"name": "Zucchini", "price": 3.49, "category": "Vegetables"},
            {"name": "Peaches", "price": 5.49, "category": "Fruit"},
            {"name": "Maple Syrup (8oz)", "price": 15.99, "category": "Pantry"},
        ]

        # Create products
        products = []
        for data in products_data:
            existing = db.query(Product).filter(
                Product.vendor_id == vendor.id,
                Product.name == data["name"]
            ).first()

            if not existing:
                product = Product(
                    vendor_id=vendor.id,
                    name=data["name"],
                    price=Decimal(str(data["price"])),
                    category=data["category"],
                    is_active=True,
                    is_seasonal=data["category"] == "Fruit",
                )
                db.add(product)
                products.append(product)
            else:
                products.append(existing)

        db.commit()
        print(f"✅ Created {len(products)} products")

        # Generate sales history (last 30 days)
        sales_created = 0
        start_date = datetime.now() - timedelta(days=30)

        for day in range(30):
            sale_date = start_date + timedelta(days=day)

            # Skip some days randomly (not every day has a market)
            if random.random() < 0.3:
                continue

            # Create 3-8 sales per market day
            num_sales = random.randint(3, 8)

            for _ in range(num_sales):
                # Random 1-4 products per sale
                num_items = random.randint(1, 4)
                selected_products = random.sample(products, num_items)

                line_items = []
                total = Decimal("0.00")

                for product in selected_products:
                    quantity = random.randint(1, 3)
                    subtotal = product.price * quantity
                    total += subtotal

                    line_items.append({
                        "product_id": str(product.id),
                        "product_name": product.name,
                        "quantity": quantity,
                        "unit_price": float(product.price),
                        "subtotal": float(subtotal),
                    })

                sale = Sale(
                    vendor_id=vendor.id,
                    sale_date=sale_date,
                    total_amount=total,
                    line_items=line_items,
                    weather_temp_f=Decimal(str(random.randint(60, 85))),
                    was_sunny=random.choice([True, False]),
                )
                db.add(sale)
                sales_created += 1

        db.commit()
        print(f"✅ Created {sales_created} sales over 30 days")

        # Generate recommendations for next Saturday
        next_saturday = datetime.now()
        days_ahead = (5 - next_saturday.weekday()) % 7  # 5 = Saturday
        if days_ahead == 0:
            days_ahead = 7
        next_saturday += timedelta(days=days_ahead)

        recommendations_created = 0
        for product in products[:8]:  # Top 8 products
            confidence = random.uniform(0.65, 0.95)
            quantity = random.randint(5, 25)
            revenue = float(product.price) * quantity

            rec = Recommendation(
                vendor_id=vendor.id,
                market_date=next_saturday,
                product_id=product.id,
                recommended_quantity=quantity,
                confidence_score=Decimal(str(confidence)),
                predicted_revenue=Decimal(str(revenue)),
                weather_features={
                    "temp_f": 75.0,
                    "condition": "sunny",
                    "humidity": 60,
                },
                event_features={
                    "is_special": False,
                    "event_name": None,
                },
                model_version="v1.0.0",
            )
            db.add(rec)
            recommendations_created += 1

        db.commit()
        print(f"✅ Created {recommendations_created} recommendations for {next_saturday.strftime('%Y-%m-%d')}")

        # Summary
        print("")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print("✅ Test data generated successfully!")
        print("")
        print(f"  📦 Products: {len(products)}")
        print(f"  💰 Sales: {sales_created}")
        print(f"  🤖 Recommendations: {recommendations_created}")
        print("")
        print("Login at http://localhost:3000 to see the data:")
        print("  Email: test@example.com")
        print("  Password: test123")

    except Exception as e:
        print(f"❌ Error generating test data: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    generate_test_data()
