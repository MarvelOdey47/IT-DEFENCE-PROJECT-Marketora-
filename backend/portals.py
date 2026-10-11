"""
Independent sign-in "portals", so one browser can hold several logins at once.

A browser sends the same cookies from every tab, so a normal Flask session means
one login per browser. Here the site can be opened under three URL prefixes and
each gets its own session cookie:

    http://127.0.0.1:5000/          -> customer portal   (cookie "session")
    http://127.0.0.1:5000/seller/   -> seller portal     (cookie "session_seller")
    http://127.0.0.1:5000/admin/    -> admin portal      (cookie "session_admin")

The middleware strips the prefix before Flask routes the request and moves it
into SCRIPT_NAME, so every url_for() link inside a portal automatically stays
inside that portal.
"""
from flask import request, url_for
from flask.sessions import SecureCookieSessionInterface

PORTAL_PREFIXES = {"seller": "/seller", "admin": "/admin"}
ENV_KEY = "marketora.portal"


class PortalMiddleware:
    def __init__(self, wsgi_app):
        self.wsgi_app = wsgi_app

    def __call__(self, environ, start_response):
        path = environ.get("PATH_INFO", "")
        environ[ENV_KEY] = "customer"
        for name, prefix in PORTAL_PREFIXES.items():
            if path == prefix or path.startswith(prefix + "/"):
                environ["SCRIPT_NAME"] = environ.get("SCRIPT_NAME", "") + prefix
                environ["PATH_INFO"] = path[len(prefix):] or "/"
                environ[ENV_KEY] = name
                break
        return self.wsgi_app(environ, start_response)


class PortalSessionInterface(SecureCookieSessionInterface):
    """Uses a different session cookie for each portal."""

    def get_cookie_name(self, app):
        base = app.config["SESSION_COOKIE_NAME"]
        portal = request.environ.get(ENV_KEY, "customer")
        return base if portal == "customer" else f"{base}_{portal}"


def current_portal():
    return request.environ.get(ENV_KEY, "customer")


def portal_url(portal, endpoint, **values):
    """URL of `endpoint` inside another portal (e.g. send a visitor to seller sign-up)."""
    url = url_for(endpoint, **values)
    root = request.script_root
    if root and url.startswith(root):
        url = url[len(root):]
    return PORTAL_PREFIXES.get(portal, "") + url
