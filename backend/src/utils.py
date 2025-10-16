from langchain_openai import AzureOpenAIEmbeddings
from .config import AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY, AZURE_OPENAI_EMBEDDING_DEPLOYMENT

# Inicializar el cliente de Embeddings de Azure OpenAI
try:
    embedding_model = AzureOpenAIEmbeddings(
        azure_deployment=AZURE_OPENAI_EMBEDDING_DEPLOYMENT,
        openai_api_version="2024-02-01",
        azure_endpoint=AZURE_OPENAI_ENDPOINT,
        openai_api_key=AZURE_OPENAI_API_KEY
    )
    print("✅ AzureOpenAIEmbeddings inicializado.")
except Exception as e:
    print(f"❌ Error al inicializar AzureOpenAIEmbeddings. Verifica tu .env. Error: {e}")
    embedding_model = None

def get_embedding(text: str) -> list[float] | None:
    """
    Genera el vector de embedding para una consulta de texto.
    """
    if not embedding_model:
        return None
    try:
        return embedding_model.embed_query(text)
    except Exception as e:
        print(f"Error generando embedding para el texto: '{text[:20]}...'. Error: {e}")
        return None
