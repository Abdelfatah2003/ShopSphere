"""
Integration tests for ShopSphere using moto mock.
Tests all CRUD operations and edge cases with two DynamoDB tables.
"""
import os
os.environ["DYNAMO_MODE"] = "local"
os.environ["AWS_ACCESS_KEY_ID"] = "fakeAccessKeyId"
os.environ["AWS_SECRET_ACCESS_KEY"] = "fakeSecretAccessKey"
os.environ["AWS_REGION"] = "us-east-1"
os.environ["PRODUCTS_TABLE"] = "ShopSphere_Products"
os.environ["REVIEWS_TABLE"] = "ShopSphere_Reviews"

from moto import mock_aws
import boto3
from config import Config


def setup_tables():
    client = boto3.client("dynamodb", region_name=Config.REGION)

    # Products table
    client.create_table(
        TableName=Config.PRODUCTS_TABLE,
        KeySchema=[
            {"AttributeName": "product_id", "KeyType": "HASH"},
        ],
        AttributeDefinitions=[
            {"AttributeName": "product_id", "AttributeType": "S"},
            {"AttributeName": "category", "AttributeType": "S"},
            {"AttributeName": "created_at", "AttributeType": "S"},
        ],
        GlobalSecondaryIndexes=[
            {
                "IndexName": "CategoryIndex",
                "KeySchema": [
                    {"AttributeName": "category", "KeyType": "HASH"},
                    {"AttributeName": "created_at", "KeyType": "RANGE"},
                ],
                "Projection": {"ProjectionType": "ALL"},
            },
        ],
        BillingMode="PAY_PER_REQUEST",
    )

    # Reviews table
    client.create_table(
        TableName=Config.REVIEWS_TABLE,
        KeySchema=[
            {"AttributeName": "product_id", "KeyType": "HASH"},
            {"AttributeName": "sk", "KeyType": "RANGE"},
        ],
        AttributeDefinitions=[
            {"AttributeName": "product_id", "AttributeType": "S"},
            {"AttributeName": "sk", "AttributeType": "S"},
            {"AttributeName": "created_at", "AttributeType": "S"},
        ],
        GlobalSecondaryIndexes=[
            {
                "IndexName": "ProductReviewsIndex",
                "KeySchema": [
                    {"AttributeName": "product_id", "KeyType": "HASH"},
                    {"AttributeName": "created_at", "KeyType": "RANGE"},
                ],
                "Projection": {"ProjectionType": "ALL"},
            },
        ],
        BillingMode="PAY_PER_REQUEST",
    )

    resource = boto3.resource("dynamodb", region_name=Config.REGION)
    resource.Table(Config.PRODUCTS_TABLE).wait_until_exists()
    resource.Table(Config.REVIEWS_TABLE).wait_until_exists()
    print("✅ Tables created")


# Run tests
mock = mock_aws()
mock.start()
setup_tables()

import db

# ─── Product Tests ───────────────────────────────────────────────────────

print("\n--- Product CRUD Tests ---")

# Create a product
pid1 = db.create_product("Test Product", "A test", "Electronics", 29.99, 100, "")
assert pid1 is not None
print(f"✅ Created product: {pid1}")

# Get product
prod = db.get_product(pid1)
assert prod is not None
assert prod["name"] == "Test Product"
assert prod["category"] == "Electronics"
assert prod["price"] == 29.99
assert prod["stock_quantity"] == 100
assert prod["is_deleted"] is False
assert prod["created_at"] is not None
assert prod["updated_at"] is not None
print(f"✅ Got product: {prod['name']}")

# Create another product in different category
pid2 = db.create_product("Another Product", "Another test", "Books", 15.50, 50, "http://example.com/img.jpg")

# Get all products
items, next_key = db.get_all_products()
assert len(items) == 2
print(f"✅ Listed {len(items)} products")

# Filter by category
items, _ = db.get_all_products(category="Electronics")
assert len(items) == 1
assert items[0]["name"] == "Test Product"
print(f"✅ Filtered by Electronics: {len(items)} product(s)")

items, _ = db.get_all_products(category="Books")
assert len(items) == 1
assert items[0]["name"] == "Another Product"
print(f"✅ Filtered by Books: {len(items)} product(s)")

# Update product
db.update_product(pid1, name="Updated Product", price=39.99)
prod = db.get_product(pid1)
assert prod["name"] == "Updated Product"
assert prod["price"] == 39.99
print(f"✅ Updated product: {prod['name']}")

# Soft delete
db.delete_product(pid1)
prod = db.get_product(pid1)
assert prod["is_deleted"] is True
print(f"✅ Soft-deleted product: is_deleted={prod['is_deleted']}")

# Verify soft-deleted doesn't show in normal listing
items, _ = db.get_all_products()
assert len(items) == 1
print(f"✅ Normal listing excludes deleted: {len(items)} product(s)")

# Verify admin view shows all
items, _ = db.get_all_products_including_deleted()
assert len(items) == 2
print(f"✅ Admin listing includes deleted: {len(items)} product(s)")

# Restore
db.restore_product(pid1)
prod = db.get_product(pid1)
assert prod["is_deleted"] is False
items, _ = db.get_all_products()
assert len(items) == 2
print(f"✅ Restored product, listing count: {len(items)}")

# Hard delete
db.delete_product(pid1, hard=True)
prod = db.get_product(pid1)
assert prod is None
items, _ = db.get_all_products()
assert len(items) == 1
print(f"✅ Hard deleted product, listing count: {len(items)}")

# ─── Review Tests ────────────────────────────────────────────────────────

print("\n--- Review Tests ---")

# Add reviews
rid1, err = db.create_review(pid2, "Alice", 5, "Great book!")
assert err is None
assert rid1 is not None
print(f"✅ Created review: {rid1}")

rid2, err = db.create_review(pid2, "Bob", 3, "Decent read")
assert err is None
print(f"✅ Created review: {rid2}")

rid3, err = db.create_review(pid2, "Charlie", 4, "Pretty good")
assert err is None
print(f"✅ Created review: {rid3}")

# Duplicate prevention
rid4, err = db.create_review(pid2, "Alice", 2, "Trying again")
assert err is not None
assert "Duplicate" in err
assert rid4 is None
print(f"✅ Duplicate prevented: {err}")

# Get reviews for product
reviews = db.get_reviews_for_product(pid2)
assert len(reviews) == 3
print(f"✅ Got {len(reviews)} reviews for product")

# Sort by rating descending
reviews_desc = db.get_reviews_for_product(pid2, sort_by="rating", sort_order="desc")
assert reviews_desc[0]["rating"] >= reviews_desc[-1]["rating"]
print(f"✅ Reviews sorted by rating desc: [{reviews_desc[0]['rating']}...{reviews_desc[-1]['rating']}]")

# Sort by date
reviews_date = db.get_reviews_for_product(pid2, sort_by="date", sort_order="asc")
assert reviews_date[0]["created_at"] <= reviews_date[-1]["created_at"]
print(f"✅ Reviews sorted by date asc")

# Check avg rating
prod = db.get_product(pid2)
assert abs(prod["avg_rating"] - 4.0) < 0.1
assert prod["review_count"] == 3
print(f"✅ Avg rating: {prod['avg_rating']} ({prod['review_count']} reviews)")

# ─── Edge Cases ──────────────────────────────────────────────────────────

print("\n--- Edge Cases ---")

# Non-existent product
prod = db.get_product("nonexistent")
assert prod is None
print("✅ Non-existent product returns None")

# Empty category filter
items, _ = db.get_all_products(category="NonExistent")
assert len(items) == 0
print(f"✅ Empty category returns 0 products")

# No reviews
reviews = db.get_reviews_for_product("nonexistent")
assert len(reviews) == 0
print(f"✅ Non-existent product returns 0 reviews")

# Categories list
cats = db.get_all_categories()
assert "Books" in cats
assert "Electronics" not in cats
print(f"✅ Categories: {cats}")

print("\n🎉 ALL TESTS PASSED!")
