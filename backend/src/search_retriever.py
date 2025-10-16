from typing import List
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery, QueryType
from azure.core.credentials import AzureKeyCredential
from langchain_core.documents import Document
from .config import AZURE_SEARCH_ENDPOINT, AZURE_SEARCH_API_KEY, AZURE_SEARCH_INDEX_NAME
from .utils import get_embedding 

class AzureHybridSearchRetriever:
    """
    Implementa la búsqueda Híbrida (Vectorial + Keyword + Semántica/RRF) 
    con soporte para Doble Vector en Azure AI Search.
    """
    def __init__(self):
        self.select_fields = ["chunk_id", "numero_dictamen", "embedding_text", "url", "ai_summary"] 
        
        try:
            self.search_client = SearchClient(
                endpoint=AZURE_SEARCH_ENDPOINT,
                index_name=AZURE_SEARCH_INDEX_NAME,
                credential=AzureKeyCredential(AZURE_SEARCH_API_KEY)
            )
            print("✅ SearchClient de Azure AI Search inicializado correctamente.")
        except Exception as e:
            print(f"❌ Error al inicializar SearchClient: {e}")
            self.search_client = None

    def run_hybrid_search(self, query_text: str, use_two_vectors: bool = False) -> List[Document]:
        """
        Ejecuta la búsqueda híbrida con RRF, con opción de usar uno o dos vectores.
        """
        if not self.search_client:
            return [Document(page_content="Error: Cliente de búsqueda no disponible.")]

        query_embedding = get_embedding(query_text)
        if not query_embedding: return []
            
        vector_queries = []
        
        # 1. Vector principal: Búsqueda en el chunk de contenido (Campo 'embedding')
        vector_queries.append(VectorizedQuery(
            vector=query_embedding, 
            k_nearest_neighbors=50, 
            fields="embedding", 
            exhaustive=False
        ))

        # 2. Segundo Vector (Opcional): Búsqueda en el resumen (Campo 'summary_embedding')
        if use_two_vectors:
            vector_queries.append(VectorizedQuery( 
                vector=query_embedding, 
                k_nearest_neighbors=25, 
                fields="summary_embedding", 
                exhaustive=False
            ))

        # Ejecución Híbrida: Palabras clave + Vectores + RRF
        try:
            # Primero intentar búsqueda semántica si está configurada
            try:
                results = self.search_client.search(
                    search_text=query_text,
                    vector_queries=vector_queries,
                    query_type=QueryType.SEMANTIC, 
                    semantic_configuration_name="my-semantic-config",
                    select=self.select_fields,
                    top=5
                )
            except:
                # Si falla la búsqueda semántica, usar búsqueda simple
                print("⚠️ Búsqueda semántica no disponible. Usando búsqueda híbrida simple.")
                results = self.search_client.search(
                    search_text=query_text,
                    vector_queries=vector_queries,
                    select=self.select_fields,
                    top=5
                )
        except Exception as e:
            print(f"Error en la búsqueda de Azure AI Search: {e}")
            # Intentar búsqueda solo por texto como último recurso
            try:
                print("⚠️ Intentando búsqueda solo por texto...")
                results = self.search_client.search(
                    search_text=query_text,
                    select=self.select_fields,
                    top=5
                )
            except Exception as e2:
                print(f"❌ Error crítico en búsqueda: {e2}")
                return []

        retrieved_documents = []
        for result in results:
            doc = dict(result)
            score = doc.get('@search.reranker_score', 0.0) 
            
            lc_doc = Document(
                page_content=doc.get("embedding_text", "Contenido no disponible"),
                metadata={
                    "source": doc.get("numero_dictamen", "N/A"),
                    "url": doc.get("url", ""),
                    "score": score,
                    "summary_match": doc.get("ai_summary", "")
                }
            )
            retrieved_documents.append(lc_doc)
            
        return retrieved_documents

    def run_legal_list_search(self, query_text: str, limit: int = 3) -> List[Document]:
        """
        Búsqueda especializada para listados de dictámenes asociados a leyes o conceptos jurídicos.
        Retorna los últimos dictámenes con información estructurada para tablas.
        """
        if not self.search_client:
            return [Document(page_content="Error: Cliente de búsqueda no disponible.")]

        # Campos específicos para listados de dictámenes
        select_fields = [
            "numero_dictamen", "fecha", "ano", "ai_summary", 
            "fuentes_legales", "dictamenes_aplicados", "url",
            "accion", "referencias", "descriptores", "destinatarios"
        ]
        
        query_embedding = get_embedding(query_text)
        if not query_embedding:
            return []

        vector_queries = [
            VectorizedQuery(
                vector=query_embedding, 
                k_nearest_neighbors=20, 
                fields="embedding", 
                exhaustive=False
            )
        ]

        try:
            # Búsqueda híbrida con filtros específicos para dictámenes
            results = self.search_client.search(
                search_text=query_text,
                vector_queries=vector_queries,
                query_type=QueryType.SEMANTIC,
                semantic_configuration_name="my-semantic-config",
                select=select_fields,
                top=limit,
                order_by=["fecha desc"]  # Ordenar por fecha descendente (más recientes primero)
            )
        except:
            # Fallback a búsqueda simple
            try:
                results = self.search_client.search(
                    search_text=query_text,
                    vector_queries=vector_queries,
                    select=select_fields,
                    top=limit,
                    order_by=["fecha desc"]
                )
            except:
                # Último recurso: búsqueda solo por texto
                results = self.search_client.search(
                    search_text=query_text,
                    select=select_fields,
                    top=limit,
                    order_by=["fecha desc"]
                )

        retrieved_documents = []
        for result in results:
            doc = dict(result)
            
            # Crear documento con metadata estructurada para tablas
            lc_doc = Document(
                page_content=doc.get("ai_summary", "Resumen no disponible"),
                metadata={
                    "numero_dictamen": doc.get("numero_dictamen", "N/A"),
                    "fecha": doc.get("fecha", "N/A"),
                    "ano": doc.get("ano", "N/A"),
                    "resumen": doc.get("ai_summary", "Resumen no disponible"),
                    "leyes_aplicadas": doc.get("fuentes_legales", "N/A"),
                    "dictamenes_aplicados": doc.get("dictamenes_aplicados", "N/A"),
                    "url": doc.get("url", ""),
                    "accion": doc.get("accion", "N/A"),
                    "referencias": doc.get("referencias", "N/A"),
                    "descriptores": doc.get("descriptores", "N/A"),
                    "destinatarios": doc.get("destinatarios", "N/A"),
                    "score": doc.get('@search.reranker_score', 0.0)
                }
            )
            retrieved_documents.append(lc_doc)
            
        return retrieved_documents
