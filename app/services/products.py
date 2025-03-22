from app.repositories import ProductRepository
from app.models.product import Product

class ProductService:
    def __init__(self, db):
        self.repo = ProductRepository(db)

    def get_all_products(self):
        return self.repo.get_all()

    def get_product_by_id(self, product_id: int):
        return self.repo.get_by_id(product_id)

    def create_product(self, product_data: dict):
        # Se asume que product_data contiene las claves necesarias
        new_product = Product(**product_data)
        return self.repo.create(new_product)

    def update_product(self, product_id: int, update_data: dict):
        product = self.get_product_by_id(product_id)
        if not product:
            return None
        return self.repo.update(product, update_data)

    def delete_product(self, product_id: int):
        product = self.get_product_by_id(product_id)
        if not product:
            return False
        self.repo.delete(product)
        return True

    def search_products_by_name(self, name: str):
        return self.repo.get_by_name(name)
