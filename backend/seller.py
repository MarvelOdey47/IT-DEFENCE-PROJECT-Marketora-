from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user
from sqlalchemy import func

from backend.database import db
from backend.models import Order, OrderItem, Product
from backend.orders import NEXT_STATUSES, apply_status
from backend.utils import seller_required

seller_bp = Blueprint("seller", __name__)


def seller_orders_query():
    """Orders that contain at least one of this seller's products."""
    return (
        Order.query.join(OrderItem, OrderItem.order_id == Order.id)
        .join(Product, Product.id == OrderItem.product_id)
        .filter(Product.seller_id == current_user.id)
        .distinct()
    )


def seller_items(order):
    return [i for i in order.items if i.product and i.product.seller_id == current_user.id]


@seller_bp.route("/centre")
@seller_required
def dashboard():
    my_products = Product.query.filter_by(seller_id=current_user.id)
    product_count = my_products.count()
    low_stock = my_products.filter(Product.stock <= 5, Product.is_active.is_(True)).count()

    revenue = (
        db.session.query(func.coalesce(func.sum(OrderItem.price * OrderItem.quantity), 0))
        .join(Product, Product.id == OrderItem.product_id)
        .join(Order, Order.id == OrderItem.order_id)
        .filter(Product.seller_id == current_user.id, Order.status != "cancelled")
        .scalar()
    )
    orders = seller_orders_query().order_by(Order.created_at.desc())
    order_count = orders.count()
    pending = orders.filter(Order.status == "pending").count()
    recent_orders = orders.limit(5).all()
    recent_products = my_products.order_by(Product.created_at.desc()).limit(5).all()

    return render_template(
        "seller/dashboard.html", product_count=product_count, low_stock=low_stock, revenue=revenue,
        order_count=order_count, pending=pending, recent_orders=recent_orders,
        recent_products=recent_products, seller_items=seller_items,
    )


@seller_bp.route("/centre/products")
@seller_required
def products():
    q = request.args.get("q", "").strip()
    page = request.args.get("page", 1, type=int)
    query = Product.query.filter_by(seller_id=current_user.id)
    if q:
        query = query.filter(Product.name.ilike(f"%{q}%"))
    pagination = query.order_by(Product.created_at.desc()).paginate(page=page, per_page=12, error_out=False)
    return render_template("seller/products.html", pagination=pagination, products=pagination.items, q=q)


@seller_bp.route("/centre/orders")
@seller_required
def orders():
    status = request.args.get("status", "")
    page = request.args.get("page", 1, type=int)
    query = seller_orders_query()
    if status:
        query = query.filter(Order.status == status)
    pagination = query.order_by(Order.created_at.desc()).paginate(page=page, per_page=10, error_out=False)
    return render_template(
        "seller/orders.html", pagination=pagination, orders=pagination.items, status=status,
        seller_items=seller_items, next_statuses=NEXT_STATUSES,
    )


@seller_bp.route("/centre/orders/<int:order_id>/status", methods=["POST"])
@seller_required
def update_order_status(order_id):
    order = seller_orders_query().filter(Order.id == order_id).first_or_404()
    error = apply_status(order, request.form.get("status", ""))
    if error:
        flash(error, "danger")
    else:
        db.session.commit()
        flash(f"Order {order.reference} is now {order.status}.", "success")
    return redirect(request.referrer or url_for("seller.orders"))
