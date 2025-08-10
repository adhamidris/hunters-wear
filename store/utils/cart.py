from decimal import Decimal

CART_KEY = "cart"

def get_cart(session):
    cart = session.get(CART_KEY, {"items": []})
    return cart

def save_cart(session, cart):
    session[CART_KEY] = cart
    session.modified = True


