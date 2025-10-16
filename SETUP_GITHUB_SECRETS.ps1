# Configurar GitHub Secrets para el repositorio

Write-Host "=== CONFIGURACIÓN DE GITHUB SECRETS ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "Necesitas configurar los siguientes secrets en GitHub:" -ForegroundColor Yellow
Write-Host ""
Write-Host "1. Ve a: https://github.com/asandovala21/mpv2-char-juridico-azure/settings/secrets/actions" -ForegroundColor White
Write-Host ""
Write-Host "2. Agrega estos secrets:" -ForegroundColor Yellow
Write-Host ""
Write-Host "AZURE_CREDENTIALS:" -ForegroundColor Cyan
Write-Host '  Ejecuta: az ad sp create-for-rbac --name "github-actions" --role contributor --scopes /subscriptions/{subscription-id}/resourceGroups/CDEIA_sistradoc --sdk-auth' -ForegroundColor White
Write-Host ""
Write-Host "AZURE_SEARCH_ENDPOINT: https://aisearch-cgr.search.windows.net" -ForegroundColor Cyan
Write-Host "AZURE_SEARCH_API_KEY: (tu key)" -ForegroundColor Cyan
Write-Host "AZURE_SEARCH_INDEX_NAME: dictamenes-juridicos" -ForegroundColor Cyan
Write-Host ""
Write-Host "AZURE_OPENAI_ENDPOINT: https://openai-sistradoc.openai.azure.com/" -ForegroundColor Cyan
Write-Host "AZURE_OPENAI_API_KEY: (tu key)" -ForegroundColor Cyan
Write-Host "AZURE_OPENAI_CHAT_DEPLOYMENT: gpt-4.1" -ForegroundColor Cyan
Write-Host "AZURE_OPENAI_EMBEDDING_DEPLOYMENT: text-embedding-3-large" -ForegroundColor Cyan
Write-Host ""
Write-Host "USE_COSMOS_DB: true" -ForegroundColor Cyan
Write-Host "COSMOS_ENDPOINT: https://chat-juris-db-cosmos-history.documents.azure.com:443/" -ForegroundColor Cyan
Write-Host "COSMOS_KEY: (tu key)" -ForegroundColor Cyan
Write-Host "COSMOS_DB_NAME: chat_database" -ForegroundColor Cyan
Write-Host "COSMOS_CONTAINER_NAME: chat_history" -ForegroundColor Cyan
