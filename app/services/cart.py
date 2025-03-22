from app.models.cart import Cart, CartStatus
from app.repositories import CartItemRepository, CartRepository


class CartService:
    def __init__(self, db):
        self.cart_repo = CartRepository(db)
        self.cart_item_repo = CartItemRepository(db)

    def get_active_cart(self, user_id: int):
        return self.cart_repo.get_active_cart_by_user(user_id)

    def create_cart_for_user(self, user_id: int):
        new_cart = Cart(user_id=user_id, status=CartStatus.active)
        return self.cart_repo.create(new_cart)

    def add_item_to_cart(self, user_id: int, product_id: int, quantity: int = 1):
        cart = self.get_active_cart(user_id)
        if not cart:
            cart = self.create_cart_for_user(user_id)
        return self.cart_item_repo.add_item_to_cart(cart.id, product_id, quantity)

    def remove_item_from_cart(self, user_id: int, product_id: int, quantity: int = 1):
        cart = self.get_active_cart(user_id)
        if not cart:
            return None
        return self.cart_item_repo.remove_item_from_cart(cart.id, product_id, quantity)

    def empty_cart(self, user_id: int):
        cart = self.get_active_cart(user_id)
        if cart:
            self.cart_item_repo.delete_items_by_cart(cart.id)
        return cart

    def get_cart_history(self, user_id: int):
        return self.cart_repo.get_history_by_user(user_id)

    def calculate_totals(self, user_id: int):
        cart = self.get_active_cart(user_id)
        if not cart:
            return {"subtotal": 0, "discount_value": 0, "total": 0}

        subtotal = sum(item.quantity * item.product.price for item in cart.items)
        discount_value = 0

        if cart.discount and cart.discount.active:
            if (
                cart.discount.min_purchase is None
                or subtotal >= cart.discount.min_purchase
            ):
                if cart.discount.discount_type == "percentage":
                    discount_value = subtotal * (cart.discount.value / 100)
                elif cart.discount.discount_type == "fixed":
                    discount_value = min(cart.discount.value, subtotal)

        total = subtotal - discount_value

        return {"subtotal": subtotal, "discount_value": discount_value, "total": total}

    def finalize_cart(self, user_id: int):
        cart = self.get_active_cart(user_id)
        if not cart:
            return None

        totals = self.calculate_totals(user_id)
        finalized_cart = self.cart_repo.update(cart, {"status": CartStatus.completed})

        return {"cart": finalized_cart, "totals": totals}
