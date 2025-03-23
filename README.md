# Recovo CIMS - Prueba Técnica Backend Senior

Este repositorio contiene la solución del backend para una tienda online, desarrollada como parte de la prueba técnica para el puesto de Backend Senior en Recovo CIMS. La aplicación está construida con **FastAPI** y  **Python**, utiliza **PostgreSQL** como base de datos y está completamente dockerizada para facilitar su ejecución local.

## Requisitos

* **Docker** y **Docker Compose** instalados en tu máquina.
* El proyecto se ejecuta con **Python 3.9** (o superior).

## Instalación y Ejecución

### 1. Clona el Repositorio y accede a el.

```
https://github.com/nachovoss/recovo.git
```

```
cd  recovo
```

### 2. Configura las Variables de Entorno

Si fuese necesario, modifica el archivo `.env` en la raíz del proyecto.
Normalmente, no incluiria el archivo .env en el repositorio pero en este caso lo he incluido para facilitarle la ejecucíon a quien valore la prueba.

### 3. Levanta la Aplicación con Docker Compose

Construye y levanta los contenedores ejecutando:

```
docker-compose up --build
```

Esto iniciará los contenedores para:

* **api** : La aplicación FastAPI.
* **db** : PostgreSQL.

La API estará disponible en [http://localhost:8000]() y la documentación interactiva (Swagger UI) en [http://localhost:8000/docs]().


## Colección Postman

Se proporciona una colección exportada en el archivo `postman_collection.json`. Para probar los endpoints de la API utilizando Postman, sigue estos pasos:

1. **Crear un usuario:**

   Primero, utiliza el endpoint **"create user"** para registrar un nuevo usuario en la aplicación.
2. **Iniciar sesión:**

   Una vez creado el usuario, llama al endpoint  **"login"** . Este endpoint validará las credenciales y devolverá un token JWT.
3. **Copiar el token:**

   Copia el token de acceso que se devuelve en la respuesta del login.
4. **Autenticar en Postman:**

   En Postman, abre la pestaña de **Autorización** de la colección o del request. Selecciona el tipo **Bearer Token** e introduce el token copiado.

   De esta forma, todas las peticiones a los endpoints protegidos incluirán el token de autenticación en la cabecera `Authorization`.

Con estos pasos, podrás probar todos los endpoints implementados en la API. La colección incluye ejemplos de peticiones para la gestión de usuarios, productos, carrito y descuentos.


## Estructura del Proyecto

```

project-root
├── alembic                       # Migraciones de base de datos con Alembic
├── app
│   ├── config.py                 # Configuración de la aplicación (DB, etc.)
│   ├── dependencies.py           # Inyección de dependencias (servicios, DB, etc.)
│   ├── main.py                   # Punto de entrada de la aplicación FastAPI
│   ├── models                    # Modelos SQLAlchemy
│   │   ├── __init__.py
│   │   ├── cart.py
│   │   ├── discount.py
│   │   ├── product.py
│   │   └── user.py
│   ├── repositories              # Acceso a la base de datos (CRUD)
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── cart.py
│   │   ├── cart_item.py
│   │   ├── discount.py
│   │   ├── product.py
│   │   └── user.py
│   ├── routes                    # Endpoints agrupados por funcionalidad (routers)
│   │   ├── __init__.py
│   │   ├── auth_routes.py
│   │   ├── cart_routes.py
│   │   ├── discount_routes.py
│   │   ├── product_routes.py
│   │   └── user_routes.py
│   ├── schemas                   # Esquemas Pydantic para validación y serialización
│   │   ├── __init__.py
│   │   ├── cart.py
│   │   ├── discount.py
│   │   ├── product.py
│   │   └── user.py
│   └── services                  # Lógica de negocio
│       ├── auth.py
│       ├── cart.py
│       ├── discount.py
│       ├── product.py
│       └── user.py
├── Dockerfile                    # Imagen de la aplicación FastAPI
├── docker-compose.yml            # Orquestación de contenedores (FastAPI, PostgreSQL, Redis)
├── postman_collection.json       # Colección exportada de Postman con todos los endpoints
├── README.md                     # Este archivo
└── requirements.txt              # Dependencias del proyecto
```



## Buenas Prácticas y Patrones Utilizados

* **Patrón de Repositorio:** Se utiliza para centralizar el acceso a la base de datos y evitar duplicación de código.
* **Servicios:** La lógica de negocio se implementa en servicios que consumen los repositorios, lo que facilita la escalabilidad y mantenibilidad.
* **Modularización:** La aplicación está organizada en módulos (models, schemas, repositories, services, routes), facilitando el mantenimiento y la comprensión del código.
* **Dockerización:** El uso de Docker y Docker Compose simplifica la ejecución local y garantiza un entorno consistente.
