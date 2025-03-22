from app.models.discount import Discount
from app.repositories.base import BaseRepository


class DiscountRepository(BaseRepository):
    def __init__(self, db):
        super().__init__(db, Discount)

    def get_active_discounts(self):
        return self.db.query(self.model).filter(self.model.active == True).all()

    def get_discount_by_type(self, discount_type: str):
        return (
            self.db.query(self.model)
            .filter(
                self.model.discount_type == discount_type, self.model.active == True
            )
            .all()
        )
