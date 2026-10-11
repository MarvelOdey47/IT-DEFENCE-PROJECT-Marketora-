"""
Seeds the 500-category taxonomy and imports demo products from the free
DummyJSON API (https://dummyjson.com) as products sold by the "Marketora"
official store account.

Run from the project root (after `python migrate.py`):   python seed_catalog.py
Safe to re-run: existing categories/products are skipped.
"""
import json
import random
import re
import secrets
import urllib.request
from datetime import datetime

from werkzeug.security import generate_password_hash

from app import app
from backend.database import db
from backend.models import Category, Product, ProductImage, Review, User
from backend.taxonomy import DEPARTMENTS

API_URL = "https://dummyjson.com/products?limit=0"
USD_TO_NGN = 1500  
STORE_USERNAME = "Marketora Official"
LEGACY_STORE_USERNAMES = ("markethub", "Marvodey Official")
STORE_EMAIL = "store@marketora.com"


def slugify(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def seed_categories():
    if Category.query.count() >= 500:
        print("Categories already seeded.")
        return

    used = {c.slug for c in Category.query.all()}
    created = 0
    for dept in DEPARTMENTS:
        slug = slugify(dept["name"])
        parent = Category.query.filter_by(slug=slug).first()
        if not parent:
            parent = Category(name=dept["name"], slug=slug, icon=dept["icon"], api_group=dept["groups"][0])
            db.session.add(parent)
            db.session.flush()
            used.add(slug)

        for i, sub in enumerate(dept["subs"]):
            sub_slug = slugify(sub)
            if sub_slug in used:
                sub_slug = f"{sub_slug}-{slugify(dept['name'])}"
            if sub_slug in used:
                continue
            used.add(sub_slug)
            db.session.add(Category(
                name=sub, slug=sub_slug, parent_id=parent.id, icon=dept["icon"],
                api_group=dept["groups"][i % len(dept["groups"])],
            ))
            created += 1
    db.session.commit()
    print(f"Created {created} sub-categories under {len(DEPARTMENTS)} departments.")


def get_store_user():
    legacy = User.query.filter(User.username.in_(LEGACY_STORE_USERNAMES)).first()
    if legacy and not User.query.filter_by(username=STORE_USERNAME).first():
        legacy.username, legacy.email = STORE_USERNAME, STORE_EMAIL
        db.session.commit()
    store = User.query.filter_by(username=STORE_USERNAME).first()
    if not store:
        # random password: nobody is meant to sign in as the official store
        store = User(
            username=STORE_USERNAME, email=STORE_EMAIL, role="seller",
            password_hash=generate_password_hash(secrets.token_urlsafe(24)),
        )
        db.session.add(store)
        db.session.commit()
    return store


def primary_leaves():
    """api group -> the sub-category imported products of that group are filed under."""
    mapping = {}
    for dept in DEPARTMENTS:
        parent = Category.query.filter_by(name=dept["name"], parent_id=None).first()
        kids = Category.query.filter_by(parent_id=parent.id).order_by(Category.id).all()
        for i, group in enumerate(dept["groups"]):
            mapping.setdefault(group, kids[i])
    return mapping


def title_case_tags(tags):
    return ", ".join(t.replace("-", " ").title() for t in tags)


def import_products():
    if Product.query.filter_by(seller_id=get_store_user().id).count() >= 150:
        print("API products already imported.")
        return

    print("Downloading products from DummyJSON ...")
    req = urllib.request.Request(API_URL, headers={"User-Agent": "Marketora-demo"})
    data = json.load(urllib.request.urlopen(req, timeout=60))["products"]
    store = get_store_user()
    leaves = primary_leaves()
    rng = random.Random(42)

    existing_skus = {s for (s,) in db.session.query(Product.sku).filter(Product.seller_id == store.id)}
    added = 0

    for item in data:
        sku = item.get("sku") or f"DJ-{item['id']}"
        if sku in existing_skus:
            continue

        price = round(item["price"] * USD_TO_NGN / 50) * 50          # nearest 50 naira
        discount = item.get("discountPercentage") or 0
        old_price = round(price / (1 - discount / 100) / 50) * 50 if discount >= 5 else None
        category = leaves.get(item["category"])

        dims = item.get("dimensions") or {}
        specs = [
            ("Brand", item.get("brand") or "Generic"),
            ("SKU", sku),
            ("Weight", f"{item.get('weight', '')} kg"),
            ("Dimensions (W x H x D)", f"{dims.get('width', '-')} x {dims.get('height', '-')} x {dims.get('depth', '-')} cm"),
            ("Availability", item.get("availabilityStatus", "In Stock")),
            ("Minimum order", str(item.get("minimumOrderQuantity", 1))),
        ]
        features = [t.replace("-", " ").title() for t in item.get("tags", [])]
        features += [item.get("warrantyInformation", ""), item.get("shippingInformation", "")]

        tags = []
        if discount >= 15:
            tags.append("flash_sale")
        if discount >= 8:
            tags.append("top_deal")
        if item.get("rating", 0) >= 4.5:
            tags.append("best_seller")
        if rng.random() < 0.25:
            tags.append("trending")
        if rng.random() < 0.3:
            tags.append("new_arrival")
        tags.append("official_store")

        images = item.get("images") or [item.get("thumbnail")]
        product = Product(
            name=item["title"][:160],
            description=item.get("description"),
            price=price,
            old_price=old_price,
            image_url=images[0],
            seller_id=store.id,
            category_id=category.id if category else None,
            stock=item.get("stock", 20),
            brand=item.get("brand"),
            sku=sku,
            condition="New",
            weight=item.get("weight"),
            warranty=item.get("warrantyInformation"),
            key_features="\n".join(f for f in features if f),
            specifications="\n".join(f"{k}: {v}" for k, v in specs),
            box_contents=f"1 x {item['title']}",
            return_policy=item.get("returnPolicy"),
            rating=item.get("rating", 0),
            rating_count=len(item.get("reviews", [])) or 0,
        )
        product.set_tags(tags)
        db.session.add(product)
        db.session.flush()

        for pos, url in enumerate(images):
            db.session.add(ProductImage(product_id=product.id, url=url, position=pos))

        for r in item.get("reviews", []):
            db.session.add(Review(
                product_id=product.id, author_name=r["reviewerName"], rating=r["rating"],
                comment=r["comment"],
                created_at=datetime.fromisoformat(r["date"].replace("Z", "+00:00")).replace(tzinfo=None),
            ))
        added += 1

    db.session.commit()
    print(f"Imported {added} products for the '{STORE_USERNAME}' official store.")


if __name__ == "__main__":
    with app.app_context():
        seed_categories()
        import_products()
