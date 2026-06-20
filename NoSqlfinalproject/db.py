import json
import boto3
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from config import Config

PRODUCTS_GSI = [
    {
        "IndexName": "CategoryIndex",
        "KeySchema": [
            {"AttributeName": "category", "KeyType": "HASH"},
            {"AttributeName": "created_at", "KeyType": "RANGE"},
        ],
        "Projection": {"ProjectionType": "ALL"},
    },
]

REVIEWS_GSI = [
    {
        "IndexName": "ProductReviewsIndex",
        "KeySchema": [
            {"AttributeName": "product_id", "KeyType": "HASH"},
            {"AttributeName": "created_at", "KeyType": "RANGE"},
        ],
        "Projection": {"ProjectionType": "ALL"},
    },
]


def get_dynamodb_resource():
    kwargs = {
        "aws_access_key_id": Config.AWS_ACCESS_KEY_ID,
        "aws_secret_access_key": Config.AWS_SECRET_ACCESS_KEY,
        "region_name": Config.REGION,
    }
    if Config.AWS_SESSION_TOKEN:
        kwargs["aws_session_token"] = Config.AWS_SESSION_TOKEN
    return boto3.resource("dynamodb", **kwargs)


def get_products_table():
    return get_dynamodb_resource().Table(Config.PRODUCTS_TABLE)


def get_reviews_table():
    return get_dynamodb_resource().Table(Config.REVIEWS_TABLE)


def ensure_products_table():
    resource = get_dynamodb_resource()
    existing = [t.name for t in resource.tables.all()]
    if Config.PRODUCTS_TABLE in existing:
        return
    table = resource.create_table(
        TableName=Config.PRODUCTS_TABLE,
        KeySchema=[
            {"AttributeName": "product_id", "KeyType": "HASH"},
        ],
        AttributeDefinitions=[
            {"AttributeName": "product_id", "AttributeType": "S"},
            {"AttributeName": "category", "AttributeType": "S"},
            {"AttributeName": "created_at", "AttributeType": "S"},
        ],
        GlobalSecondaryIndexes=PRODUCTS_GSI,
        BillingMode="PAY_PER_REQUEST",
    )
    table.wait_until_exists()


def ensure_reviews_table():
    resource = get_dynamodb_resource()
    existing = [t.name for t in resource.tables.all()]
    if Config.REVIEWS_TABLE in existing:
        return
    table = resource.create_table(
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
        GlobalSecondaryIndexes=REVIEWS_GSI,
        BillingMode="PAY_PER_REQUEST",
    )
    table.wait_until_exists()


def ensure_tables():
    ensure_products_table()
    ensure_reviews_table()


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def generate_id():
    return uuid.uuid4().hex[:12]


def serialize_for_dynamo(item):
    if isinstance(item, dict):
        return {k: serialize_for_dynamo(v) for k, v in item.items()}
    elif isinstance(item, list):
        return [serialize_for_dynamo(v) for v in item]
    elif isinstance(item, float):
        return Decimal(str(item))
    return item


def deserialize_from_dynamo(item):
    if isinstance(item, dict):
        return {k: deserialize_from_dynamo(v) for k, v in item.items()}
    elif isinstance(item, list):
        return [deserialize_from_dynamo(v) for v in item]
    elif isinstance(item, Decimal):
        return float(item) if item % 1 != 0 else int(item)
    return item


# ─── Product CRUD ───────────────────────────────────────────────────────────


def create_product(name, description, category, price, stock_quantity, image_url=""):
    table = get_products_table()
    product_id = generate_id()
    now = now_iso()
    item = serialize_for_dynamo({
        "product_id": product_id,
        "name": name,
        "description": description,
        "category": category,
        "price": price,
        "stock_quantity": int(stock_quantity),
        "image_url": image_url,
        "is_deleted": False,
        "created_at": now,
        "updated_at": now,
        "avg_rating": 0.0,
        "review_count": 0,
    })
    table.put_item(Item=item)
    return product_id


def get_product(product_id):
    table = get_products_table()
    response = table.get_item(Key={"product_id": product_id})
    item = response.get("Item")
    if not item:
        return None
    return deserialize_from_dynamo(item)


def get_all_products(category=None, page_size=10, last_key=None):
    table = get_products_table()
    if category:
        kwargs = {
            "IndexName": "CategoryIndex",
            "KeyConditionExpression": "category = :cat",
            "ExpressionAttributeValues": {":cat": category},
            "Limit": page_size,
            "ScanIndexForward": False,
        }
        if last_key:
            kwargs["ExclusiveStartKey"] = last_key
        response = table.query(**kwargs)
    else:
        kwargs = {"Limit": page_size}
        if last_key:
            kwargs["ExclusiveStartKey"] = last_key
        response = table.scan(**kwargs)

    items = [deserialize_from_dynamo(i) for i in response.get("Items", [])]
    items = [i for i in items if not i.get("is_deleted", False)]
    last_evaluated_key = response.get("LastEvaluatedKey")
    return items, last_evaluated_key


def get_all_products_including_deleted(category=None, page_size=20, last_key=None):
    table = get_products_table()
    if category:
        kwargs = {
            "IndexName": "CategoryIndex",
            "KeyConditionExpression": "category = :cat",
            "ExpressionAttributeValues": {":cat": category},
            "Limit": page_size,
            "ScanIndexForward": False,
        }
        if last_key:
            kwargs["ExclusiveStartKey"] = last_key
        response = table.query(**kwargs)
    else:
        kwargs = {"Limit": page_size}
        if last_key:
            kwargs["ExclusiveStartKey"] = last_key
        response = table.scan(**kwargs)

    items = [deserialize_from_dynamo(i) for i in response.get("Items", [])]
    last_evaluated_key = response.get("LastEvaluatedKey")
    return items, last_evaluated_key


def update_product(product_id, **kwargs):
    table = get_products_table()
    key = {"product_id": product_id}

    update_parts = []
    expr_values = {}
    expr_names = {}

    for field, value in kwargs.items():
        if value is not None:
            key_attr = f"#{field}"
            update_parts.append(f"{key_attr} = :{field}")
            expr_names[key_attr] = field
            expr_values[f":{field}"] = serialize_for_dynamo(value)

    if not update_parts:
        return False

    update_parts.append("#updated_at = :now")
    expr_names["#updated_at"] = "updated_at"
    expr_values[":now"] = now_iso()

    expression = "SET " + ", ".join(update_parts)
    table.update_item(
        Key=key,
        UpdateExpression=expression,
        ExpressionAttributeNames=expr_names,
        ExpressionAttributeValues=expr_values,
    )
    return True


def delete_product(product_id, hard=False):
    table = get_products_table()
    if hard:
        table.delete_item(Key={"product_id": product_id})
        return True
    return update_product(product_id, is_deleted=True)


def restore_product(product_id):
    return update_product(product_id, is_deleted=False)


# ─── Review CRUD ────────────────────────────────────────────────────────────


def create_review(product_id, customer_name, rating, comment):
    reviews_table = get_reviews_table()
    now = now_iso()
    review_id = generate_id()

    existing = reviews_table.query(
        KeyConditionExpression="product_id = :pid",
        FilterExpression="customer_name = :name",
        ExpressionAttributeValues={
            ":pid": product_id,
            ":name": customer_name,
        },
    )
    if existing.get("Items"):
        return None, "Duplicate review: you have already submitted a review for this product."

    item = serialize_for_dynamo({
        "product_id": product_id,
        "sk": f"{now}#{review_id}",
        "review_id": review_id,
        "customer_name": customer_name,
        "rating": int(rating),
        "comment": comment,
        "created_at": now,
    })
    reviews_table.put_item(Item=item)
    update_product_rating(product_id)
    return review_id, None


def get_reviews_for_product(product_id, sort_by="date", sort_order="desc"):
    table = get_reviews_table()
    response = table.query(
        KeyConditionExpression="product_id = :pid",
        ExpressionAttributeValues={":pid": product_id},
        ScanIndexForward=(sort_order == "asc"),
    )
    items = [deserialize_from_dynamo(i) for i in response.get("Items", [])]

    if sort_by == "rating":
        items.sort(key=lambda r: r.get("rating", 0), reverse=(sort_order == "desc"))

    return items


def update_product_rating(product_id):
    reviews = get_reviews_for_product(product_id)
    review_count = len(reviews)

    if review_count == 0:
        avg_rating = 0.0
    else:
        avg_rating = sum(r.get("rating", 0) for r in reviews) / review_count

    table = get_products_table()
    table.update_item(
        Key={"product_id": product_id},
        UpdateExpression="SET avg_rating = :avg, review_count = :cnt",
        ExpressionAttributeValues={
            ":avg": Decimal(str(round(avg_rating, 2))),
            ":cnt": review_count,
        },
    )


# ─── Categories ─────────────────────────────────────────────────────────────


def get_all_categories():
    table = get_products_table()
    response = table.scan(
        FilterExpression="attribute_exists(category)",
        ProjectionExpression="category",
    )
    categories = set()
    for item in response.get("Items", []):
        if "category" in item:
            categories.add(item["category"])

    while "LastEvaluatedKey" in response:
        response = table.scan(
            ExclusiveStartKey=response["LastEvaluatedKey"],
            FilterExpression="attribute_exists(category)",
            ProjectionExpression="category",
        )
        for item in response.get("Items", []):
            if "category" in item:
                categories.add(item["category"])

    return sorted(categories)


# ─── Key Encoding for Pagination ───────────────────────────────────────────


def encode_key(key):
    if key is None:
        return ""
    return json.dumps(key, default=str)


def decode_key(raw):
    if not raw:
        return None
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        return None
