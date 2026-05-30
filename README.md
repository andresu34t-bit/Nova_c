# 🏦 Nova Capital Group

> Plataforma profesional de inversión, trading y gestión de activos financieros

![Python](https://img.shields.io/badge/Python-3.11+-blue?style=flat-square&logo=python)
![Django](https://img.shields.io/badge/Django-4.2-green?style=flat-square&logo=django)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15+-blue?style=flat-square&logo=postgresql)
![License](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)

---

## 📋 Descripción

Nova Capital Group es una plataforma web financiera de nivel institucional construida con Django y PostgreSQL. Incluye trading simulado en tiempo real, gestión de portafolio, mercados globales, noticias financieras y un sistema de seguridad de nivel bancario.

### ✨ Características Principales

- **🔐 Seguridad Bancaria** — 2FA, protección CSRF/XSS, anti-fuerza bruta, registro de actividad
- **📊 Trading Avanzado** — Gráficos TradingView, órdenes de mercado/límite, watchlist
- **🌐 Mercados Globales** — Criptomonedas, acciones, forex e índices en tiempo real
- **💼 Gestión de Portafolio** — Distribución de activos, P&L, evolución histórica
- **💰 Centro Financiero** — Depósitos, retiros, historial de transacciones
- **📰 Noticias Financieras** — Noticias en tiempo real y calendario económico
- **🎨 Diseño Premium** — UI dark mode estilo Bloomberg/TradingView

---

## 🚀 Instalación Rápida

### Requisitos del Sistema

- Python 3.11+
- PostgreSQL 15+
- Git

### 1. Clonar el repositorio

```bash
git clone https://github.com/tu-usuario/nova-capital-group.git
cd nova-capital-group
```

### 2. Crear entorno virtual

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 4. Configurar variables de entorno

```bash
cp .env.example .env
```

Edita `.env` con tus valores:

```env
SECRET_KEY=tu-clave-secreta-muy-larga-y-aleatoria
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

DB_NAME=nova_capital_db
DB_USER=postgres
DB_PASSWORD=tu_password
DB_HOST=localhost
DB_PORT=5432
```

### 5. Crear base de datos PostgreSQL

```sql
CREATE DATABASE nova_capital_db;
CREATE USER nova_user WITH PASSWORD 'tu_password';
GRANT ALL PRIVILEGES ON DATABASE nova_capital_db TO nova_user;
```

### 6. Ejecutar migraciones

```bash
python manage.py migrate
```

### 7. Crear superusuario

```bash
python manage.py createsuperuser
```

### 8. Cargar datos iniciales (opcional)

```bash
python manage.py shell -c "
from apps.markets.views import fetch_market_data
from django.test import RequestFactory
from django.contrib.auth import get_user_model
User = get_user_model()
"
```

### 9. Iniciar servidor de desarrollo

```bash
python manage.py runserver
```

Visita: **http://localhost:8000**

---

## 🔑 Variables de Entorno

| Variable | Descripción | Requerida |
|----------|-------------|-----------|
| `SECRET_KEY` | Clave secreta de Django | ✅ |
| `DEBUG` | Modo debug (True/False) | ✅ |
| `ALLOWED_HOSTS` | Hosts permitidos | ✅ |
| `DB_NAME` | Nombre de la base de datos | ✅ |
| `DB_USER` | Usuario de PostgreSQL | ✅ |
| `DB_PASSWORD` | Contraseña de PostgreSQL | ✅ |
| `DB_HOST` | Host de PostgreSQL | ✅ |
| `DATABASE_URL` | URL completa (para Render) | Producción |
| `EMAIL_HOST_USER` | Email para notificaciones | Opcional |
| `EMAIL_HOST_PASSWORD` | Contraseña del email | Opcional |
| `COINGECKO_API_KEY` | API key de CoinGecko | Opcional |
| `NEWS_API_KEY` | API key de NewsAPI | Opcional |
| `FINNHUB_API_KEY` | API key de Finnhub | Opcional |

---

## 🌐 Despliegue en Render

### 1. Crear cuenta en [Render](https://render.com)

### 2. Conectar repositorio de GitHub

### 3. Crear nuevo Web Service

- **Build Command:** `./build.sh`
- **Start Command:** `gunicorn config.wsgi:application --bind 0.0.0.0:$PORT`

### 4. Configurar variables de entorno en Render

Añade todas las variables del archivo `.env.example` en el panel de Render.

### 5. Crear base de datos PostgreSQL en Render

El archivo `render.yaml` ya incluye la configuración automática.

### Despliegue con render.yaml (automático)

```bash
# El archivo render.yaml en la raíz configura todo automáticamente
# Solo conecta tu repo y Render detectará la configuración
```

---

## 📁 Estructura del Proyecto

```
nova_capital_group/
├── apps/
│   ├── accounts/          # Usuarios, autenticación, KYC
│   ├── core/              # Landing page, middleware, contexto
│   ├── dashboard/         # Panel principal
│   ├── markets/           # Mercados y precios
│   ├── trading/           # Terminal de trading, órdenes
│   ├── portfolio/         # Gestión de portafolio
│   ├── finances/          # Depósitos, retiros, transacciones
│   └── news/              # Noticias financieras
├── config/
│   ├── settings/
│   │   ├── base.py        # Configuración base
│   │   ├── development.py # Desarrollo local
│   │   └── production.py  # Producción (Render)
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
├── static/
│   ├── css/nova.css       # Estilos premium
│   └── js/
├── templates/             # Templates HTML
├── .env.example           # Variables de entorno ejemplo
├── .gitignore
├── build.sh               # Script de build para Render
├── manage.py
├── Procfile
├── render.yaml            # Configuración de Render
├── requirements.txt
└── README.md
```

---

## 🔒 Seguridad

- ✅ Autenticación 2FA con TOTP
- ✅ Verificación por email
- ✅ Protección CSRF en todos los formularios
- ✅ Protección XSS con Content Security Policy
- ✅ Protección SQL Injection (ORM de Django)
- ✅ Protección contra fuerza bruta (django-axes, 5 intentos)
- ✅ Sesiones seguras con HttpOnly y SameSite
- ✅ Headers de seguridad (HSTS, X-Frame-Options, etc.)
- ✅ Registro completo de actividad de usuarios
- ✅ Encriptación de datos sensibles

---

## 🛠️ Tecnologías

| Tecnología | Versión | Uso |
|-----------|---------|-----|
| Django | 4.2 | Framework principal |
| PostgreSQL | 15+ | Base de datos |
| Bootstrap | 5.3 | UI Framework |
| Chart.js | 4.4 | Gráficos |
| TradingView | Latest | Gráficos de trading |
| django-axes | 6.4 | Anti-fuerza bruta |
| django-otp | 1.3 | 2FA |
| Whitenoise | 6.6 | Archivos estáticos |
| Gunicorn | 21.2 | Servidor WSGI |

---

## 📊 APIs Utilizadas

- **CoinGecko** — Precios de criptomonedas en tiempo real
- **NewsAPI** — Noticias financieras
- **Finnhub** — Datos de acciones y forex
- **TradingView** — Widget de gráficos avanzados

---

## 🤝 Contribución

1. Fork el repositorio
2. Crea una rama: `git checkout -b feature/nueva-funcionalidad`
3. Commit: `git commit -m 'feat: añadir nueva funcionalidad'`
4. Push: `git push origin feature/nueva-funcionalidad`
5. Abre un Pull Request

---

## ⚠️ Aviso Legal

Esta plataforma es para **fines educativos y de simulación**. No constituye asesoramiento financiero real. Las inversiones en mercados financieros conllevan riesgo de pérdida.

---

## 📄 Licencia

MIT License — ver [LICENSE](LICENSE) para más detalles.

---

<div align="center">
  <strong>Nova Capital Group</strong> · Inversiones de Clase Mundial
</div>
