from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from backend.database import db
from backend.models import User
from backend.forms import RegistrationForm, LoginForm
from backend.portals import current_portal
from backend.utils import delete_avatar_file, save_avatar
from werkzeug.security import generate_password_hash


auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    wanted = request.args.get("role")
    if current_user.is_authenticated:
        if current_user.role == "seller":
            return redirect(url_for("seller.dashboard"))
        if current_user.role == "admin":
            return redirect(url_for("admin.dashboard"))
        if wanted == "seller":
            flash("You are signed in as a customer. Log out to register a seller account.", "info")
        return redirect(url_for("index"))

    form = RegistrationForm()
    if request.method == "GET":
        if wanted in ("customer", "seller"):
            form.role.data = wanted
        elif current_portal() == "seller":
            form.role.data = "seller"

    if form.validate_on_submit():
        password_hash = generate_password_hash(form.password.data)
        user = User(
            username=form.username.data,
            email=form.email.data,
            password_hash=password_hash,
            role=form.role.data,
        )
        db.session.add(user)
        db.session.commit()
        flash("Registration successful! You can now log in.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/register.html", form=form)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    wanted = request.args.get("role")
    if current_user.is_authenticated:
        if wanted == "seller" and current_user.role == "seller":
            return redirect(url_for("seller.dashboard"))
        if wanted == "seller" and current_user.role == "customer":
            flash("You are signed in as a customer. Log out to sign in as a seller.", "info")
        return redirect(url_for("index"))

    form = LoginForm()
    if request.method == "GET":
        if wanted in ("customer", "seller"):
            form.role.data = wanted
        elif current_portal() == "seller":
            form.role.data = "seller"

    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.role != "admin" and user.check_password(form.password.data):
            if user.suspended:
                flash("This account has been suspended. Please contact support.", "danger")
            elif user.role != form.role.data:
                flash(f"This account is not a {form.role.data} account. Pick the right tab.", "danger")
            else:
                login_user(user)
                next_page = request.args.get("next")
                if next_page and next_page.startswith("/") and not next_page.startswith("//"):
                    return redirect(next_page)
                if user.role == "admin":
                    return redirect(url_for("admin.dashboard"))
                if user.role == "seller":
                    return redirect(url_for("seller.dashboard"))
                return redirect(url_for("index"))
        else:
            flash("Invalid username or password.", "danger")

    return render_template("auth/login.html", form=form)


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("index"))


@auth_bp.route("/account", methods=["GET", "POST"])
@login_required
def account():
    """Profile page for every role: view details, upload or remove a profile picture."""
    if request.method == "POST":
        if request.form.get("action") == "remove":
            delete_avatar_file(current_user.avatar_url)
            current_user.avatar_url = None
            db.session.commit()
            flash("Profile picture removed.", "info")
        else:
            url, error = save_avatar(request.files.get("avatar"))
            if error:
                flash(error, "danger")
            else:
                delete_avatar_file(current_user.avatar_url)
                current_user.avatar_url = url
                db.session.commit()
                flash("Profile picture updated.", "success")
        return redirect(url_for("auth.account"))
    return render_template("auth/account.html")
