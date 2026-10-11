from flask_wtf import FlaskForm
from wtforms import (
    StringField, PasswordField, SubmitField, DecimalField, TextAreaField, RadioField,
    SelectField, IntegerField,
)
from wtforms.validators import (
    DataRequired, Email, Length, EqualTo, ValidationError, NumberRange, Optional, InputRequired,
)
from backend.models import User


class RegistrationForm(FlaskForm):

    # Admin accounts cannot be created publicly (see seed_admin.py)
    role = RadioField(
        "Register as",
        choices=[("customer", "Customer"), ("seller", "Seller")],
        default="customer",
        validators=[DataRequired()],
    )

    username = StringField(
        "Username",
        validators=[DataRequired(), Length(min=3, max=25)],
    )

    email = StringField(
        "Email",
        validators=[DataRequired(), Email()],
    )

    password = PasswordField(
        "Password",
        validators=[DataRequired(), Length(min=6)],
    )

    confirm_password = PasswordField(
        "Confirm Password",
        validators=[DataRequired(), EqualTo("password")],
    )

    submit = SubmitField("Register")

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError("Username already taken.")

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError("Email already registered.")


class LoginForm(FlaskForm):

    role = RadioField(
        "Sign in as",
        choices=[("customer", "Customer"), ("seller", "Seller")],
        default="customer",
        validators=[DataRequired()],
    )

    username = StringField(
        "Username",
        validators=[DataRequired()],
    )

    password = PasswordField(
        "Password",
        validators=[DataRequired()],
    )

    submit = SubmitField("Login")


class AdminLoginForm(FlaskForm):

    username = StringField("Admin username", validators=[DataRequired()])

    password = PasswordField("Password", validators=[DataRequired()])

    submit = SubmitField("Sign in")


class ProductForm(FlaskForm):
    """Product listing form, modelled on the fields marketplace sellers fill in."""

    name = StringField(
        "Product name",
        validators=[DataRequired(), Length(min=3, max=160)],
        description="Brand + product type + key feature, e.g. 'Samsung Galaxy A15 6.5\" 128GB'.",
    )

    category_id = SelectField("Category", coerce=int, validators=[DataRequired(message="Choose a category.")])

    brand = StringField("Brand", validators=[Optional(), Length(max=80)])

    condition = SelectField(
        "Condition",
        choices=[("New", "New"), ("Refurbished", "Refurbished"), ("Used", "Used - like new")],
        default="New",
    )

    price = DecimalField(
        "Selling price (₦)",
        validators=[DataRequired(), NumberRange(min=1)],
        places=2,
    )

    old_price = DecimalField(
        "Original price (₦)",
        validators=[Optional(), NumberRange(min=1)],
        places=2,
        description="Optional. If higher than the selling price it is shown struck-through with a discount badge.",
    )

    stock = IntegerField(
        "Quantity in stock",
        validators=[InputRequired(), NumberRange(min=0, max=100000)],
        default=1,
    )

    sku = StringField("Seller SKU", validators=[Optional(), Length(max=60)])

    color = StringField("Colour", validators=[Optional(), Length(max=60)])

    size = StringField("Size / Capacity", validators=[Optional(), Length(max=60)])

    weight = DecimalField("Weight (kg)", validators=[Optional(), NumberRange(min=0)], places=2)

    warranty = StringField(
        "Warranty", validators=[Optional(), Length(max=120)],
        description="e.g. '12 months manufacturer warranty'.",
    )

    return_policy = StringField(
        "Return policy", validators=[Optional(), Length(max=160)],
        default="7 days return policy",
    )

    key_features = TextAreaField(
        "Key features",
        validators=[Optional(), Length(max=2000)],
        description="One feature per line. Shown as bullet points next to the price.",
    )

    description = TextAreaField(
        "Product description",
        validators=[Optional(), Length(max=5000)],
    )

    specifications = TextAreaField(
        "Specifications",
        validators=[Optional(), Length(max=3000)],
        description="One per line as 'Name: value', e.g. 'Screen size: 6.5 inches'.",
    )

    box_contents = TextAreaField(
        "What's in the box", validators=[Optional(), Length(max=1000)],
    )

    image_urls = TextAreaField(
        "Image links",
        validators=[Optional(), Length(max=4000)],
        description="Paste one image link per line. You can also upload files below.",
    )

    submit = SubmitField("Save product")


class CheckoutForm(FlaskForm):

    full_name = StringField("Full name", validators=[DataRequired(), Length(max=120)])

    phone = StringField("Phone number", validators=[DataRequired(), Length(min=7, max=40)])

    address = StringField("Delivery address", validators=[DataRequired(), Length(max=300)])

    city = StringField("City / State", validators=[DataRequired(), Length(max=80)])

    submit = SubmitField("Place order")


class ReviewForm(FlaskForm):

    rating = SelectField(
        "Your rating",
        choices=[("5", "5 - Excellent"), ("4", "4 - Good"), ("3", "3 - Average"), ("2", "2 - Poor"), ("1", "1 - Terrible")],
        default="5",
    )

    comment = TextAreaField("Your review", validators=[Optional(), Length(max=1000)])

    submit = SubmitField("Submit review")


class CategoryForm(FlaskForm):

    name = StringField("Category name", validators=[DataRequired(), Length(max=120)])

    parent_id = SelectField("Parent department", coerce=int)

    submit = SubmitField("Save category")
