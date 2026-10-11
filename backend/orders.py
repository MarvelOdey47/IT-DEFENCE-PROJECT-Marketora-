from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user

from backend.database import db
from backend.forms import CheckoutForm
from backend.models import ORDER_STATUSES, Cart, Order, OrderItem
from backend.utils import customer_required

orders_bp = Blueprint("orders", __name__)

STATUS_STEPS = ["pending", "confirmed", "processing", "shipped", "delivered"]


# Allowed next steps for a seller moving an order along (admins may set any status)
NEXT_STATUSES = {
    "pending": ["confirmed", "cancelled"],
    "confirmed": ["processing", "cancelled"],
    "processing": ["shipped"],
    "shipped": ["delivered"],
}


def apply_status(order, new_status, is_admin=False):
    """Change an order's status. Returns an error message, or None on success."""
    if new_status not in ORDER_STATUSES:
        return "Unknown status."
    if order.status == new_status:
        return None
    if not is_admin and new_status not in NEXT_STATUSES.get(order.status, []):
        return f"An order that is {order.status} cannot be moved to {new_status}."
    if new_status == "cancelled" and order.status != "cancelled":
        restock(order)
    elif order.status == "cancelled":
        return "A cancelled order cannot be reopened."
    order.status = new_status
    return None


def restock(order):
    for item in order.items:
        if item.product:
            item.product.stock += item.quantity


def cancel_order(order):
    restock(order)
    order.status = "cancelled"


@orders_bp.route("/checkout", methods=["GET", "POST"])
@customer_required
def checkout():
    items = Cart.query.filter_by(user_id=current_user.id).all()

    if not items:
        flash("Your cart is empty.", "warning")
        return redirect(url_for("products.product_list"))

    total = sum(item.product.price * item.quantity for item in items)
    form = CheckoutForm()
    if request.method == "GET":
        form.full_name.data = current_user.username

    if form.validate_on_submit():
        # Re-check stock at the moment of ordering
        problems = [i for i in items if not i.product.is_active or i.quantity > i.product.stock]
        if problems:
            for i in problems:
                flash(f"'{i.product.name}' only has {i.product.stock} unit(s) left. Please update your cart.", "danger")
            return redirect(url_for("cart.cart_view"))

        order = Order(
            user_id=current_user.id, total=total,
            shipping_name=form.full_name.data, shipping_phone=form.phone.data,
            shipping_address=form.address.data, shipping_city=form.city.data,
        )
        db.session.add(order)
        db.session.flush()

        for item in items:
            db.session.add(OrderItem(
                order_id=order.id, product_id=item.product_id,
                quantity=item.quantity, price=item.product.price,
            ))
            item.product.stock -= item.quantity
            db.session.delete(item)

        db.session.commit()
        flash(f"Order {order.reference} placed successfully!", "success")
        return redirect(url_for("orders.order_detail", order_id=order.id))

    return render_template("orders/checkout.html", items=items, total=total, form=form)


@orders_bp.route("/orders")
@customer_required
def order_list():
    orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.created_at.desc()).all()
    return render_template("orders/list.html", orders=orders)


@orders_bp.route("/orders/<int:order_id>")
@customer_required
def order_detail(order_id):
    order = Order.query.get_or_404(order_id)
    if order.user_id != current_user.id:
        abort(404)
    return render_template("orders/detail.html", order=order, steps=STATUS_STEPS)


@orders_bp.route("/orders/<int:order_id>/cancel", methods=["POST"])
@customer_required
def order_cancel(order_id):
    order = Order.query.get_or_404(order_id)
    if order.user_id != current_user.id:
        abort(404)
    if not order.can_cancel:
        flash("This order can no longer be cancelled.", "danger")
    else:
        cancel_order(order)
        db.session.commit()
        flash(f"Order {order.reference} was cancelled.", "info")
    return redirect(url_for("orders.order_detail", order_id=order.id))
