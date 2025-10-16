// Configuración de la aplicación frontend

// Determinar la URL del backend basándose en el entorno
const getBackendUrl = () => {
    // En producción (Azure Container Apps), usar la ruta relativa /api
    // que será proxeada por nginx al backend interno
    if (process.env.NODE_ENV === 'production') {
        return '/api';
    }
    
    // En desarrollo, usar la variable de entorno o valor por defecto
    if (process.env.REACT_APP_API_URL) {
        return process.env.REACT_APP_API_URL;
    }
    
    // Valor por defecto para desarrollo local
    return 'http://127.0.0.1:8000';
};

const config = {
    API_URL: getBackendUrl(),
    CHAT_ENDPOINT: `${getBackendUrl()}/chat`,
    
    // Configuración de timeouts
    REQUEST_TIMEOUT: 60000, // 60 segundos para operaciones RAG
    
    // Configuración de reintentos
    MAX_RETRIES: 3,
    RETRY_DELAY: 1000,
    
    // Configuración de UI
    MAX_MESSAGE_LENGTH: 5000,
    MAX_HISTORY_ITEMS: 50,
    
    // Feature flags
    ENABLE_DOUBLE_VECTOR: true,
    ENABLE_COSMOS_DB: process.env.REACT_APP_USE_COSMOS_DB === 'true',
};

export default config;
