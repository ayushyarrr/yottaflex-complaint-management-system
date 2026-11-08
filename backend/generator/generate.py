
import argparse
import random
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from faker import Faker
from sqlalchemy.orm import Session

from backend.app.database import Base, SessionLocal, engine
from backend.app.models import Customer, Product, Order, OrderItem, Category


# --------------------------------------------------
# CONFIGURATION
# --------------------------------------------------

SEED = 20261022

fake = Faker("en_IN")


def reset_random_seed():
    """Reset random generators for reproducible data."""
    random.seed(SEED)
    Faker.seed(SEED)
    fake.seed_instance(SEED)


# --------------------------------------------------
# CUSTOMER GENERATION
# --------------------------------------------------

def generate_customers(db: Session, count: int):
    """Generate synthetic customer records."""

    customers = []

    for number in range(1, count + 1):
        customer = Customer(
            customer_id=f"CUS-{number:06d}",
            full_name=fake.name(),
            email=f"customer{number}@example.com",
            phone=f"9{number % 1000000000:09d}",
            region=random.choice([
                "North India",
                "South India",
                "East India",
                "West India",
                "Central India"
            ]),
            is_vulnerable=random.random() < 0.05,
            status="ACTIVE"
        )

        customers.append(customer)

    db.add_all(customers)
    db.flush()

    print(f"Generated {len(customers)} customers.")


# --------------------------------------------------
# PRODUCT GENERATION
# --------------------------------------------------

def generate_products(db: Session, count: int):
    """Generate synthetic product records."""

    product_types = [
        "Electronics",
        "Home Appliances",
        "Fashion",
        "Furniture",
        "Accessories",
        "Kitchen",
        "Personal Care",
        "Sports"
    ]

    products = []

    for number in range(1, count + 1):
        category = random.choice(product_types)

        product = Product(
            product_id=f"PROD-{number:06d}",
            product_name=f"{fake.word().title()} {category}",
            category_name=category,
            unit_price=round(random.uniform(200, 50000), 2),
            is_safety_sensitive=category in [
                "Electronics",
                "Home Appliances",
                "Kitchen"
            ],
            status="ACTIVE"
        )

        products.append(product)

    db.add_all(products)
    db.flush()

    print(f"Generated {len(products)} products.")


# --------------------------------------------------
# CATEGORY GENERATION
# --------------------------------------------------

def generate_categories(db: Session):
    """Generate the 10 complaint categories without duplicates."""

    categories = [
        ("DELIVERY", "Delivery delays, tracking and shipment issues"),
        ("REFUND", "Refund and reimbursement requests"),
        ("PAYMENT", "Payment failures, billing and incorrect charges"),
        ("DAMAGED PRODUCT", "Damaged, defective or malfunctioning products"),
        ("PRODUCT SAFETY", "Safety hazards, injuries and dangerous products"),
        ("MISSING ITEM", "Missing items or incomplete orders"),
        ("CANCELLATION", "Order cancellation requests"),
        ("WARRANTY", "Warranty, repair and replacement requests"),
        ("ACCOUNT", "Account access and login problems"),
        ("OTHER", "Complaints that do not fit another category")
    ]

    existing_names = {
        category.category_name
        for category in db.query(Category).all()
    }

    added = 0

    for name, description in categories:
        if name not in existing_names:
            category = Category(
                category_name=name,
                description=description,
                is_active=True
            )

            db.add(category)
            added += 1

    db.flush()

    print(f"Added {added} complaint categories.")
    print(f"Total categories: {db.query(Category).count()}")


# --------------------------------------------------
# ORDER AND ORDER ITEM GENERATION
# --------------------------------------------------

def generate_orders(db: Session, count: int):
    """Generate orders and associated order items."""

    customers = db.query(Customer).order_by(
        Customer.customer_id
    ).all()

    products = db.query(Product).order_by(
        Product.product_id
    ).all()

    if not customers or not products:
        raise ValueError(
            "Customers and products must exist before generating orders."
        )

    orders = []
    order_items = []

    base_date = datetime(2026, 1, 1, tzinfo=timezone.utc)

    for number in range(1, count + 1):

        customer = random.choice(customers)

        selected_products = random.sample(
            products,
            k=random.randint(1, min(3, len(products)))
        )

        order_date = base_date + timedelta(
            days=random.randint(0, 300)
        )

        order_id = f"ORD-2026-{number:06d}"

        order_total = Decimal("0.00")

        current_items = []

        for product in selected_products:

            quantity = random.randint(1, 3)

            unit_price = Decimal(str(product.unit_price))

            line_total = (
                unit_price * quantity
            ).quantize(Decimal("0.01"))

            order_total += line_total

            current_items.append(
                OrderItem(
                    order_id=order_id,
                    product_id=product.product_id,
                    quantity=quantity,
                    unit_price=unit_price,
                    line_total=line_total
                )
            )

        order = Order(
            order_id=order_id,
            customer_id=customer.customer_id,
            order_date=order_date,
            total_amount=order_total,
            payment_status=random.choice([
                "PAID",
                "PAID",
                "PENDING",
                "FAILED",
                "REFUNDED"
            ]),
            order_status=random.choice([
                "PROCESSING",
                "SHIPPED",
                "DELIVERED",
                "CANCELLED"
            ]),
            shipping_region=customer.region
        )

        orders.append(order)
        order_items.extend(current_items)

    db.add_all(orders)
    db.flush()

    db.add_all(order_items)
    db.flush()

    print(f"Generated {len(orders)} orders.")
    print(f"Generated {len(order_items)} order items.")


# --------------------------------------------------
# MAIN GENERATOR
# --------------------------------------------------

def main():

    parser = argparse.ArgumentParser(
        description="Generate synthetic complaint-system data."
    )

    parser.add_argument(
        "--mode",
        choices=["starter", "full"],
        default="starter"
    )

    args = parser.parse_args()

    reset_random_seed()

    if args.mode == "starter":

        customer_count = 100
        product_count = 30
        order_count = 160

    else:

        customer_count = 5000
        product_count = 500
        order_count = 8000

    Base.metadata.create_all(bind=engine)

    db = SessionLocal()

    try:

        existing_customers = db.query(Customer).count()
        existing_products = db.query(Product).count()
        existing_orders = db.query(Order).count()

        # Check whether existing master data matches selected mode.
        if existing_customers not in (0, customer_count):
            raise RuntimeError(
                f"Expected 0 or {customer_count} customers, "
                f"found {existing_customers}."
            )

        if existing_products not in (0, product_count):
            raise RuntimeError(
                f"Expected 0 or {product_count} products, "
                f"found {existing_products}."
            )

        # Generate master data only when missing.
        if existing_customers == 0:
            generate_customers(db, customer_count)
        else:
            print(f"Using existing {existing_customers} customers.")

        if existing_products == 0:
            generate_products(db, product_count)
        else:
            print(f"Using existing {existing_products} products.")

        # Generate complaint categories.
        generate_categories(db)

        # Generate orders only when they do not already exist.
        if existing_orders == 0:
            generate_orders(db, order_count)
        else:
            print(f"Using existing {existing_orders} orders.")
            print("Skipping order generation to avoid duplicates.")

        db.commit()

        print("\nData generation completed successfully.")
        print(f"Mode: {args.mode}")
        print(f"Seed: {SEED}")

    except Exception:

        db.rollback()
        raise

    finally:

        db.close()


if __name__ == "__main__":
    main()
