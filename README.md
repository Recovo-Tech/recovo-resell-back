# Recovo CIMS - Prueba Técnica Backend Senior

Este repositorio contiene la solución del backend para una tienda online, desarrollada como parte de la prueba técnica para el puesto de Backend Senior en Recovo CIMS. La aplicación está construida con **FastAPI** y  **Python**, utiliza **PostgreSQL** como base de datos y está completamente dockerizada para facilitar su ejecución local.


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
normalmente no incluiria el archivo .env en el repositorio pero en este caso lo he incluido para facilitar le la ejecucío a quien valore la prueba.


### 3. Levanta la Aplicación con Docker Compose

Construye y levanta los contenedores ejecutando:

<pre class="!overflow-visible" data-start="4759" data-end="4796"><div class="contain-inline-size rounded-md border-[0.5px] border-token-border-medium relative bg-token-sidebar-surface-primary"><div class="flex items-center text-token-text-secondary px-4 py-2 text-xs font-sans justify-between h-9 bg-token-sidebar-surface-primary dark:bg-token-main-surface-secondary select-none rounded-t-[5px]">bash</div><div class="sticky top-9"><div class="absolute bottom-0 right-0 flex h-9 items-center pr-2"><div class="flex items-center rounded bg-token-sidebar-surface-primary px-2 font-sans text-xs text-token-text-secondary dark:bg-token-main-surface-secondary"><span class="" data-state="closed"><button class="flex gap-1 items-center select-none px-4 py-1" aria-label="Copiar"><svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" class="icon-xs"><path fill-rule="evenodd" clip-rule="evenodd" d="M7 5C7 3.34315 8.34315 2 10 2H19C20.6569 2 22 3.34315 22 5V14C22 15.6569 20.6569 17 19 17H17V19C17 20.6569 15.6569 22 14 22H5C3.34315 22 2 20.6569 2 19V10C2 8.34315 3.34315 7 5 7H7V5ZM9 7H14C15.6569 7 17 8.34315 17 10V15H19C19.5523 15 20 14.5523 20 14V5C20 4.44772 19.5523 4 19 4H10C9.44772 4 9 4.44772 9 5V7ZM5 9C4.44772 9 4 9.44772 4 10V19C4 19.5523 4.44772 20 5 20H14C14.5523 20 15 19.5523 15 19V10C15 9.44772 14.5523 9 14 9H5Z" fill="currentColor"></path></svg>Copiar</button></span></div></div></div><div class="overflow-y-auto p-4" dir="ltr"><code class="!whitespace-pre language-bash"><span><span>docker-compose up --build
</span></span></code></div></div></pre>

Esto iniciará los contenedores para:

* **api** : La aplicación FastAPI.
* **db** : PostgreSQL.
* **redis** : Redis.

La API estará disponible en [http://localhost:8000]() y la documentación interactiva (Swagger UI) en [http://localhost:8000/docs]().
