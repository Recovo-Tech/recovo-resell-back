from app.models.cart import Cart, CartStatus
from app.repositories.base import BaseRepository


class CartRepository(BaseRepository):
    def __init__(self, db):
        super().__init__(db, Cart)

    def get_by_user(self, user_id: int):
        return self.db.query(self.model).filter(self.model.user_id == user_id).all()

    def get_active_cart_by_user(self, user_id: int):
        return (
            self.db.query(self.model)
            .filter(
                self.model.user_id == user_id, self.model.status == CartStatus.active
            )
            .first()
        )

    def get_history_by_user(self, user_id: int):
        return (
            self.db.query(self.model)
            .filter(
                self.model.user_id == user_id, self.model.status != CartStatus.active
            )
            .all()
        )
