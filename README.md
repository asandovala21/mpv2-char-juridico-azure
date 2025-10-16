# MPV2 Jurídico - Producción

## 🚀 Despliegue Automatizado

Este repositorio está configurado para despliegue automático en Azure Container Apps.

### Configuración de GitHub Secrets

Configura los siguientes secrets en GitHub (Settings > Secrets > Actions):

#### Azure Credentials
- AZURE_CREDENTIALS: Service Principal de Azure

#### API Keys
- AZURE_SEARCH_ENDPOINT
- AZURE_SEARCH_API_KEY
- AZURE_SEARCH_INDEX_NAME
- AZURE_OPENAI_ENDPOINT
- AZURE_OPENAI_API_KEY
- AZURE_OPENAI_CHAT_DEPLOYMENT
- AZURE_OPENAI_EMBEDDING_DEPLOYMENT

#### Cosmos DB (Opcional)
- USE_COSMOS_DB
- COSMOS_ENDPOINT
- COSMOS_KEY
- COSMOS_DB_NAME
- COSMOS_CONTAINER_NAME

### Despliegue

El despliegue se ejecuta automáticamente al hacer push a la rama main.

También puedes ejecutar manualmente:
1. Ve a Actions
2. Selecciona "Deploy to Azure Container Apps"
3. Click en "Run workflow"

### URLs de Producción

- **Frontend**: https://frontend-web.wonderfulocean-98856422.eastus2.azurecontainerapps.io
- **Backend**: Interno (no expuesto públicamente)

### Estructura

\\\
/
├── backend/          # API REST
│   ├── src/         # Código fuente
│   └── Dockerfile   # Imagen Docker
├── frontend/        # Aplicación React
│   ├── src/        # Código fuente
│   └── Dockerfile  # Imagen Docker
├── .github/
│   └── workflows/  # GitHub Actions
└── scripts/        # Scripts de utilidad
\\\

## 🔐 Seguridad

- NO incluyas archivos .env en el repositorio
- Usa GitHub Secrets para credenciales
- Las API keys se inyectan en tiempo de despliegue
