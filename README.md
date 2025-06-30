# Recovo - Second-Hand Marketplace with Shopify Integration

A FastAPI-based e-commerce platform that allows customers to sell their second-hand products through your store, with Shopify product verification to ensure only authentic store products can be resold.

## Features

### Second-Hand Marketplace

- **Product Verification**: Verify products against Shopify store inventory using SKU or barcode
- **Secure Listings**: Only products that exist in your Shopify store can be listed
- **Product Management**: Upload images, set prices, manage condition status
- **Admin Approval**: Admin approval system for second-hand listings
- **Real-time Updates**: Shopify webhooks to keep product status synchronized

### Shopify Integration

- **GraphQL API**: Direct integration with Shopify GraphQL API
- **Product Verification**: Real-time verification of SKUs and barcodes
- **Webhook Support**: Automatic updates when products change in Shopify
- **Inventory Sync**: Maintain consistency between store and marketplace

## Technology Stack

- **Backend**: FastAPI (Python)
- **Database**: PostgreSQL
- **ORM**: SQLAlchemy
- **Migration**: Alembic
- **Authentication**: JWT tokens
- **File Storage**: Local filesystem (can be extended to cloud storage)
- **External API**: Shopify GraphQL API

## Prerequisites

- Python 3.8+
- Docker and Docker Compose
- Shopify Partner Account (for app development)
- PostgreSQL (via Docker)

## Setup Instructions

### 1. Clone and Setup Environment

```bash
cd c:\Users\nacho\Desktop\works\recovo
cp .env.example .env
```

### 2. Configure Environment Variables

Edit `.env` file with your settings:

```env
# Database Configuration
DATABASE_USERNAME=postgres
DATABASE_PASSWORD=
DATABASE_HOSTNAME=db  # Use 'localhost' for local development
DATABASE_PORT=5432
DATABASE_NAME=recovo
DATABASE_POOL_SIZE=10
DATABASE_POOL_SIZE_OVERFLOW=10

# Authentication
SECRET_KEY=your-super-secret-jwt-key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Shopify Configuration
SHOPIFY_APP_URL=your-app-domain.com
SHOPIFY_API_KEY=your-shopify-api-key
SHOPIFY_API_SECRET=your-shopify-api-secret
SHOPIFY_WEBHOOK_SECRET=your-webhook-secret
SHOPIFY_SCOPES=read_products,write_products,read_inventory,write_inventory
SHOPIFY_API_VERSION=2024-01

# File Upload
MAX_FILE_SIZE=5242880
ALLOWED_IMAGE_EXTENSIONS=jpg,jpeg,png,webp
UPLOAD_DIRECTORY=uploads/second_hand_products
```

### 3. Install Dependencies

```bash
# Activate virtual environment
.\var\venv\Scripts\activate

# Install requirements
pip install -r requirements.txt
```

### 4. Start Database

```bash
docker-compose up -d db
```

### 5. Run Migrations

```bash
alembic upgrade head
```

### 6. Start the Application

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## API Endpoints

### Second-Hand Marketplace

#### Product Verification

- `POST /second-hand/verify-product` - Verify if a product exists in your Shopify store by SKU and/or barcode.

**Request Body:**
```json
{
  "sku": "ABC123",         // optional, string
  "barcode": "1234567890"  // optional, string
}
```

**Response Example:**
```json
{
  "is_verified": true,
  "product_info": {
    "id": "gid://shopify/Product/123456789",
    "title": "iPhone 13 Pro",
    "sku": "ABC123",
    "barcode": "1234567890"
  },
  "verification_method": "sku",
  "error": null
}
```

- If the product is not found, `is_verified` will be `false` and `error` will contain a message.
- At least one of `sku` or `barcode` must be provided.

#### Product Management

- `POST /second-hand/products` - Create new second-hand product
- `GET /second-hand/products` - Get all approved products
- `GET /second-hand/products/my` - Get current user's products
- `GET /second-hand/products/{id}` - Get specific product
- `PUT /second-hand/products/{id}` - Update product (owner only)
- `DELETE /second-hand/products/{id}` - Delete product (owner only)
- `POST /second-hand/products/search` - Search products with filters

#### File Upload

- `POST /second-hand/upload-images` - Upload product images

#### Admin Functions

- `POST /second-hand/admin/products/{id}/approve` - Approve product for sale

### Shopify Webhooks

- `POST /webhooks/shopify/products/update` - Handle product updates
- `POST /webhooks/shopify/products/delete` - Handle product deletions

## API Reference

### Authentication

- `POST /auth/register` — Register a new user and receive a JWT token
- `POST /auth/login` — Log in and receive a JWT token

### Users

- `GET /users/me` — Get current user's profile (auth required)
- `PUT /users/me` — Update current user's profile (auth required)
- `DELETE /users/me` — Delete current user's account (auth required)
- `GET /users/` — List all users (admin only)
- `PATCH /users/{user_id}/role` — Update a user's role (admin only)

### Products

- `GET /products/` — List all products
- `GET /products/{product_id}` — Get product by ID
- `POST /products/` — Create a new product (auth required)
- `PUT /products/{product_id}` — Update a product (auth required)
- `DELETE /products/{product_id}` — Delete a product (auth required)

### Cart

- `GET /cart/` — Get current user's active cart (auth required)
- `POST /cart/items` — Add item to cart (auth required)
- `DELETE /cart/items` — Remove item from cart (auth required)
- `POST /cart/empty` — Empty the cart (auth required)
- `POST /cart/finalize` — Finalize and checkout the cart (auth required)
- `POST /cart/apply-discount` — Apply a discount to the cart (auth required)

### Discounts

- `POST /discounts/` — Create a discount (auth required)
- `GET /discounts/` — List all discounts
- `PUT /discounts/{discount_id}` — Update a discount (auth required)
- `DELETE /discounts/{discount_id}` — Deactivate a discount (auth required)

### Second-Hand Marketplace

- `POST /second-hand/verify-product` — Verify product by SKU/barcode
- `POST /second-hand/products` — Create new second-hand product (auth required)
- `GET /second-hand/products` — Get all approved second-hand products
- `GET /second-hand/products/my` — Get current user's second-hand products (auth required)
- `GET /second-hand/products/{id}` — Get a specific second-hand product
- `PUT /second-hand/products/{id}` — Update a second-hand product (owner only, auth required)
- `DELETE /second-hand/products/{id}` — Delete a second-hand product (owner only, auth required)
- `POST /second-hand/products/search` — Search second-hand products with filters
- `POST /second-hand/upload-images` — Upload product images (auth required)
- `POST /second-hand/admin/products/{id}/approve` — Approve a second-hand product for sale (admin only)

### Shopify Webhooks

- `POST /webhooks/shopify/products/update` — Handle product updates from Shopify
- `POST /webhooks/shopify/products/delete` — Handle product deletions from Shopify

Each endpoint may require authentication and/or specific roles (admin/client). See the code and docstrings for detailed request/response formats and permissions.

## Usage Example

### 1. Verify Product

First, verify that a product exists in your Shopify store:

```python
import requests

verification_data = {
    "sku": "ABC123",
    "barcode": "1234567890123",
    "shop_domain": "your-shop.myshopify.com",
    "access_token": "your-access-token"
}

response = requests.post(
    "http://localhost:8000/second-hand/verify-product",
    json=verification_data
)
```

### 2. Upload Product Images

Upload images for your second-hand product:

```python
files = [
    ('files', open('product1.jpg', 'rb')),
    ('files', open('product2.jpg', 'rb'))
]

response = requests.post(
    "http://localhost:8000/second-hand/upload-images",
    files=files,
    headers={"Authorization": "Bearer your-jwt-token"}
)
image_urls = response.json()["image_urls"]
```

### 3. Create Second-Hand Product

Create a new second-hand product listing:

```python
product_data = {
    "name": "iPhone 13 Pro - Like New",
    "description": "Barely used iPhone 13 Pro in excellent condition",
    "price": 899.99,
    "condition": "like_new",
    "original_sku": "IPHONE13PRO-128-GOLD",
    "barcode": "1234567890123",
    "image_urls": image_urls
}

response = requests.post(
    "http://localhost:8000/second-hand/products",
    json=product_data,
    params={
        "shop_domain": "your-shop.myshopify.com",
        "shopify_access_token": "your-access-token"
    },
    headers={"Authorization": "Bearer your-jwt-token"}
)
```

## Shopify App Setup

### 1. Create Shopify App

1. Go to [Shopify Partners](https://partners.shopify.com/)
2. Create a new app
3. Configure app settings with your domain
4. Set required scopes: `read_products,write_products,read_inventory,write_inventory`

### 2. Configure Webhooks

Set up webhooks in your Shopify app for:

- Product updates: `https://your-domain.com/webhooks/shopify/products/update`
- Product deletions: `https://your-domain.com/webhooks/shopify/products/delete`

### 3. Install App

Install your app on the target Shopify store and obtain the access token.

## Database Schema

### Second-Hand Products

- Product information with seller details
- SKU/barcode verification status
- Admin approval status
- Connection to original Shopify product

### Product Images

- Multiple images per product
- Primary image designation
- Optimized for web delivery

## Security Features

- **JWT Authentication**: Secure user authentication
- **Product Verification**: Only authentic store products allowed
- **Admin Approval**: Manual review before products go live
- **Webhook Verification**: Secure webhook handling with HMAC validation
- **File Upload Security**: Image validation and optimization

## Development

### Running Tests

```bash
pytest
```

### Database Migration

```bash
# Create new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback migration
alembic downgrade -1
```

### Code Formatting

```bash
black app/
isort app/
```

## Production Deployment

1. **Environment**: Update environment variables for production
2. **Database**: Use managed PostgreSQL service
3. **File Storage**: Configure cloud storage (AWS S3, etc.)
4. **HTTPS**: Enable SSL/TLS for security
5. **Monitoring**: Add logging and monitoring
6. **Scaling**: Consider Redis for caching and session management

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

This project is licensed under the MIT License.
