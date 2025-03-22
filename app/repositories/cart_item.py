from app.models.cart import CartItem
from app.repositories.base import BaseRepository


class CartItemRepository(BaseRepository):
    def __init__(self, db):
        super().__init__(db, CartItem)

    def get_items_by_cart(self, cart_id: int):
        return self.db.query(self.model).filter(self.model.cart_id == cart_id).all()

    def delete_items_by_cart(self, cart_id: int):
        items = self.get_items_by_cart(cart_id)
        for item in items:
            self.db.delete(item)
        self.db.commit()

    def add_item_to_cart(self, cart_id: int, product_id: int, quantity: int):
        existing_item = (
            self.db.query(self.model)
            .filter(self.model.cart_id == cart_id, self.model.product_id == product_id)
            .first()
        )

        if existing_item:
            existing_item.quantity += quantity
            self.db.commit()
            self.db.refresh(existing_item)
            return existing_item
        else:
            new_item = self.model(
                cart_id=cart_id, product_id=product_id, quantity=quantity
            )
            self.db.add(new_item)
            self.db.commit()
            self.db.refresh(new_item)
            return new_item

    def remove_item_from_cart(self, cart_id: int, product_id: int, quantity: int):
        existing_item = (
            self.db.query(self.model)
            .filter(self.model.cart_id == cart_id, self.model.product_id == product_id)
            .first()
        )

        if not existing_item:
            return None

        if existing_item.quantity > quantity:
            existing_item.quantity -= quantity
            self.db.commit()
            self.db.refresh(existing_item)
            return existing_item
        else:
            self.db.delete(existing_item)
            self.db.commit()
            return None
