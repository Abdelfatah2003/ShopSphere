from flask import Flask, render_template, request, redirect, url_for, flash, session
import db

app = Flask(__name__)
app.secret_key = "shopsphere-secret-key-change-in-production"


@app.context_processor
def inject_globals():
    categories = db.get_all_categories()
    return dict(categories=categories)


# ─── Home / Product Listing ────────────────────────────────────────────────


@app.route("/")
def index():
    category = request.args.get("category", "")
    page_size = int(request.args.get("page_size", 10))
    session_key = f"pgkeys_{category or '_all'}"

    direction = request.args.get("dir", "")
    page_keys = session.get(session_key, [])

    last_key = None
    if direction == "next":
        if page_keys:
            last_key = page_keys[-1]
    elif direction == "prev":
        if page_keys:
            page_keys.pop()
        if page_keys:
            last_key = page_keys[-1]
        session[session_key] = page_keys
    # else: first page, no last_key, keep existing page_keys

    category_param = category if category else None
    items, next_key_raw = db.get_all_products(category=category_param, page_size=page_size, last_key=last_key)

    if next_key_raw:
        if direction == "next":
            page_keys.append(next_key_raw)
        elif not direction:
            page_keys[:] = [next_key_raw]
        session[session_key] = page_keys

    has_prev = len(page_keys) > 0
    has_next = next_key_raw is not None

    return render_template(
        "index.html",
        products=items,
        category=category,
        has_prev=has_prev,
        has_next=has_next,
        page_size=page_size,
    )


# ─── Product Detail ─────────────────────────────────────────────────────────


@app.route("/product/<product_id>")
def product_detail(product_id):
    product = db.get_product(product_id)
    if not product:
        flash("Product not found.", "error")
        return render_template("error.html", message="Product not found.")

    sort_by = request.args.get("sort_by", "date")
    sort_order = request.args.get("sort_order", "desc")
    reviews = db.get_reviews_for_product(product_id, sort_by=sort_by, sort_order=sort_order)

    return render_template("product.html", product=product, reviews=reviews, sort_by=sort_by, sort_order=sort_order)


# ─── Add Product ────────────────────────────────────────────────────────────


@app.route("/product/add", methods=["GET", "POST"])
def add_product():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()
        category = request.form.get("category", "").strip()
        price = request.form.get("price", "").strip()
        stock_quantity = request.form.get("stock_quantity", "0").strip()
        image_url = request.form.get("image_url", "").strip()

        errors = []
        if not name:
            errors.append("Product name is required.")
        if not category:
            errors.append("Category is required.")
        if not price:
            errors.append("Price is required.")
        else:
            try:
                price = float(price)
                if price <= 0:
                    errors.append("Price must be greater than 0.")
            except ValueError:
                errors.append("Price must be a number.")

        try:
            stock_quantity = int(stock_quantity)
            if stock_quantity < 0:
                errors.append("Stock quantity cannot be negative.")
        except ValueError:
            errors.append("Stock quantity must be an integer.")

        if errors:
            for err in errors:
                flash(err, "error")
            return render_template("add_product.html", form=request.form)

        product_id = db.create_product(name, description, category, price, stock_quantity, image_url)
        flash(f"Product '{name}' created successfully!", "success")
        return redirect(url_for("product_detail", product_id=product_id))

    return render_template("add_product.html", form={})


# ─── Edit Product ───────────────────────────────────────────────────────────


@app.route("/product/<product_id>/edit", methods=["GET", "POST"])
def edit_product(product_id):
    product = db.get_product(product_id)
    if not product:
        flash("Product not found.", "error")
        return render_template("error.html", message="Product not found.")

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()
        category = request.form.get("category", "").strip()
        price = request.form.get("price", "").strip()
        stock_quantity = request.form.get("stock_quantity", "").strip()
        image_url = request.form.get("image_url", "").strip()

        errors = []
        if not name:
            errors.append("Product name is required.")
        if not category:
            errors.append("Category is required.")
        if not price:
            errors.append("Price is required.")
        else:
            try:
                price = float(price)
                if price <= 0:
                    errors.append("Price must be greater than 0.")
            except ValueError:
                errors.append("Price must be a number.")

        try:
            stock_quantity = int(stock_quantity)
            if stock_quantity < 0:
                errors.append("Stock quantity cannot be negative.")
        except ValueError:
            errors.append("Stock quantity must be an integer.")

        if errors:
            for err in errors:
                flash(err, "error")
            return render_template("edit_product.html", product=product)

        db.update_product(
            product_id,
            name=name,
            description=description,
            category=category,
            price=price,
            stock_quantity=stock_quantity,
            image_url=image_url,
        )
        flash("Product updated successfully!", "success")
        return redirect(url_for("product_detail", product_id=product_id))

    return render_template("edit_product.html", product=product)


# ─── Delete / Restore Product ──────────────────────────────────────────────


@app.route("/product/<product_id>/delete", methods=["POST"])
def delete_product(product_id):
    product = db.get_product(product_id)
    if not product:
        flash("Product not found.", "error")
        return redirect(url_for("index"))

    db.delete_product(product_id, hard=True)
    flash(f"Product '{product['name']}' has been deleted.", "warning")
    return redirect(url_for("index"))


# ─── Reviews ────────────────────────────────────────────────────────────────


@app.route("/product/<product_id>/review", methods=["POST"])
def add_review(product_id):
    product = db.get_product(product_id)
    if not product:
        flash("Product not found.", "error")
        return redirect(url_for("index"))

    customer_name = request.form.get("customer_name", "").strip()
    rating = request.form.get("rating", "").strip()
    comment = request.form.get("comment", "").strip()

    errors = []
    if not customer_name:
        errors.append("Your name is required.")
    if not rating:
        errors.append("Rating is required.")
    else:
        try:
            rating = int(rating)
            if rating < 1 or rating > 5:
                errors.append("Rating must be between 1 and 5.")
        except ValueError:
            errors.append("Rating must be a number between 1 and 5.")

    if not comment:
        errors.append("Comment is required.")

    if errors:
        for err in errors:
            flash(err, "error")
        return redirect(url_for("product_detail", product_id=product_id))

    review_id, error = db.create_review(product_id, customer_name, int(rating), comment)
    if error:
        flash(error, "error")
    else:
        flash("Review submitted successfully!", "success")

    return redirect(url_for("product_detail", product_id=product_id))


# ─── Admin ──────────────────────────────────────────────────────────────────


@app.route("/admin")
def admin_panel():
    page_size = int(request.args.get("page_size", 20))
    last_key = db.decode_key(request.args.get("last_key", ""))

    items, next_key = db.get_all_products_including_deleted(page_size=page_size, last_key=last_key)
    next_key_param = db.encode_key(next_key)

    return render_template("admin.html", products=items, next_key=next_key_param)


# ─── Main ───────────────────────────────────────────────────────────────────


if __name__ == "__main__":
    db.ensure_tables()
    app.run(debug=True, host="0.0.0.0", port=5000)
