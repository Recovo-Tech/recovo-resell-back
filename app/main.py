# app/main.py
from fastapi import FastAPI
from app.routes import user_routes, product_routes, cart_routes, auth_routes

app = FastAPI(title="Online Store API")

app.include_router(user_routes.router)
app.include_router(product_routes.router)
app.include_router(cart_routes.router)
app.include_router(auth_routes.router)
