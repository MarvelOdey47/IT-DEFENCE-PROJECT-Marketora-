# MarketHub — Agent Progress File

## Project
MarketHub is a beginner-friendly Flask mini online marketplace being built as a complete CRUD project in about 5 days.

## Core architecture
```text
Browser
   ↓
Flask
   ↓
SQLAlchemy
   ↓
Supabase PostgreSQL
```

The project uses Supabase PostgreSQL with the **Direct Connection** option.

## Project structure
```text
MARKET-HUB/
├── backend/
│   ├── __init__.py
│   ├── config.py
│   ├── database.py
│   ├── forms.py
│   ├── models.py
│   ├── auth.py
│   ├── products.py
│   ├── cart.py
│   ├── orders.py
│   ├── seller.py
│   └── admin.py
├── templates/
│   ├── admin/
│   ├── auth/
│   ├── cart/
│   ├── orders/
│   ├── products/
│   └── seller/
├── static/
│   ├── css/
│   ├── js/
│   └── images/
├── env/                 # Python virtual environment
├── .env                 # Supabase credentials; never commit/share
├── .gitignore
├── app.py
├── requirements.txt
└── Agent.md
```

## Architecture rule
`app.py` should only start the Flask application. Business/application logic belongs in `backend/`.

## Completed steps
### Steps 1–7
- Chosen project: MarketHub — Mini Online Marketplace.
- Decided on Flask + SQLAlchemy + Supabase PostgreSQL.
- Chosen Supabase **Direct Connection**, not Session Pooler or Transaction Pooler.
- Created/organized the backend, templates, and static structure.
- Supabase project created and Direct Connection string obtained.
- Database credentials are stored in `.env`.

### Step 8
Installed the main dependencies:
```powershell
pip install flask flask-sqlalchemy flask-login flask-wtf python-dotenv psycopg
pip freeze > requirements.txt
```

### Steps 9–15
- Configured:
  - `.env`
  - `.gitignore`
  - `backend/config.py`
  - `backend/database.py`
  - `backend/__init__.py`
  - `app.py`
- Installed main dependencies:
  ```powershell
  pip install flask flask-sqlalchemy flask-login flask-wtf python-dotenv psycopg
  pip freeze > requirements.txt
  ```
- Installed `psycopg[binary]` successfully (version 3.3.6).
- Flask starts correctly.
- Attempted `/test-db` route; Supabase hostname does not resolve (stale project reference).

Expected `.env` pattern:
```env
SECRET_KEY=market-hub-super-secret-key
DATABASE_URL=postgresql+psycopg://YOUR_SUPABASE_CONNECTION_STRING
```

### Step 15
- Installed `psycopg[binary]` successfully (version 3.3.6).
- Flask starts correctly.
- Attempted `/test-db` route:
  ```text
  Database connection failed: (psycopg.OperationalError) failed to resolve host 'db.rpvlsvzcbbcnbxllkxap.supabase.co': [Errno 11001] getaddrinfo failed
  ```
- `nslookup` returned no results for the Supabase host.

### Current issue at Step 15
Supabase hostname `db.rpvlsvzcbbcnbxllkxap.supabase.co` does not resolve. The Supabase project may have been deleted or the project reference changed.

### Diagnosis
The `DATABASE_URL` in `.env` contains a stale Supabase project reference. A valid, active Supabase project and its Direct Connection string are required.

## Current issue at Step 15
- Updated `.env` with correct Supabase Direct Connection URL.
- Flask restarted.
- `/test-db` still fails with:
  ```text
  failed to resolve host 'db.rpvlsvzcbbcnbxllkxap.supabase.co': [Errno 11001] getaddrinfo failed
  ```

### Diagnosis
- Internet works: `ping 8.8.8.8` succeeds.
- Python's `socket.getaddrinfo` cannot resolve the hostname.
- `nslookup` times out for all external hosts.
- `Resolve-DnsName` (PowerShell) CAN resolve some hosts but returns **no A record** for `db.rpvlsvzcbbcnbxllkxap.supabase.co`, only an HINFO/RFC8482 response.
- `Resolve-DnsName` previously returned an AAAA record (`2a05:d018:1701:d202:a072:33ac:697:6078`), but this machine has no global IPv6 connectivity (only link-local), so IPv6 is unusable.
- Querying both Google DNS (`8.8.8.8`) and Cloudflare DNS (`1.1.1.1`) returns **no A record** for this host.

**Root cause:** `db.rpvlsvzcbbcnbxllkxap.supabase.co` has **no public A record**. This strongly suggests the Supabase project may have been deleted, suspended, or the Direct Connection hostname is no longer published.

## Verified facts
- Supabase domain `supabase.co` exists (SOA record found).
- Specific host `db.rpvlsvzcbbcnbxllkxap.supabase.co` has **no A record** in public DNS.
- Python, nslookup, and Test-NetConnection all fail name resolution.
- Only `Resolve-DnsName` found an AAAA record (unusable without IPv6 connectivity).

### Current issue at Step 15
- Updated `.env` with new Supabase Direct Connection URL.
- Flask restarted.
- `/test-db` fails due to DNS resolution issues on this network.
- Switched to Supabase **Session Pooler** as fallback.
- Updated `.env` with Session Pooler URL.
- Restarted Flask and retested `http://127.0.0.1:5000/test-db`.
- **Result: `Database connection successful!`**

### Step 15 — Resolved
- Database connection works via Supabase Session Pooler.
- `.env` now contains the Session Pooler URL.
- `backend/test.py` temporary test route removed.
- `User` model created in `backend/models.py`.
- `db.create_all()` executed successfully; `users` table created in Supabase.

### Step 16 — Build registration
- Created `RegistrationForm` in `backend/forms.py`.
- Created registration route in `backend/auth.py` using `auth_bp` Blueprint.
- Created registration template `templates/auth/register.html`.
- Created base template `templates/base.html` with nav and flash messages.
- Created index template `templates/index.html`.
- Updated `backend/__init__.py` to register blueprint and initialize Flask-Login.
- Installed `email-validator` for WTForms email validation.
- Disabled CSRF temporarily for development (`WTF_CSRF_ENABLED = False`).
- Registration tested successfully: user created and redirected to login.

### Step 17 — Build login
- Created `LoginForm` in `backend/forms.py`.
- Created login route in `backend/auth.py`.
- Created login template `templates/auth/login.html`.
- Login tested successfully: authenticates user and redirects to home.

### Step 18 — Build logout
- Created logout route in `backend/auth.py` with `@login_required`.
- Logout tested successfully: logs out user and redirects to home.

### Step 19 — Build protected dashboard
- Created dashboard route in `backend/__init__.py` with `@login_required`.
- Created dashboard template `templates/dashboard.html`.
- Dashboard tested successfully: accessible only when logged in.

### Step 21 — Cart + Checkout + Orders
- Created `Cart`, `Order`, and `OrderItem` models in `backend/models.py`.
- Created `cart_bp` Blueprint in `backend/cart.py` with routes: view, add, remove.
- Created `orders_bp` Blueprint in `backend/orders.py` with routes: checkout, list.
- Created cart and orders templates.
- Registered blueprints in `backend/__init__.py`.
- Ran `db.create_all()` to create `carts`, `orders`, and `order_items` tables.
- Tested add to cart, checkout, and order listing successfully.

### Step 22 — Seller Dashboard
- Created `seller_bp` Blueprint in `backend/seller.py`.
- Added seller dashboard route with `@login_required` and seller check.
- Created seller dashboard template `templates/seller/dashboard.html`.
- Registered `seller_bp` in `backend/__init__.py`.
- Updated base template to show Seller Dashboard link for sellers.
- Tested seller dashboard successfully.

### Step 23 — Admin Dashboard
- Created `admin_bp` Blueprint in `backend/admin.py`.
- Added admin dashboard route with `@login_required` and admin check.
- Created admin dashboard template `templates/admin/dashboard.html`.
- Registered `admin_bp` in `backend/__init__.py`.
- Updated base template to show Admin Dashboard link for admins.
- Tested admin dashboard successfully.

### Completed steps summary
- Step 1: Removed temporary test route/file — done.
- Step 2: Created `User` model — done.
- Step 3: Ran `db.create_all()` — done.
- Step 4: Built registration — done.
- Step 5: Built login — done.
- Step 6: Built logout — done.
- Step 7: Built protected dashboard — done.
- Step 8: Built Product CRUD — done.
- Step 9: Built Cart + Checkout + Orders — done.
- Step 10: Built Seller Dashboard — done.
- Step 11: Built Admin Dashboard — done.

### Step 24 — Roles, role-based sign-in, home page redesign (2026-10-07)
Audit against the project outline showed the earlier "nearly complete" claim was wrong: the app was a minimal CRUD, not the full outline. Work done:
- **Roles:** `User.is_admin` / `User.is_seller` booleans replaced by a single `role` column (`customer` | `seller` | `admin`). `is_admin` / `is_seller` still exist as read-only properties on `User` so older code keeps working.
- **Migration + admin seed:** `seed_admin.py` (project root, repeatable) adds `users.role`, backfills from the old booleans, drops the old columns, and creates the admin. Already run against Supabase.
  - Admin login → username `admin`, password `Admin@12345`, email `admin@markethub.com` (override with env vars `ADMIN_USERNAME`, `ADMIN_EMAIL`, `ADMIN_PASSWORD` before running; change the password after first sign-in).
- **Register:** Customer / Seller tabs (`RegistrationForm.role`). Admin cannot be registered publicly.
- **Login:** Customer / Seller / Admin tabs (`LoginForm.role`). The account's role must match the tab. After login: admin → admin dashboard, seller → seller dashboard, customer → home. `next` redirect only accepts local paths.
- **Product permissions:** `/products/create` is seller/admin only. Product detail page: logged-out/customer sees Add to Cart (logged-out sees "Sign in to add to cart"); owning seller and admin see Edit/Delete (with confirm). Edit/delete routes already enforced owner-or-admin on the server.
- **UI:** `base.html` rebuilt as a top bar (logo, search, Sign In/Register or role links, Cart, theme icon at far right; sun/moon SVG replaces "Theme" text). `index.html` rebuilt to match the ApexMarket-style screenshot (category sidebar, "New Arrivals: Fashion" hero, Popular Categories, Flash Sales cards from the latest 10 DB products). `style.css` rewritten (orange accent, light + dark). New `templates/partials/product_card.html`. `products/list.html` is now a card grid with `?q=` name search. Prices on touched pages show ₦.
- Home categories are currently a static list (no Category table yet); they link to a name search.

### Step 25 — Big marketplace upgrade (2026-10-08) — DONE, tested
User asked for a Jumia-like mini marketplace. Everything below is implemented and verified by an end-to-end test (80+ checks with CSRF on, run through Flask's test client; test data cleaned up). Not yet eyeballed in a real browser — user should check visuals.

**Access rules**
- Seller sees/manages ONLY own products (`/seller/products`, edit/delete owner-checked server side); admin sees all (`/admin/products`).
- Seller/admin cannot add to cart, check out or order (`customer_required` on cart/orders routes; cart link hidden). They can browse the home page and product pages; seller tracks own orders at `/seller/orders` and updates status (forward-only flow; seller can also reject pending/confirmed -> cancelled which restocks). Admin may set any status.
- Customer: product page shows Add to cart / Buy now; logged-out sees "Sign in to buy".
- Suspended users are logged out on next request and cannot sign in.

**Data / API**
- Free DummyJSON API is the "MarketHub official store" catalogue (`seed_catalog.py` -> user `markethub`, 194 products, tagged `official_store`). Jumia is NOT scraped (ToS/brittle). USD->NGN x1500.
- 25 departments x 20 = 500 sub-categories (`backend/taxonomy.py`). Imported products sit in the primary sub-category per API group; every other category page borrows products from the same API group (`catalog.category_query`) so no category page is empty.
- Tags (`PRODUCT_TAGS` in models): flash_sale, top_deal, new_arrival, best_seller, trending, official_store (admin-only). Sellers pick tags in the product form; flash_sale requires old_price > price. Each tag becomes a home-page section (`catalog.home_sections`); flash sale has a countdown to midnight. `/products?tag=<tag>` lists a tag.
- Run order for a fresh DB: `python migrate.py`, `python seed_admin.py`, `python seed_catalog.py`.

**Pages**
- Home: sticky category sidebar, hero slider (flash-sale products), trust strip, Popular Categories carousel (all 500, auto-scrolls; "Browse all" opens the drawer), flash sale, banners, tag sections, department shelves, official store, discover-more-stores links, footer. Hamburger before the logo opens a searchable all-categories drawer.
- `/products` + `/category/<slug>`: filters (category, price, brand), sort, pagination. `/explore`: endless shuffled feed (auto-loads 3 pages, then Load more).
- Product detail: Jumia-style gallery carousel (auto-advance 4s, pause/play, thumbs, arrows), price/discount, stock, qty stepper, key features, delivery/returns, specs, verified ratings; reviews only from customers with a delivered order.
- Product form: sections for basic info (category, brand, condition, SKU, colour, size), pricing & stock (old price, weight, warranty, return policy), details (features, description, specs, box contents), images (paste links AND upload multiple files; remove existing), promotion tags.
- Cart (qty +/-, stock clamp), checkout form (name/phone/address/city), order detail with tracker + cancel, customer dashboard stats.
- Seller dashboard (products, orders, revenue, low stock), seller products/orders; admin dashboard (stats + bars), users (suspend, role), products, categories (add/rename/delete, 525 rows searchable), orders.
- Archive rule: deleting a product that has past orders hides it (`is_active=False`) instead of erasing it.
- CSRF is ON (all POST forms carry a token). Emojis removed everywhere; Font Awesome icons via CDN. Theme toggle is a sun/moon icon at far right. README written. Empty stub templates/CSS/JS, `cookies.txt`, `query` deleted.

**Known limits / ideas**
- Order status is per order, not per seller item (if two sellers share an order either can advance it).
- Delivery fee is not modelled; payment is simulated (pay on delivery).
- Category dropdown in product form lists all 500 leaves (grouped by department) with no search box.
- Hero/Flash visuals depend on the DummyJSON image CDN (needs internet).

### Step 26 — Rebrand, auth/admin changes, news, home-page fixes (2026-10-09) — DONE, tested
- **Brand renamed MarketHub -> Marvodey** (coined from Marvel + Odey; web-searched, no marketplace of that name found - not a trademark check). Single source: `BRAND_NAME` / `ORDER_PREFIX` ("MV", order refs like MV1001) in `backend/config.py`; templates use `{{ BRAND }}`. Official-store account renamed to `Marvodey Official`; admin email now `admin@marvodey.com`. Code identifiers/folder names still say MARKET-HUB (not displayed).
- **Admin sign-in is hidden**: no Admin tab on /login or /register. Admin signs in only at **http://127.0.0.1:5000/admin** (now the admin portal; the form lives at `/admin/console/login`). Admin credentials: username `admin`, password `Admin@12345` (from `seed_admin.py`; change after first login). Admin accounts can no longer use the public login. Anonymous hits on admin pages redirect to /admin.
- **Auth pages are standalone** (`templates/auth_base.html`): no navbar, drawer, sidebar or footer - just logo, back-to-store link and theme icon. Applies to /login, /register, /admin.
- **Seller CTAs fixed**: "Sell on Marvodey" tile, "Become a seller / Start selling" banner and footer links go to `/register?role=seller` / `/login?role=seller` (tab preselected; already-signed-in users get a message/redirect).
- **Hero**: 30 s per slide; products are random each page load (`catalog.hero_products`) and the JS fetches a fresh set from `/hero/feed` every 3 min. **Product gallery carousel**: 30 s per image.
- **Flash Sales header** now matches the other shelves (title + "Ends in HH:MM:SS" slots in the header row; red top border only).
- **Dark mode scrollbars** fixed (`color-scheme: dark` + themed `--scroll-thumb`).
- **Market news section** on the home page, before the footer (`backend/news.py`, `/news/feed`, tabs: E-commerce, Stock market (NGX), Digital marketing, Fintech & payments). Real headlines from Bing News RSS (Nigeria-focused queries), cached 30 min, linking to the original publishers. Caveat: RSS feeds carry usage terms - fine for a demo/school project, review before commercial use.
- Cart/order access: only logged-in **customers** can add to cart / order (anonymous -> sign-in; seller/admin blocked).
- Test suite (scratchpad e2e) re-run: all checks pass.

### Step 27 — Rename to Marketora, multi-login portals, avatars, UI polish (2026-10-10) — DONE, tested
- **Brand renamed again: Marvodey -> Marketora** (web search found no marketplace with that name; Bazaario is a registered trademark and Tradora a company, so both were rejected - not a trademark check). Order refs now `MR1001`. Official-store account `Marketora Official`, admin email `admin@marketora.com`. Change in one place: `BRAND_NAME` / `ORDER_PREFIX` in `backend/config.py`.
- **Several logins at once in one browser** (`backend/portals.py`): the site is served under three URL prefixes, each with its own session cookie - `/` (customer, cookie `session`), `/seller/` (`session_seller`), `/admin/` (`session_admin`). `PortalMiddleware` moves the prefix into SCRIPT_NAME so every `url_for` link stays in the portal; `PortalSessionInterface` picks the cookie name; `portal_url(portal, endpoint)` links across portals (used for "Sell"/"Become a seller"). A tag beside the logo shows the portal. JS reads `data-root` on `<body>` for fetch URLs. Uploaded image URLs are stored root-relative (`/static/...`) so they work in every portal.
- **Routes renamed** to avoid clashing with portal prefixes: seller area is `/centre`, `/centre/products`, `/centre/orders`; admin area is `/console/...` (admin login `/console/login`; visiting `/admin` redirects there or to the dashboard). So in the browser: seller dashboard = `/seller/centre`, admin dashboard = `/admin/console/dashboard`.
- **Profile pictures for all roles**: `User.avatar_url` (migration run), `/account` page (upload/remove, png/jpg/webp/gif, 2 MB), shown in the navbar and dashboard sidebar; default person icon when none. Files in `static/uploads/avatars/`.
- **News images**: shimmer placeholder while loading, fade-in, one retry, icon fallback; product thumbnails also show a shimmer until loaded.
- **Footer redesigned** to a compact single band (brand + 4 short link columns + inline subscribe + slim bottom bar).
- **Dark-mode accent** changed to soft gold `#e9b44c` (hover `#f3c670`); light mode keeps the Jumia orange `#f68b1e`. Edit the `--accent*` variables in the `[data-theme="dark"]` block of `static/css/style.css` to tweak.
- Tests: original suite (updated for renamed routes) plus a new multi-login/avatar suite pass.

## Remaining ideas (vs. outline)
1. Visual QA in a browser; tweak spacing/colours.
2. Per-item order status for multi-seller orders; delivery fees; wishlist; sales chart.
3. Product-form category search box; seller image reordering.
4. Hosting/deploy notes.

## Immediate next action
Ask the user to run `python app.py`, review the UI in the browser (home, product page, seller/admin dashboards, dark mode) and report anything to adjust.

## Important implementation details
- Keep using Psycopg 3, not Psycopg 2.
- Keep the SQLAlchemy URI using:
```text
postgresql+psycopg://
```
- Do not expose or paste the real Supabase database password into chat.
- Do not switch to XAMPP.
- Supabase Direct Connection is unusable on this network; using Session Pooler (`aws-0-eu-west-1.pooler.supabase.com:6543`) instead.
- Do not over-engineer the project; the user is learning Flask and wants understandable code.
- Test each stage before moving forward.

## Planned next stages
After the database connection succeeds:
1. Remove the temporary database test route/file.
2. Create the `User` model.
3. Run `db.create_all()` and verify the `users` table in Supabase.
4. Build registration.
5. Build login.
6. Build logout.
7. Build protected dashboard.
8. Then move to Product CRUD.
9. Then Cart + Checkout + Orders.
10. Then Seller Dashboard.
11. Then Admin Dashboard.
12. Finish with UI polish, JavaScript, images, testing, and README.

## Marketplace functionality target
Customer:
- Register/login/logout
- Browse products
- Search/filter
- Product details
- Add to cart
- Checkout
- View orders

Seller:
- Seller dashboard
- Create product
- Read/list products
- Edit product
- Delete product
- View/manage seller orders

Admin:
- Dashboard/statistics
- Manage users
- Manage products
- Manage categories
- Manage orders

## UI direction
Customer-facing pages should be clean, light(also implement dark-mode), modern, and marketplace-focused, inspired by major e-commerce layouts without copying them exactly.

Suggested homepage:
```text
MarketHub | Search products | Sign In | Cart

Categories       Hero / New Arrivals
                 Shop Now

Popular Categories

Flash Sales / Product Cards
```

Seller/admin dashboards can use a darker professional dashboard style.

## Continuation rule
This file is the project's handoff/context document. Update it after every meaningful set of steps or every user prompt that changes project progress, including errors, fixes, completed files, and the next action.
