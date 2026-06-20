"""
Run ShopSphere with a local mocked DynamoDB backend using moto.
No AWS account or Docker required.
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
import db

mock = mock_aws()
mock.start()

client = boto3.client("dynamodb", region_name=Config.REGION)

# ─── Products Table ──────────────────────────────────────────────────────────
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

resource = boto3.resource("dynamodb", region_name=Config.REGION)
products_table = resource.Table(Config.PRODUCTS_TABLE)
products_table.wait_until_exists()
print(f"✅ Products table '{Config.PRODUCTS_TABLE}' created in local mock mode.")

# ─── Reviews Table ───────────────────────────────────────────────────────────
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

reviews_table = resource.Table(Config.REVIEWS_TABLE)
reviews_table.wait_until_exists()
print(f"✅ Reviews table '{Config.REVIEWS_TABLE}' created in local mock mode.")

print("🚀 Starting ShopSphere on http://0.0.0.0:5000")

from app import app
app.run(debug=True, host="0.0.0.0", port=5000)
