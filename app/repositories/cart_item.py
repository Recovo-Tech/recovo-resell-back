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
