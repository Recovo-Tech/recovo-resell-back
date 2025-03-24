# app/main.py
from fastapi import FastAPI

from app.routes import (
    auth_routes,
    cart_routes,
    discount_routes,
    product_routes,
    user_routes,
)

app = FastAPI(title="Recovo Online Store API", docs_url=None)

app.include_router(user_routes.router)
app.include_router(product_routes.router)
app.include_router(cart_routes.router)
app.include_router(auth_routes.router)
app.include_router(discount_routes.router)
