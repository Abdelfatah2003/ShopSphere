# ShopSphere — Product Catalog & Customer Feedback Platform

ShopSphere is a cloud-native, NoSQL-powered e-commerce product catalog built with **Python (Flask)** and **AWS DynamoDB**. It demonstrates real-world NoSQL data modeling, query optimization with Global Secondary Indexes (GSIs), and scalable product management with customer reviews.

## Features

- **Product CRUD** — Create, read, update, and delete products
- **Customer Reviews** — Submit ratings (1–5) and comments, computed average rating
- **Category Filtering** — Efficient GSI-based query (no Scan)
- **Pagination** — DynamoDB-native pagination with Previous/Next controls
- **Review Sorting** — Sort reviews by date or rating, ascending or descending
- **Hard Delete** — Products are permanently removed from DynamoDB
- **Duplicate Review Prevention** — Prevents duplicate reviews per customer per product
- **Timestamps** — ISO 8601 `created_at` / `updated_at` on all items
- **Atomic Rating Updates** — Average rating computed and stored on the product item

## DynamoDB Schema Design

### Two-Table Design

**ShopSphere_Products**

| PK | Attributes |
|---|---|
| `product_id` | name, description, category, price, stock_quantity, avg_rating, review_count, is_deleted, created_at, updated_at |

**ShopSphere_Reviews**

| PK | SK | Attributes |
|---|---|---|
| `product_id` | `created_at#review_id` | review_id, customer_name, rating, comment, created_at |

### Access Patterns

| Pattern | Operation |
|---|---|
| Get product by ID | `GetItem(PK=product_id)` on Products table |
| List all products | `Scan()` on Products table — acceptable for MVP; paginated |
| Products by category | **Query on CategoryIndex GSI** — efficient, no Scan |
| Reviews for a product | `Query(PK=product_id)` on Reviews table |
| Sort reviews by date | Native SK ordering (`ScanIndexForward`) |
| Sort reviews by rating | In-memory sort after Query (fine for typical review counts) |

### Global Secondary Indexes

**CategoryIndex** (on Products table)
- PK: `category` (string) — SK: `created_at` (string)
- Projects: ALL — enables efficient product listing by category

**ProductReviewsIndex** (on Reviews table)
- PK: `product_id` (string) — SK: `created_at` (string)
- Projects: ALL — enables date-sorted access to reviews

### Why Two Tables?

Products and reviews have different access patterns and lifecycles. Separating them into two tables provides cleaner schema design, simpler query patterns, and better isolation. The products table uses `product_id` as a simple hash key, while the reviews table uses a composite key (`product_id` + `created_at#review_id`) to group reviews by product and enable native date sorting.

## Setup Instructions

### Prerequisites
- Python 3.10+
- pip

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/Abdelfatah2003/ShopSphere.git
cd ShopSphere

# 2. (Recommended) Create a virtual environment
python3 -m venv venv
source venv/bin/activate   # Linux/Mac
# venv\Scripts\activate    # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run locally (uses moto to mock DynamoDB — no AWS account needed)
python run_local.py

# 5. Open http://localhost:5000 in your browser
```

### Running with Real AWS DynamoDB

1. Ensure your AWS credentials are configured in `.env`:
   ```
   DYNAMO_MODE=aws
   AWS_ACCESS_KEY_ID=your_access_key
   AWS_SECRET_ACCESS_KEY=your_secret_key
   AWS_SESSION_TOKEN=your_session_token
   AWS_REGION=us-east-1
   PRODUCTS_TABLE=ShopSphere_Products
   REVIEWS_TABLE=ShopSphere_Reviews
   ```
2. Run: `python app.py`

## Project Structure

```
shopsphere/
├── app.py              # Flask application (routes)
├── config.py           # Configuration (DynamoDB mode, credentials)
├── db.py               # DynamoDB repository layer (all data operations)
├── run_local.py        # Local launcher with moto mock
├── requirements.txt    # Python dependencies
├── .env                # Environment variables (not committed)
├── .gitignore
├── README.md
├── templates/
│   ├── base.html       # Base layout with navigation
│   ├── index.html      # Product listing with category filter + pagination
│   ├── product.html    # Product detail + reviews
│   ├── add_product.html
│   ├── edit_product.html
│   ├── admin.html      # Admin panel for product management
│   └── error.html
└── static/
    └── style.css
```

## GSI Query vs Scan: Cost & Performance

| Approach | Read Cost | Latency | Scalability |
|---|---|---|---|
| **Scan** on full table | Reads every item (RCUs = item size × all items) | Increases linearly with table size | ❌ Does not scale |
| **Query on GSI** (CategoryIndex) | Reads only matching items (RCUs = item size × matching items) | Fast, proportional to result set | ✅ Scales to millions |

In this project, the category filter initially used a `Scan` with `FilterExpression`. It was refactored to use a **Query on the CategoryIndex GSI**, reducing read costs from O(n) to O(k) where k is the number of items in the category.

## Screenshots

*(Add screenshots here before submission — see examples below)*

### Product Catalog
![Product Catalog](./screenshots/catalog.png)

### Product Detail with Reviews
![Product Detail](./screenshots/product-detail.png)

### Add Product Form
![Add Product](./screenshots/add-product.png)

### Admin Panel
![Admin Panel](./screenshots/admin.png)

## Modification Challenges Implemented

The following scenarios from the assignment have been pre-implemented:

- **Scenario A** — Atomic counters for average rating (`update_product_rating` uses `UpdateItem` with SET)
- **Scenario B** — GSI-based category filter (CategoryIndex with Query instead of Scan)
- **Scenario C** — Pagination with `LastEvaluatedKey` / `ExclusiveStartKey` (Previous/Next controls)
- **Scenario D** — Soft/Hard delete (soft delete sets `is_deleted=true`; hard delete calls `DeleteItem`)
- **Scenario E** — ISO 8601 timestamps on all items (`created_at`, `updated_at`)
- **Scenario F** — Duplicate review prevention (ConditionExpression on PutItem)

## Video Walkthrough

1. **Introduction** — Name, student ID, and what ShopSphere does
2. **Architecture** — DynamoDB schema (two tables, GSIs, single-table vs multi-table design)
3. **Live Demo** — Add product, browse catalog, submit review
4. **Code Walkthrough** — DynamoDB connection, Query/PutItem, review aggregation
5. **Reflection** — One challenge and resolution

## Resources Used

- AWS DynamoDB Documentation
- Flask Documentation
- boto3 SDK Documentation
