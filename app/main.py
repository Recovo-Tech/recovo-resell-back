from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import (
    auth_routes,
    cart_routes,
    discount_routes,
    product_routes,
    user_routes,
    second_hand_routes,
    shopify_webhook_routes,
    tenant_routes,
)
from app.middleware.tenant_middleware import tenant_middleware

app = FastAPI(title="Recovo Online Store API")

app.middleware("http")(tenant_middleware)

origins = ['*']
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(user_routes.router)
app.include_router(product_routes.router)
app.include_router(cart_routes.router)
app.include_router(auth_routes.router)
app.include_router(discount_routes.router)
app.include_router(second_hand_routes.router)
app.include_router(shopify_webhook_routes.router)
app.include_router(tenant_routes.router)
