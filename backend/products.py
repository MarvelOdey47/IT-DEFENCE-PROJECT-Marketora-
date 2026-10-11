import secrets

from flask import Blueprint, abort, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from backend import catalog
from backend.database import db
from backend.forms import ProductForm, ReviewForm
from backend.models import PRODUCT_TAGS, Cart, Category, Order, OrderItem, Product, ProductImage, Review
from backend.utils import (
    customer_required, get_category_tree, parse_image_urls, role_required, save_uploaded_images,
)

products_bp = Blueprint("products", __name__)

PER_PAGE = 20
SORT_OPTIONS = [
    ("relevance", "Popularity"),
    ("newest", "Newest arrivals"),
    ("price_asc", "Price: low to high"),
    ("price_desc", "Price: high to low"),
    ("rating", "Customer rating"),
]


# ---------------------------------------------------------------- public pages
@products_bp.route("/products")
def product_list():
    return render_results(None)


@products_bp.route("/category/<slug>")
def category_page(slug):
    category = Category.query.filter_by(slug=slug).first_or_404()
    return render_results(category)


def render_results(category):
    q = request.args.get("q", "").strip()
    sort = request.args.get("sort", "relevance")
    page = request.args.get("page", 1, type=int)
    min_price = request.args.get("min", type=float)
    max_price = request.args.get("max", type=float)
    brand = request.args.get("brand", "").strip()
    tag = request.args.get("tag", "")
    if tag not in PRODUCT_TAGS:
        tag = ""

    if category is None and request.args.get("category"):
        category = Category.query.filter_by(slug=request.args["category"]).first()

    query = catalog.category_query(category) if category else catalog.active_products()
    if q:
        like = f"%{q}%"
        query = query.filter(
            db.or_(Product.name.ilike(like), Product.brand.ilike(like), Product.description.ilike(like))
        )

    if tag:
        query = query.filter(Product.tags.like(f"%,{tag},%"))

    brands = catalog.brands_for(query)
    if brand:
        query = query.filter(Product.brand == brand)
    if min_price is not None:
        query = query.filter(Product.price >= min_price)
    if max_price is not None:
        query = query.filter(Product.price <= max_price)

    pagination = catalog.apply_sort(query, sort).paginate(page=page, per_page=PER_PAGE, error_out=False)

    return render_template(
        "products/list.html",
        products=pagination.items, pagination=pagination, q=q, sort=sort, sort_options=SORT_OPTIONS,
        category=category, brands=brands, brand=brand, min_price=min_price, max_price=max_price,
        tag=tag, tag_names=PRODUCT_TAGS,
        parent=category.parent if category and category.parent_id else category,
    )


@products_bp.route("/explore")
def explore():
    seed = request.args.get("seed") or secrets.token_hex(3)
    products = catalog.endless_page(0, seed)
    return render_template("products/explore.html", products=products, seed=seed)


@products_bp.route("/hero/feed")
def hero_feed():
    items = [
        {
            "id": p.id, "name": p.name[:48], "brand": p.brand or "Top brand", "image": p.image_url,
            "price": "₦{:,.0f}".format(float(p.price)), "discount": p.discount_percent,
            "url": url_for("products.product_detail", product_id=p.id),
        }
        for p in catalog.hero_products(4)
    ]
    return jsonify({"items": items})


@products_bp.route("/explore/feed")
def explore_feed():
    page = request.args.get("page", 1, type=int)
    seed = request.args.get("seed", "0")
    products = catalog.endless_page(page, seed)
    html = "".join(render_template("partials/product_card.html", product=p) for p in products)
    return jsonify({"html": html, "next": page + 1})


@products_bp.route("/products/<int:product_id>")
def product_detail(product_id):
    product = Product.query.get_or_404(product_id)
    if not product.is_active and not can_manage(product):
        abort(404)

    similar = []
    if product.category_id:
        similar = (
            catalog.category_query(product.category.parent or product.category)
            .filter(Product.id != product.id)
            .order_by(Product.rating.desc())
            .limit(12)
            .all()
        )

    can_review = False
    if current_user.is_authenticated and current_user.role == "customer":
        can_review = (
            db.session.query(OrderItem.id)
            .join(Order, Order.id == OrderItem.order_id)
            .filter(
                Order.user_id == current_user.id, Order.status == "delivered",
                OrderItem.product_id == product.id,
            )
            .first() is not None
        )
        if can_review:
            can_review = not Review.query.filter_by(product_id=product.id, user_id=current_user.id).first()

    return render_template(
        "products/detail.html", product=product, similar=similar, can_manage=can_manage(product),
        can_review=can_review, review_form=ReviewForm(), tag_names=PRODUCT_TAGS,
    )


@products_bp.route("/products/<int:product_id>/review", methods=["POST"])
@customer_required
def product_review(product_id):
    product = Product.query.get_or_404(product_id)
    form = ReviewForm()
    bought = (
        db.session.query(OrderItem.id)
        .join(Order, Order.id == OrderItem.order_id)
        .filter(Order.user_id == current_user.id, Order.status == "delivered", OrderItem.product_id == product.id)
        .first()
    )
    if not bought:
        flash("You can only review products you have received.", "danger")
    elif Review.query.filter_by(product_id=product.id, user_id=current_user.id).first():
        flash("You have already reviewed this product.", "info")
    elif form.validate_on_submit():
        db.session.add(Review(
            product_id=product.id, user_id=current_user.id, author_name=current_user.username,
            rating=int(form.rating.data), comment=form.comment.data,
        ))
        db.session.flush()
        ratings = [r.rating for r in Review.query.filter_by(product_id=product.id).all()]
        product.rating = round(sum(ratings) / len(ratings), 2)
        product.rating_count = len(ratings)
        db.session.commit()
        flash("Thanks for your review!", "success")
    else:
        flash("Could not save your review.", "danger")
    return redirect(url_for("products.product_detail", product_id=product.id) + "#reviews")


# ------------------------------------------------------- seller / admin management
def can_manage(product):
    return current_user.is_authenticated and (
        current_user.role == "admin"
        or (current_user.role == "seller" and product.seller_id == current_user.id)
    )


def category_choices():
    choices = {}
    for dept in get_category_tree():
        choices[dept["name"]] = [(c["id"], c["name"]) for c in dept["children"]]
    return choices


def after_manage_redirect():
    if current_user.role == "admin":
        return redirect(url_for("admin.products"))
    return redirect(url_for("seller.products"))


def build_form(product=None):
    form = ProductForm(obj=product) if product is not None else ProductForm()
    form.category_id.choices = category_choices()
    if product is not None and request.method == "GET":
        form.image_urls.data = ""
    return form


def apply_form(product, form):
    for field in (
        "name", "brand", "condition", "price", "old_price", "stock", "sku", "color", "size",
        "weight", "warranty", "return_policy", "key_features", "description", "specifications",
        "box_contents", "category_id",
    ):
        setattr(product, field, getattr(form, field).data)
    for field in ("brand", "sku", "color", "size", "warranty", "return_policy", "key_features",
                  "description", "specifications", "box_contents"):
        if getattr(product, field) == "":
            setattr(product, field, None)

    allowed = set(PRODUCT_TAGS) if current_user.role == "admin" else set(PRODUCT_TAGS) - {"official_store"}
    chosen = [t for t in request.form.getlist("tags") if t in allowed]
    if current_user.role != "admin":
        # sellers cannot add or remove admin-only tags
        chosen += [t for t in product.tag_list if t not in allowed]
    product.set_tags(chosen)


def tags_valid(form):
    chosen = request.form.getlist("tags")
    if "flash_sale" in chosen:
        old, new = form.old_price.data, form.price.data
        if not old or not new or old <= new:
            form.old_price.errors.append("Flash sale products need an original price higher than the selling price.")
            return False
    return True


def collect_images():
    urls, errors = parse_image_urls(request.form.get("image_urls", ""))
    file_urls, file_errors = save_uploaded_images(request.files.getlist("image_files"))
    return urls + file_urls, errors + file_errors


def sync_cover(product):
    db.session.flush()
    db.session.refresh(product)
    product.image_url = product.images[0].url if product.images else None


@products_bp.route("/products/create", methods=["GET", "POST"])
@role_required("seller", "admin")
def product_create():
    form = build_form()

    if form.validate_on_submit():
        urls, errors = collect_images()
        for e in errors:
            flash(e, "warning")
        if not urls:
            flash("Add at least one product image (a link or an uploaded file).", "danger")
        elif tags_valid(form):
            product = Product(seller_id=current_user.id)
            apply_form(product, form)
            db.session.add(product)
            db.session.flush()
            for pos, url in enumerate(urls):
                db.session.add(ProductImage(product_id=product.id, url=url, position=pos))
            sync_cover(product)
            db.session.commit()
            flash("Product created successfully!", "success")
            return after_manage_redirect()

    return render_template("products/form.html", form=form, product=None, tag_names=PRODUCT_TAGS)


@products_bp.route("/products/<int:product_id>/edit", methods=["GET", "POST"])
@role_required("seller", "admin")
def product_edit(product_id):
    product = Product.query.get_or_404(product_id)
    if not can_manage(product):
        flash("You are not authorized to edit this product.", "danger")
        return redirect(url_for("products.product_detail", product_id=product_id))

    form = build_form(product)

    if form.validate_on_submit():
        urls, errors = collect_images()
        for e in errors:
            flash(e, "warning")

        remove_ids = {int(i) for i in request.form.getlist("remove_image") if i.isdigit()}
        remaining = [img for img in product.images if img.id not in remove_ids]

        if not remaining and not urls:
            flash("A product needs at least one image.", "danger")
        elif tags_valid(form):
            apply_form(product, form)
            for img in product.images:
                if img.id in remove_ids:
                    db.session.delete(img)
            start = max([img.position for img in remaining], default=-1) + 1
            for offset, url in enumerate(urls):
                db.session.add(ProductImage(product_id=product.id, url=url, position=start + offset))
            sync_cover(product)
            db.session.commit()
            flash("Product updated successfully!", "success")
            return after_manage_redirect()

    return render_template("products/form.html", form=form, product=product, tag_names=PRODUCT_TAGS)


@products_bp.route("/products/<int:product_id>/delete", methods=["POST"])
@role_required("seller", "admin")
def product_delete(product_id):
    product = Product.query.get_or_404(product_id)

    if not can_manage(product):
        flash("You are not authorized to delete this product.", "danger")
        return redirect(url_for("products.product_detail", product_id=product_id))

    Cart.query.filter_by(product_id=product.id).delete()
    if OrderItem.query.filter_by(product_id=product.id).first():
        # Past orders still reference it, so hide it instead of deleting
        product.is_active = False
        flash("This product has past orders, so it was removed from the store instead of being erased.", "info")
    else:
        db.session.delete(product)
        flash("Product deleted successfully!", "success")
    db.session.commit()
    return after_manage_redirect()
