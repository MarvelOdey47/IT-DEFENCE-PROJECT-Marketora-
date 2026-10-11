import re
from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_user
from sqlalchemy import func
from backend.database import db
from backend.forms import AdminLoginForm, CategoryForm
from backend.models import ORDER_STATUSES, Category, Order, OrderItem, Product, User
from backend.orders import apply_status
from backend.utils import admin_required, clear_category_cache


admin_bp = Blueprint("admin", __name__)


@admin_bp.route("/console/login", methods=["GET", "POST"])
def login():
    """Unlisted admin sign-in page. Visiting /admin (the admin portal) leads here."""
    if current_user.is_authenticated and current_user.role == "admin":
        return redirect(url_for("admin.dashboard"))

    form = AdminLoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.role == "admin" and user.check_password(form.password.data):
            login_user(user)
            return redirect(url_for("admin.dashboard"))
        flash("Invalid admin credentials.", "danger")
    return render_template("admin/login.html", form=form)


@admin_bp.route("/console/dashboard")
@admin_required
def dashboard():
    revenue = (
        db.session.query(func.coalesce(func.sum(Order.total), 0)).filter(Order.status != "cancelled").scalar()
    )
    role_counts = dict(db.session.query(User.role, func.count(User.id)).group_by(User.role).all())
    status_counts = dict(db.session.query(Order.status, func.count(Order.id)).group_by(Order.status).all())

    return render_template(
        "admin/dashboard.html",
        user_count=User.query.count(),
        product_count=Product.query.filter_by(is_active=True).count(),
        order_count=Order.query.count(),
        category_count=Category.query.count(),
        revenue=revenue,
        role_counts=role_counts,
        status_counts=status_counts,
        statuses=ORDER_STATUSES,
        recent_users=User.query.order_by(User.created_at.desc()).limit(5).all(),
        recent_orders=Order.query.order_by(Order.created_at.desc()).limit(5).all(),
        recent_products=Product.query.order_by(Product.created_at.desc()).limit(5).all(),
    )


# ---------------------------------------------------------------- users
@admin_bp.route("/console/users")
@admin_required
def users():
    q = request.args.get("q", "").strip()
    role = request.args.get("role", "")
    page = request.args.get("page", 1, type=int)
    query = User.query
    if q:
        query = query.filter(db.or_(User.username.ilike(f"%{q}%"), User.email.ilike(f"%{q}%")))
    if role:
        query = query.filter(User.role == role)
    pagination = query.order_by(User.created_at.desc()).paginate(page=page, per_page=15, error_out=False)
    return render_template("admin/users.html", pagination=pagination, users=pagination.items, q=q, role=role)


@admin_bp.route("/console/users/<int:user_id>/suspend", methods=["POST"])
@admin_required
def toggle_suspend(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id or user.role == "admin":
        flash("Admin accounts cannot be suspended.", "danger")
    else:
        user.suspended = not user.suspended
        db.session.commit()
        flash(f"{user.username} has been {'suspended' if user.suspended else 'reactivated'}.", "success")
    return redirect(request.referrer or url_for("admin.users"))


@admin_bp.route("/console/users/<int:user_id>/role", methods=["POST"])
@admin_required
def change_role(user_id):
    user = User.query.get_or_404(user_id)
    role = request.form.get("role")
    if user.id == current_user.id:
        flash("You cannot change your own role.", "danger")
    elif role not in ("customer", "seller", "admin"):
        flash("Unknown role.", "danger")
    else:
        user.role = role
        db.session.commit()
        flash(f"{user.username} is now a {role}.", "success")
    return redirect(request.referrer or url_for("admin.users"))


# ---------------------------------------------------------------- products
@admin_bp.route("/console/products")
@admin_required
def products():
    q = request.args.get("q", "").strip()
    page = request.args.get("page", 1, type=int)
    query = Product.query
    if q:
        query = query.filter(db.or_(Product.name.ilike(f"%{q}%"), Product.brand.ilike(f"%{q}%")))
    pagination = query.order_by(Product.created_at.desc(), Product.id.desc()).paginate(
        page=page, per_page=15, error_out=False
    )
    return render_template("admin/products.html", pagination=pagination, products=pagination.items, q=q)


# ---------------------------------------------------------------- categories
def slugify(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def parent_choices():
    return [(0, "- None (this is a department) -")] + [
        (c.id, c.name) for c in Category.query.filter(Category.parent_id.is_(None)).order_by(Category.name)
    ]


@admin_bp.route("/console/categories", methods=["GET", "POST"])
@admin_required
def categories():
    form = CategoryForm()
    form.parent_id.choices = parent_choices()

    if form.validate_on_submit():
        slug = slugify(form.name.data)
        if Category.query.filter_by(slug=slug).first():
            slug = f"{slug}-{Category.query.count() + 1}"
        parent = Category.query.get(form.parent_id.data) if form.parent_id.data else None
        db.session.add(Category(
            name=form.name.data, slug=slug, parent_id=parent.id if parent else None,
            icon=parent.icon if parent else "fa-tag", api_group=parent.api_group if parent else None,
        ))
        db.session.commit()
        clear_category_cache()
        flash("Category added.", "success")
        return redirect(url_for("admin.categories"))

    q = request.args.get("q", "").strip()
    page = request.args.get("page", 1, type=int)
    query = Category.query
    if q:
        query = query.filter(Category.name.ilike(f"%{q}%"))
    pagination = query.order_by(Category.parent_id.is_(None).desc(), Category.id).paginate(
        page=page, per_page=20, error_out=False
    )
    counts = dict(
        db.session.query(Product.category_id, func.count(Product.id)).group_by(Product.category_id).all()
    )
    return render_template(
        "admin/categories.html", form=form, pagination=pagination, categories=pagination.items, q=q, counts=counts,
    )


@admin_bp.route("/console/categories/<int:category_id>/rename", methods=["POST"])
@admin_required
def rename_category(category_id):
    category = Category.query.get_or_404(category_id)
    name = request.form.get("name", "").strip()
    if name:
        category.name = name[:120]
        db.session.commit()
        clear_category_cache()
        flash("Category renamed.", "success")
    return redirect(request.referrer or url_for("admin.categories"))


@admin_bp.route("/console/categories/<int:category_id>/delete", methods=["POST"])
@admin_required
def delete_category(category_id):
    category = Category.query.get_or_404(category_id)
    if category.children:
        flash("Delete or move its sub-categories first.", "danger")
    elif Product.query.filter_by(category_id=category.id).first():
        flash("This category still has products. Move them first.", "danger")
    else:
        db.session.delete(category)
        db.session.commit()
        clear_category_cache()
        flash("Category deleted.", "success")
    return redirect(request.referrer or url_for("admin.categories"))


# ---------------------------------------------------------------- orders
@admin_bp.route("/console/orders")
@admin_required
def orders():
    status = request.args.get("status", "")
    page = request.args.get("page", 1, type=int)
    query = Order.query
    if status:
        query = query.filter(Order.status == status)
    pagination = query.order_by(Order.created_at.desc()).paginate(page=page, per_page=15, error_out=False)
    return render_template(
        "admin/orders.html", pagination=pagination, orders=pagination.items, status=status, statuses=ORDER_STATUSES,
    )


@admin_bp.route("/console/orders/<int:order_id>/status", methods=["POST"])
@admin_required
def update_order_status(order_id):
    order = Order.query.get_or_404(order_id)
    error = apply_status(order, request.form.get("status", ""), is_admin=True)
    if error:
        flash(error, "danger")
    else:
        db.session.commit()
        flash(f"Order {order.reference} is now {order.status}.", "success")
    return redirect(request.referrer or url_for("admin.orders"))
