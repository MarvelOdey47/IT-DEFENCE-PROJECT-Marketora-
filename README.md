# Marketora

Marketora is a multi-vendor marketplace built with Flask, in the style of Jumia: customers browse and buy, sellers list and fulfil, and an admin oversees the platform.

## Tech stack

- Flask, Flask-SQLAlchemy, Flask-Login, Flask-WTF (CSRF enabled)
- Supabase PostgreSQL (Session Pooler) via Psycopg 3
- HTML, CSS (light and dark theme), vanilla JavaScript, Font Awesome icons
- Demo catalogue from the free [DummyJSON](https://dummyjson.com) API

## Roles

| Role | Can do |
|------|--------|
| Customer | Browse, search, filter, add to cart, checkout, track and cancel orders, review delivered products |
| Seller | Create/edit/delete **own** products (links or uploads, many images), tag products (flash sale, top deal, ...), see and update orders for own products, revenue stats. Cannot add to cart or order |
| Admin | Signs in only through the hidden `/admin` portal (no tab on the public pages). Everything: all users (suspend, change role), all products, categories (500+), all orders, platform stats |

## Setup

```powershell
python -m venv env
.\env\Scripts\activate
pip install -r requirements.txt
```

Create `.env`:

```env
SECRET_KEY=change-me
DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST:PORT/postgres
```

Then, once:

```powershell
python migrate.py        # creates/updates tables
python seed_admin.py     # creates the admin account
python seed_catalog.py   # 500 categories + ~190 demo products (official store)
python app.py            # http://127.0.0.1:5000
```

Admin sign-in: http://127.0.0.1:5000/admin - username `admin`, password `Admin@12345` (change it, or set `ADMIN_USERNAME`, `ADMIN_EMAIL`, `ADMIN_PASSWORD` before running `seed_admin.py`).

## Features

- Role-based registration and sign-in (Customer / Seller tabs; admin via /admin only)
- Home page with hero slider, category sidebar, hamburger category drawer, 500-category carousel, flash-sale countdown and tag-driven sections
- Search, category pages, price/brand filters, sorting, pagination
- Endless "Explore" feed (re-shuffles when the catalogue is exhausted)
- Jumia-style product page: auto-advancing image carousel, discount, stock, quantity, key features, specifications, verified ratings
- Cart with quantity +/- and stock checks; checkout form; order tracking; cancel (restocks)
- Seller centre, admin console, customer dashboard

## Project layout

```
app.py                Starts the app
migrate.py            Idempotent schema upgrade
seed_admin.py         Role migration + admin account
seed_catalog.py       Categories + API product import
backend/              Blueprints, models, forms, helpers
templates/ static/    Jinja templates, CSS, JS
```

## Notes

- Prices from the demo API are converted USD to NGN at 1 : 1500.
- Payment is simulated (pay on delivery).
- Product images uploaded from a computer are stored in `static/uploads/products/`.

## Three logins in one browser (portals)

A browser shares cookies between tabs, so normally only one account can be signed in. Marketora gives each role its own
session cookie by serving the site under three URL prefixes:

| Tab | URL | Cookie |
|-----|-----|--------|
| Customer | http://127.0.0.1:5000/ | `session` |
| Seller | http://127.0.0.1:5000/seller/ | `session_seller` |
| Admin | http://127.0.0.1:5000/admin | `session_admin` |

Open one tab per URL and sign in separately (`/login`, `/seller/login`, `/admin`). Logging out of one tab does not affect the others.
A small tag next to the logo shows which portal a tab belongs to.

## Profile pictures

Every role (customer, seller, admin) can upload or remove a profile picture on the Profile page (`/account`, linked from the
navbar avatar and the dashboard sidebar). Without one, a default person icon is shown.
