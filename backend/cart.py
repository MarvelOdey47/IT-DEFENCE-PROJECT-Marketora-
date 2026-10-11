from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user

from backend.database import db
from backend.models import Cart, Product
from backend.utils import customer_required

cart_bp = Blueprint("cart", __name__)


def cart_total(items):
    return sum(item.product.price * item.quantity for item in items)


@cart_bp.route("/cart")
@customer_required
def cart_view():
    items = Cart.query.filter_by(user_id=current_user.id).order_by(Cart.id).all()
    return render_template("cart/view.html", items=items, total=cart_total(items))


@cart_bp.route("/cart/add/<int:product_id>", methods=["POST"])
@customer_required
def cart_add(product_id):
    product = Product.query.get_or_404(product_id)
    qty = max(1, request.form.get("quantity", 1, type=int) or 1)
    back = request.referrer or url_for("products.product_detail", product_id=product_id)

    if not product.is_active or product.stock < 1:
        flash("Sorry, this product is out of stock.", "danger")
        return redirect(back)

    item = Cart.query.filter_by(user_id=current_user.id, product_id=product_id).first()
    new_qty = (item.quantity if item else 0) + qty
    if new_qty > product.stock:
        new_qty = product.stock
        flash(f"Only {product.stock} unit(s) available - quantity adjusted.", "warning")

    if item:
        item.quantity = new_qty
    else:
        db.session.add(Cart(user_id=current_user.id, product_id=product_id, quantity=new_qty))
    db.session.commit()
    flash(f"'{product.name}' added to your cart.", "success")

    if request.form.get("buy_now"):
        return redirect(url_for("cart.cart_view"))
    return redirect(back)


@cart_bp.route("/cart/update/<int:product_id>", methods=["POST"])
@customer_required
def cart_update(product_id):
    item = Cart.query.filter_by(user_id=current_user.id, product_id=product_id).first_or_404()
    action = request.form.get("action")
    qty = item.quantity

    if action == "inc":
        qty += 1
    elif action == "dec":
        qty -= 1
    else:
        qty = request.form.get("quantity", qty, type=int)

    if qty < 1:
        db.session.delete(item)
        flash("Item removed from your cart.", "info")
    else:
        if qty > item.product.stock:
            qty = item.product.stock
            flash(f"Only {qty} unit(s) available.", "warning")
        item.quantity = qty
    db.session.commit()
    return redirect(url_for("cart.cart_view"))


@cart_bp.route("/cart/remove/<int:product_id>", methods=["POST"])
@customer_required
def cart_remove(product_id):
    item = Cart.query.filter_by(user_id=current_user.id, product_id=product_id).first_or_404()
    db.session.delete(item)
    db.session.commit()
    flash("Product removed from cart.", "info")
    return redirect(url_for("cart.cart_view"))
