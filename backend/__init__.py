import os
from datetime import datetime, timedelta

from flask import Flask, jsonify, redirect, render_template, url_for
from flask_login import LoginManager, current_user, login_required
from flask_wtf.csrf import CSRFProtect
from sqlalchemy import func

from backend import catalog
from backend.admin import admin_bp
from backend.auth import auth_bp
from backend.cart import cart_bp
from backend.config import BRAND_NAME, Config
from backend.database import db
from backend import news
from backend.models import PRODUCT_TAGS, Cart, Order, User
from backend.orders import orders_bp
from backend.portals import PortalMiddleware, PortalSessionInterface, current_portal, portal_url
from backend.products import products_bp
from backend.seller import seller_bp
from backend.utils import get_category_tree

login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.login_message_category = "info"

csrf = CSRFProtect()


@login_manager.user_loader
def load_user(user_id):
    user = db.session.get(User, int(user_id))
    # Suspended accounts are signed out on their next request
    if user is None or user.suspended:
        return None
    return user


def create_app():

    template_dir = os.path.join(os.path.dirname(__file__), "..", "templates")
    static_dir = os.path.join(os.path.dirname(__file__), "..", "static")

    app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)

    app.config.from_object(Config)

    # One session cookie per portal (/, /seller, /admin) so several logins can coexist in one browser
    app.session_interface = PortalSessionInterface()
    app.wsgi_app = PortalMiddleware(app.wsgi_app)
    app.jinja_env.globals["portal_url"] = portal_url

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    app.register_blueprint(auth_bp)
    app.register_blueprint(products_bp)
    app.register_blueprint(cart_bp)
    app.register_blueprint(orders_bp)
    app.register_blueprint(seller_bp)
    app.register_blueprint(admin_bp)

    @app.template_filter("naira")
    def naira(value):
        try:
            return "₦{:,.0f}".format(float(value))
        except (TypeError, ValueError):
            return "₦0"

    @app.context_processor
    def inject_globals():
        cart_count = 0
        if current_user.is_authenticated and current_user.role == "customer":
            cart_count = db.session.query(func.coalesce(func.sum(Cart.quantity), 0)).filter(
                Cart.user_id == current_user.id
            ).scalar()
        return {
            "category_tree": get_category_tree(), "cart_count": cart_count, "PRODUCT_TAGS": PRODUCT_TAGS,
            "BRAND": BRAND_NAME, "portal": current_portal(),
        }

    @app.route("/")
    def index():
        if current_portal() == "admin":
            # /admin is the staff entrance: sign-in page, or the dashboard when already signed in
            if current_user.is_authenticated and current_user.role == "admin":
                return redirect(url_for("admin.dashboard"))
            return redirect(url_for("admin.login"))
        tree = get_category_tree()
        official = catalog.tagged_products("official_store", 12)
        hero = catalog.hero_products(4)
        midnight = (datetime.now() + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        return render_template(
            "index.html",
            sections=catalog.home_sections(),
            strips=catalog.department_strips(tree),
            hero_products=hero,
            official=official,
            flash_ends=midnight.isoformat(),
        )

    @app.route("/news/feed")
    def news_feed():
        return jsonify(news.get_news())

    @app.route("/dashboard")
    @login_required
    def dashboard():
        if current_user.role == "admin":
            return redirect(url_for("admin.dashboard"))
        if current_user.role == "seller":
            return redirect(url_for("seller.dashboard"))

        orders = Order.query.filter_by(user_id=current_user.id)
        counts = dict(
            db.session.query(Order.status, func.count(Order.id))
            .filter(Order.user_id == current_user.id).group_by(Order.status).all()
        )
        in_progress = sum(counts.get(s, 0) for s in ("pending", "confirmed", "processing", "shipped"))
        spent = db.session.query(func.coalesce(func.sum(Order.total), 0)).filter(
            Order.user_id == current_user.id, Order.status != "cancelled"
        ).scalar()
        return render_template(
            "dashboard.html",
            total_orders=orders.count(), in_progress=in_progress, delivered=counts.get("delivered", 0),
            spent=spent, recent_orders=orders.order_by(Order.created_at.desc()).limit(5).all(),
        )

    return app
