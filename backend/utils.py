import os
import time
import uuid
from functools import wraps

from flask import current_app, flash, redirect, url_for
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename

from backend.models import Category

ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "gif"}
MAX_IMAGE_BYTES = 5 * 1024 * 1024


def role_required(*roles):
    """Login + one of the given roles. Others get a flash message and are sent home."""
    def decorator(view):
        @wraps(view)
        @login_required
        def wrapped(*args, **kwargs):
            if current_user.role not in roles:
                flash("You do not have access to that page.", "danger")
                return redirect(url_for("index"))
            return view(*args, **kwargs)
        return wrapped
    return decorator


customer_required = role_required("customer")
seller_required = role_required("seller")


def admin_required(view):
    """Admin only. Anyone else is sent to the (unlisted) admin sign-in page or home."""
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for("admin.login"))
        if current_user.role != "admin":
            flash("You do not have access to that page.", "danger")
            return redirect(url_for("index"))
        return view(*args, **kwargs)
    return wrapped


# ---------- image uploads ----------
def save_uploaded_images(files):
    """Save uploaded image files; returns (urls, errors)."""
    urls, errors = [], []
    folder = os.path.join(current_app.static_folder, "uploads", "products")
    os.makedirs(folder, exist_ok=True)

    for f in files:
        if not f or not f.filename:
            continue
        ext = secure_filename(f.filename).rsplit(".", 1)[-1].lower() if "." in f.filename else ""
        if ext not in ALLOWED_IMAGE_EXTENSIONS:
            errors.append(f"'{f.filename}' is not a supported image (png, jpg, webp, gif).")
            continue
        f.seek(0, os.SEEK_END)
        size = f.tell()
        f.seek(0)
        if size > MAX_IMAGE_BYTES:
            errors.append(f"'{f.filename}' is larger than 5 MB.")
            continue
        name = f"{uuid.uuid4().hex}.{ext}"
        f.save(os.path.join(folder, name))
        urls.append(f"/static/uploads/products/{name}")
    return urls, errors


def parse_image_urls(text):
    urls, errors = [], []
    for line in (text or "").replace(",", "\n").splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith(("http://", "https://")) and len(line) <= 500:
            urls.append(line)
        else:
            errors.append(f"Invalid image link: {line[:60]}")
    return urls, errors


# ---------- category tree (cached; 525 rows would otherwise load on every page) ----------
_tree_cache = {"at": 0, "data": None}


def get_category_tree():
    """[{id, name, slug, icon, children: [{id, name, slug}]}] for departments."""
    if _tree_cache["data"] is None or time.time() - _tree_cache["at"] > 300:
        rows = Category.query.order_by(Category.id).all()
        kids = {}
        for c in rows:
            if c.parent_id:
                kids.setdefault(c.parent_id, []).append({"id": c.id, "name": c.name, "slug": c.slug})
        _tree_cache["data"] = [
            {"id": c.id, "name": c.name, "slug": c.slug, "icon": c.icon, "children": kids.get(c.id, [])}
            for c in rows if c.parent_id is None
        ]
        _tree_cache["at"] = time.time()
    return _tree_cache["data"]


def clear_category_cache():
    _tree_cache["data"] = None


# ---------- profile pictures ----------
AVATAR_DIR = os.path.join("uploads", "avatars")
MAX_AVATAR_BYTES = 2 * 1024 * 1024


def save_avatar(file):
    """Save an uploaded profile picture. Returns (url, error)."""
    if not file or not file.filename:
        return None, "Choose an image first."
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        return None, "Use a png, jpg, webp or gif image."
    file.seek(0, os.SEEK_END)
    size = file.tell()
    file.seek(0)
    if size > MAX_AVATAR_BYTES:
        return None, "Profile pictures must be under 2 MB."
    folder = os.path.join(current_app.static_folder, AVATAR_DIR)
    os.makedirs(folder, exist_ok=True)
    name = f"{uuid.uuid4().hex}.{ext}"
    file.save(os.path.join(folder, name))
    return f"/static/uploads/avatars/{name}", None


def delete_avatar_file(url):
    """Remove a previously uploaded avatar file (ignores external links)."""
    prefix = "/static/uploads/avatars/"
    if url and url.startswith(prefix):
        path = os.path.join(current_app.static_folder, AVATAR_DIR, os.path.basename(url))
        if os.path.exists(path):
            os.remove(path)
