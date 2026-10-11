from backend.database import db
from flask_login import UserMixin
from werkzeug.security import check_password_hash

from backend.config import BRAND_NAME, ORDER_PREFIX

# Homepage sections / product tags. key -> (title, icon, short description)
PRODUCT_TAGS = {
    "flash_sale": ("Flash Sales", "fa-bolt", "Limited-time deals"),
    "top_deal": ("Top Deals", "fa-tags", "Biggest price drops"),
    "new_arrival": ("New Arrivals", "fa-star", f"Fresh on {BRAND_NAME}"),
    "best_seller": ("Best Sellers", "fa-ranking-star", "Most loved by shoppers"),
    "trending": ("Trending Now", "fa-fire", "What everyone is buying"),
    "official_store": ("Official Store", "fa-certificate", f"Sold by {BRAND_NAME}"),
}

ORDER_STATUSES = ["pending", "confirmed", "processing", "shipped", "delivered", "cancelled"]
SELLER_STATUS_FLOW = ["confirmed", "processing", "shipped", "delivered"]


class User(UserMixin, db.Model):

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)

    username = db.Column(db.String(80), unique=True, nullable=False)

    email = db.Column(db.String(120), unique=True, nullable=False)

    password_hash = db.Column(db.String(256), nullable=False)

    # One of: "customer", "seller", "admin"
    role = db.Column(db.String(20), nullable=False, default="customer", server_default="customer")

    avatar_url = db.Column(db.String(300), nullable=True)

    suspended = db.Column(db.Boolean, nullable=False, default=False, server_default=db.false())

    created_at = db.Column(db.DateTime, server_default=db.func.now())

    products = db.relationship("Product", backref="seller", lazy=True)

    @property
    def is_admin(self):
        return self.role == "admin"

    @property
    def is_seller(self):
        return self.role == "seller"

    @property
    def is_customer(self):
        return self.role == "customer"

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Category(db.Model):
    """Two levels: departments (parent_id is NULL) and sub-categories."""

    __tablename__ = "categories"

    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String(120), nullable=False)

    slug = db.Column(db.String(140), unique=True, nullable=False)

    parent_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=True)

    icon = db.Column(db.String(60), nullable=True)

    # Which product-API group this category borrows products from when it has none of its own
    api_group = db.Column(db.String(60), nullable=True)

    children = db.relationship(
        "Category", backref=db.backref("parent", remote_side=[id]), lazy=True, order_by="Category.id"
    )


class Product(db.Model):

    __tablename__ = "products"

    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String(160), nullable=False)

    description = db.Column(db.Text, nullable=True)

    price = db.Column(db.Numeric(12, 2), nullable=False)

    # Original price before discount (shown struck-through)
    old_price = db.Column(db.Numeric(12, 2), nullable=True)

    # Cover image (kept in sync with the first ProductImage)
    image_url = db.Column(db.String(500), nullable=True)

    seller_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=True)

    stock = db.Column(db.Integer, nullable=False, default=0, server_default="0")

    brand = db.Column(db.String(80), nullable=True)

    sku = db.Column(db.String(60), nullable=True)

    condition = db.Column(db.String(30), nullable=True)

    color = db.Column(db.String(60), nullable=True)

    size = db.Column(db.String(60), nullable=True)

    weight = db.Column(db.Numeric(8, 2), nullable=True)

    warranty = db.Column(db.String(120), nullable=True)

    key_features = db.Column(db.Text, nullable=True)       # one per line
    specifications = db.Column(db.Text, nullable=True)     # "Key: value" per line
    box_contents = db.Column(db.Text, nullable=True)
    return_policy = db.Column(db.String(160), nullable=True)

    # Comma-delimited with outer commas, e.g. ",flash_sale,new_arrival,"
    tags = db.Column(db.String(255), nullable=True)

    rating = db.Column(db.Float, nullable=False, default=0, server_default="0")
    rating_count = db.Column(db.Integer, nullable=False, default=0, server_default="0")

    is_active = db.Column(db.Boolean, nullable=False, default=True, server_default=db.true())

    created_at = db.Column(db.DateTime, server_default=db.func.now())

    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())

    category = db.relationship("Category")
    images = db.relationship(
        "ProductImage", backref="product", lazy=True,
        order_by="ProductImage.position", cascade="all, delete-orphan",
    )
    reviews = db.relationship(
        "Review", backref="product", lazy=True,
        order_by="Review.created_at.desc()", cascade="all, delete-orphan",
    )

    # ----- helpers -----
    @property
    def tag_list(self):
        return [t for t in (self.tags or "").split(",") if t]

    def has_tag(self, tag):
        return tag in self.tag_list

    def set_tags(self, tags):
        valid = [t for t in tags if t in PRODUCT_TAGS]
        self.tags = ("," + ",".join(valid) + ",") if valid else None

    @property
    def discount_percent(self):
        if self.old_price and self.old_price > self.price:
            return int(round((1 - float(self.price) / float(self.old_price)) * 100))
        return 0

    @property
    def image_list(self):
        urls = [img.url for img in self.images]
        if not urls and self.image_url:
            urls = [self.image_url]
        return urls

    @property
    def in_stock(self):
        return self.stock > 0

    @property
    def feature_lines(self):
        return [l.strip() for l in (self.key_features or "").splitlines() if l.strip()]

    @property
    def spec_rows(self):
        rows = []
        for line in (self.specifications or "").splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                rows.append((k.strip(), v.strip()))
        return rows


class ProductImage(db.Model):

    __tablename__ = "product_images"

    id = db.Column(db.Integer, primary_key=True)

    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)

    url = db.Column(db.String(500), nullable=False)

    position = db.Column(db.Integer, nullable=False, default=0, server_default="0")


class Review(db.Model):

    __tablename__ = "reviews"

    id = db.Column(db.Integer, primary_key=True)

    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    author_name = db.Column(db.String(80), nullable=False)

    rating = db.Column(db.Integer, nullable=False)

    comment = db.Column(db.Text, nullable=True)

    created_at = db.Column(db.DateTime, server_default=db.func.now())


class Cart(db.Model):

    __tablename__ = "carts"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)

    quantity = db.Column(db.Integer, default=1, nullable=False)

    user = db.relationship("User", backref="cart")
    product = db.relationship("Product")


class Order(db.Model):

    __tablename__ = "orders"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    total = db.Column(db.Numeric(12, 2), nullable=False)

    status = db.Column(db.String(50), default="pending")

    shipping_name = db.Column(db.String(120), nullable=True)
    shipping_phone = db.Column(db.String(40), nullable=True)
    shipping_address = db.Column(db.String(300), nullable=True)
    shipping_city = db.Column(db.String(80), nullable=True)

    created_at = db.Column(db.DateTime, server_default=db.func.now())

    user = db.relationship("User", backref="orders")

    @property
    def reference(self):
        return f"{ORDER_PREFIX}{1000 + self.id}"

    @property
    def can_cancel(self):
        return self.status in ("pending", "confirmed")


class OrderItem(db.Model):

    __tablename__ = "order_items"

    id = db.Column(db.Integer, primary_key=True)

    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=False)

    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)

    quantity = db.Column(db.Integer, default=1, nullable=False)

    # Price at the time of purchase, so later price changes don't alter old orders
    price = db.Column(db.Numeric(12, 2), nullable=False)

    order = db.relationship("Order", backref="items")
    product = db.relationship("Product")
