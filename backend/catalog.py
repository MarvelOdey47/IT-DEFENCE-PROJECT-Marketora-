"""Product listing queries shared by the home page, search, category and explore pages."""
import random

from sqlalchemy import func

from backend.database import db

from backend.models import PRODUCT_TAGS, Category, Product


def active_products():
    return Product.query.filter(Product.is_active.is_(True))


def category_ids(category):
    """The category itself plus every sub-category below it."""
    ids = [category.id]
    ids += [c.id for c in category.children]
    return ids


def category_query(category):
    """
    Active products in a category. Categories that have no products of their own
    borrow the products of other categories fed from the same product-API group,
    so no category page is ever empty.
    """
    query = active_products().filter(Product.category_id.in_(category_ids(category)))
    if query.count():
        return query

    group = category.api_group
    if category.parent_id is None:
        groups = {c.api_group for c in category.children if c.api_group}
    else:
        groups = {group} if group else set()
    if not groups:
        return query
    borrowed = [c.id for c in Category.query.filter(Category.api_group.in_(groups)).all()]
    return active_products().filter(Product.category_id.in_(borrowed))


def apply_sort(query, sort):
    if sort == "price_asc":
        return query.order_by(Product.price.asc())
    if sort == "price_desc":
        return query.order_by(Product.price.desc())
    if sort == "rating":
        return query.order_by(Product.rating.desc(), Product.id.desc())
    if sort == "newest":
        return query.order_by(Product.created_at.desc(), Product.id.desc())
    return query.order_by(Product.id.desc())


def tagged_products(tag, limit=12):
    return (
        active_products()
        .filter(Product.tags.like(f"%,{tag},%"))
        .order_by(Product.rating.desc(), Product.id.desc())
        .limit(limit)
        .all()
    )


def hero_products(count=5):
    """A random handful of discounted / top-rated products for the hero slider."""
    pool = (
        active_products()
        .filter(Product.image_url.isnot(None))
        .filter(db.or_(Product.tags.like("%,flash_sale,%"), Product.tags.like("%,top_deal,%"), Product.tags.like("%,best_seller,%")))
        .all()
    )
    random.shuffle(pool)
    return pool[:count]


def home_sections():
    """Products for each tagged homepage section (sections with nothing are skipped)."""
    sections = []
    for key, (title, icon, blurb) in PRODUCT_TAGS.items():
        if key == "official_store":
            continue
        items = tagged_products(key)
        if items:
            sections.append({"key": key, "title": title, "icon": icon, "blurb": blurb, "products": items})
    return sections


def department_strips(tree, count=4, per_strip=8):
    """A handful of department shelves for the home page ('Phones & Tablets', 'Fashion', ...)."""
    strips = []
    for dept in tree:
        category = Category.query.get(dept["id"])
        items = category_query(category).order_by(Product.rating.desc()).limit(per_strip).all()
        if len(items) >= 4:
            strips.append({"dept": dept, "products": items})
        if len(strips) == count:
            break
    return strips


def endless_page(page, seed, per_page=20):
    """
    Endless, shuffled feed. The active product ids are shuffled per 'cycle'
    (re-shuffled with a new order every time the catalogue is exhausted), so
    scrolling never runs out. Returns the page of products in feed order.
    """
    ids = [i for (i,) in active_products().with_entities(Product.id).order_by(Product.id).all()]
    if not ids:
        return []
    total = len(ids)
    orders = {}
    picked = []
    for pos in range(page * per_page, (page + 1) * per_page):
        cycle, idx = divmod(pos, total)
        if cycle not in orders:
            shuffled = ids[:]
            random.Random(f"{seed}-{cycle}").shuffle(shuffled)
            orders[cycle] = shuffled
        picked.append(orders[cycle][idx])

    by_id = {p.id: p for p in Product.query.filter(Product.id.in_(set(picked))).all()}
    return [by_id[i] for i in picked if i in by_id]


def brands_for(query, limit=12):
    rows = (
        query.with_entities(Product.brand, func.count(Product.id))
        .filter(Product.brand.isnot(None))
        .group_by(Product.brand)
        .order_by(func.count(Product.id).desc())
        .limit(limit)
        .all()
    )
    return [b for b, _ in rows]
