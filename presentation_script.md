# ShopSphere — Video Presentation Script (8-10 minutes)

---

## 1. Introduction (1 min)

**Hello, my name is [Your Name], student ID [Your ID].**

Today I'll be presenting **ShopSphere**, a cloud-native e-commerce product catalog and customer review platform powered by **AWS DynamoDB** and built with **Python Flask**.

ShopSphere allows users to:
- Browse a product catalog with category filtering
- View product details with customer reviews
- Add, edit, and delete products
- Submit ratings and reviews

The project demonstrates real-world NoSQL data modeling using DynamoDB's single-table design pattern, Global Secondary Indexes for efficient queries, pagination, and various advanced DynamoDB features.

---

## 2. Architecture Overview (1.5 min)

Let me walk you through the architecture.

ShopSphere is a **Flask web application** with server-side rendered HTML templates. It uses **two DynamoDB tables**:

| Table | Primary Key | Purpose |
|---|---|---|
| `ShopSphere_Products` | `product_id` (HASH) | Stores all product data |
| `ShopSphere_Reviews` | `product_id` (HASH) + `sk` (RANGE) | Stores customer reviews |

The project is structured into three main layers:

1. **`app.py`** — Flask routes that handle HTTP requests, form validation, and template rendering
2. **`db.py`** — The data access layer with all DynamoDB operations
3. **`config.py`** — Configuration for DynamoDB mode (local mock vs real AWS)

**[SHOW: project directory tree or architecture diagram]**

```
shopsphere/
├── app.py         → Flask routes
├── db.py          → DynamoDB operations
├── config.py      → AWS configuration
├── templates/     → HTML templates
└── static/        → CSS styles
```

---

## 3. DynamoDB Schema Design (1.5 min)

Let me explain the database design.

### Products Table

Products are stored in their own table with `product_id` as the primary key. Each product item contains:

```
{
  "product_id": "a1b2c3d4e5f6",
  "name": "Wireless Headphones",
  "category": "Electronics",
  "price": 79.99,
  "stock_quantity": 50,
  "avg_rating": 4.2,
  "review_count": 15,
  "is_deleted": false,
  "created_at": "2026-06-20T10:30:00",
  "updated_at": "2026-06-20T10:30:00"
}
```

### Reviews Table

Reviews use a composite key:
- **Partition Key**: `product_id` — groups all reviews for a product together
- **Sort Key**: `created_at#review_id` — enables native date-based sorting

This means all reviews for a product are stored together and can be efficiently queried.

### Global Secondary Indexes

I created two GSIs:

1. **CategoryIndex** on the Products table — allows querying products by category without scanning the entire table. This reduced read costs from O(n) to O(k), where k is the number of items in the category.

2. **ProductReviewsIndex** on the Reviews table — provides an alternative access pattern for date-sorted review access.

### Why Two Tables Instead of One?

The original design used a single-table approach, but I separated them for better isolation and simpler query patterns. Products and reviews have different access patterns and lifecycles, so separate tables make the schema cleaner and more maintainable.

---

## 4. Live Demo (2.5 min)

Let me show the application running.

**[START SCREEN RECORDING — open http://localhost:5000]**

### Browsing the Catalog

Here's the main product catalog page. It shows all products with their name, category, price, rating, and stock quantity.

**[Click on a product category filter to show category filtering]**

The category filter uses a **Query on the CategoryIndex GSI** — notice how fast it is. This is because we're only reading the items that match the category, not scanning the entire table.

### Product Detail and Reviews

If I click on a product, I see its details along with customer reviews. You can sort reviews by date or by rating, ascending or descending.

**[Demonstrate sorting reviews]**

Let me submit a new review. I'll enter my name, a rating, and a comment.

**[Submit a review and show the updated average rating]**

The average rating is updated atomically using DynamoDB's `UpdateItem`. Notice how the average rating changed after I submitted my review.

### Adding a Product

Let me add a new product.

**[Fill out the add product form and submit]**

The new product appears in the catalog immediately.

### Pagination

If we had many products, the pagination controls let you navigate through them. DynamoDB uses `LastEvaluatedKey` for pagination — there's no offset-based paging like in SQL databases.

**[Show previous/next buttons and navigate pages]**

### Admin Panel

The admin panel shows all products with edit and delete options.

**[Show the admin panel, then delete a product]**

When I delete a product, it's permanently removed from the DynamoDB table using the `DeleteItem` API call.

---

## 5. Code Walkthrough (1.5 min)

Let me walk through the key code sections.

### Initializing DynamoDB (config.py + db.py)

**[Show config.py]**

The configuration reads from a `.env` file with the DynamoDB mode, table names, region, and AWS credentials. In development, we use `moto`, a library that mocks AWS services locally — no AWS account needed.

**[Show get_dynamodb_resource and table initialization]**

Here's how we create the DynamoDB resource. The `ensure_tables()` function checks if tables exist and creates them with the proper schema and GSIs if needed.

### Querying Products by Category (db.py)

**[Show get_all_products function]**

This is the key function. If a category is provided, it uses a **Query** on the CategoryIndex GSI — this is efficient and scalable. Without a category, it falls back to a Scan, which reads all items.

```python
if category:
    response = table.query(
        IndexName="CategoryIndex",
        KeyConditionExpression="category = :cat",
        ...
    )
```

### Review Submission with Duplicate Prevention

**[Show create_review function]**

Before submitting a review, we check if this customer has already reviewed this product. We query existing reviews and filter by customer name. If a duplicate is found, we return an error message.

After a review is submitted, we recalculate the product's average rating using `update_product_rating`.

### Pagination in DynamoDB

**[Show pagination in app.py]**

DynamoDB pagination uses `LastEvaluatedKey` and `ExclusiveStartKey` — not page numbers. The server stores page keys in the session to enable both forward and backward navigation.

---

## 6. Feature Highlights (1 min)

Let me briefly highlight the implemented features:

| Feature | How it works |
|---|---|
| **Atomic Rating Updates** | `UpdateItem` recalculates the average rating after each review submission |
| **GSI-based Category Filter** | Query on CategoryIndex instead of Scan with FilterExpression |
| **Pagination** | DynamoDB-native with Next/Previous controls via session-stored keys |
| **Soft/Hard Delete** | Soft delete sets `is_deleted=true`; hard delete calls `DeleteItem` |
| **ISO 8601 Timestamps** | Every item has `created_at` and `updated_at` in UTC |
| **Duplicate Review Prevention** | Queries existing reviews before allowing a new submission |
| **Review Sorting** | Date sorting via native Sort Key order; rating sorting in-memory |

---

## 7. Reflection (1 min)

The biggest challenge I faced was **designing the DynamoDB schema** to support all access patterns efficiently.

Initially, the category filter used a `Scan` with a `FilterExpression`, which reads every item in the table — fine for small datasets but does not scale. I refactored it to use a **Global Secondary Index with a Query operation**, reducing read costs from reading all items to reading only matching items.

Another key learning was **DynamoDB's single-table vs multi-table design**. While single-table design is a NoSQL best practice for keeping related data co-located, I found that separating products and reviews into two tables made the access patterns clearer and the code simpler, especially as the application grew.

The project taught me how to think in terms of **access patterns first** rather than data structure first — a fundamental shift from relational database design.

---

## 8. Resources (30 sec)

The project uses:
- **AWS DynamoDB** — fully managed NoSQL database
- **Flask** — Python web framework
- **boto3** — AWS SDK for Python
- **moto** — AWS mock for local development

For development and testing, you can run the entire application locally using `moto` without any AWS account. To deploy to production, just configure real AWS credentials and set `DYNAMO_MODE=aws`.

---

**Thank you for watching!**

*Questions?*
