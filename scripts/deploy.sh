#!/bin/bash
# Script de despliegue manual a Azure Container Apps

set -e

# Configuración
RESOURCE_GROUP="CDEIA_sistradoc"
ACR_NAME="acrjurisprudencia8tzl21"
BACKEND_APP="backend-api"
FRONTEND_APP="frontend-web"

echo "🚀 Iniciando despliegue a Azure Container Apps..."

# Login a Azure
echo "📝 Iniciando sesión en Azure..."
az login

# Login a ACR
echo "🔐 Conectando a Azure Container Registry..."
az acr login --name $ACR_NAME

# Build y push del Backend
echo "🔨 Construyendo Backend..."
cd backend
az acr build --registry $ACR_NAME --image backend-api:latest --platform linux/amd64 . --no-logs
cd ..

# Build y push del Frontend
echo "🔨 Construyendo Frontend..."
cd frontend
az acr build --registry $ACR_NAME --image frontend-web:latest --platform linux/amd64 . --no-logs
cd ..

# Actualizar Backend
echo "📦 Desplegando Backend..."
az containerapp update \
  --name $BACKEND_APP \
  --resource-group $RESOURCE_GROUP \
  --image $ACR_NAME.azurecr.io/backend-api:latest

# Actualizar Frontend
echo "📦 Desplegando Frontend..."
az containerapp update \
  --name $FRONTEND_APP \
  --resource-group $RESOURCE_GROUP \
  --image $ACR_NAME.azurecr.io/frontend-web:latest

echo "✅ Despliegue completado!"
echo "🌐 URL: https://frontend-web.wonderfulocean-98856422.eastus2.azurecontainerapps.io"
