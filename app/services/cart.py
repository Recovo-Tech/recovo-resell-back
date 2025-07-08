from fastapi import HTTPException

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
        """
        Calculates the subtotal, discount value, and final total for the active cart.
        Applies the discount (if any) based on its type and conditions.
        """
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
        """
        Finalizes the active cart of the user by:
          - Calculating totals (which applies the discount if applicable)
          - Subtracting purchased item quantities from the product stocks
          - Marking the cart as 'completed'
          - Returning the finalized cart and totals summary
        """
        cart = self.get_active_cart(user_id)
        if not cart:
            return None

        totals = self.calculate_totals(user_id)

        for item in cart.items:
            product = item.product
            if product.stock < item.quantity:
                raise HTTPException(
                    status_code=400,
                    detail=f"error.insufficient_stock_for_product {product.name}",
                )
            product.stock -= item.quantity

        self.cart_repo.db.commit()

        finalized_cart = self.cart_repo.update(cart, {"status": CartStatus.completed})
        return {"cart": finalized_cart, "totals": totals}

    def apply_discount(self, user_id: int, discount_id: int, discount_service):
        """
        Applies a discount to the active cart.
        - Retrieves or creates the active cart.
        - Validates the discount using discount_service.
        - Checks that the cart's subtotal meets the discount's min_purchase (if defined).
        - Updates the cart to include the discount.
        """
        cart = self.get_active_cart(user_id)
        if not cart:
            cart = self.create_cart_for_user(user_id)

        discount = discount_service.get_discount_by_id(discount_id)
        if not discount or not discount.active:
            raise HTTPException(
                status_code=400, detail="error.invalid_or_inactive_discount"
            )

        totals = self.calculate_totals(user_id)
        if (
            discount.min_purchase is not None
            and totals["subtotal"] < discount.min_purchase
        ):
            raise HTTPException(
                status_code=400,
                detail="error.cart_subtotal_does_not_meet_the_discount_requirements",
            )

        updated_cart = self.cart_repo.update(cart, {"discount_id": discount_id})
        return updated_cart
