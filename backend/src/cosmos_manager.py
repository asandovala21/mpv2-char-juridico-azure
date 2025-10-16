# backend/src/cosmos_manager.py

from typing import List, Dict, Optional
from datetime import datetime
import uuid

try:
    from azure.cosmos import CosmosClient, PartitionKey, exceptions
    COSMOS_AVAILABLE = True
except ImportError:
    COSMOS_AVAILABLE = False
    print("⚠️ azure-cosmos no está instalado. Instala con: pip install azure-cosmos")

from .config import COSMOS_ENDPOINT, COSMOS_KEY, COSMOS_DATABASE_NAME, COSMOS_CONTAINER_NAME, USE_COSMOS_DB


class CosmosDBManager:
    """
    Gestión completa del historial de chat en Azure Cosmos DB.
    
    Características:
    - Guarda mensajes de usuario y asistente con timestamp
    - Recupera historial completo por session_id
    - Limpia historial antiguo
    - Manejo robusto de errores
    """
    
    def __init__(self):
        self.enabled = False
        self.client = None
        self.database = None
        self.container = None
        
        # Solo inicializar si está habilitado y las credenciales están disponibles
        if not USE_COSMOS_DB:
            print("ℹ️ Cosmos DB deshabilitado. Historial se guardará en RAM.")
            print("   Para habilitar, configura USE_COSMOS_DB=true en .env")
            return
        
        if not COSMOS_AVAILABLE:
            print("❌ azure-cosmos no está instalado. Usando RAM como fallback.")
            return
            
        if not COSMOS_ENDPOINT or not COSMOS_KEY:
            print("⚠️ COSMOS_ENDPOINT o COSMOS_KEY no configurados. Usando RAM como fallback.")
            return
        
        try:
            self._initialize_cosmos_db()
            self.enabled = True
            print(f"✅ CosmosDBManager inicializado correctamente.")
            print(f"   📊 Base de datos: {COSMOS_DATABASE_NAME}")
            print(f"   📦 Contenedor: {COSMOS_CONTAINER_NAME}")
        except Exception as e:
            print(f"❌ Error al inicializar Cosmos DB: {e}")
            print("   Usando RAM como fallback.")
    
    def _initialize_cosmos_db(self):
        """
        Inicializa la conexión a Cosmos DB y crea la base de datos/contenedor si no existen.
        Compatible con cuentas Serverless y Provisioned.
        """
        # Conectar al cliente
        self.client = CosmosClient(COSMOS_ENDPOINT, COSMOS_KEY)
        
        # Crear base de datos si no existe
        self.database = self.client.create_database_if_not_exists(id=COSMOS_DATABASE_NAME)
        
        # Crear contenedor si no existe (particionado por session_id para mejor rendimiento)
        # Sin especificar throughput - compatible con cuentas Serverless
        self.container = self.database.create_container_if_not_exists(
            id=COSMOS_CONTAINER_NAME,
            partition_key=PartitionKey(path="/session_id")
        )
        
        print(f"🔧 Cosmos DB configurado: {COSMOS_DATABASE_NAME}/{COSMOS_CONTAINER_NAME}")

    def save_message(self, session_id: str, role: str, content: str, sources: Optional[List[Dict]] = None):
        """
        Guarda un mensaje individual en Cosmos DB.
        
        Args:
            session_id: ID de la sesión de chat
            role: 'user' o 'assistant'
            content: Contenido del mensaje
            sources: Lista de fuentes (solo para mensajes del asistente)
        """
        if not self.enabled:
            return  # Silenciosamente no hace nada si no está habilitado
        
        try:
            message_id = str(uuid.uuid4())
            timestamp = datetime.utcnow().isoformat()
            
            item = {
                "id": message_id,
                "session_id": session_id,
                "role": role,
                "content": content,
                "sources": sources or [],
                "timestamp": timestamp,
                "type": "message"
            }
            
            self.container.create_item(body=item)
            print(f"💾 Mensaje guardado en Cosmos DB: {session_id} - {role}")
            
        except Exception as e:
            print(f"❌ Error al guardar mensaje en Cosmos DB: {e}")

    def get_chat_history(self, session_id: str, limit: Optional[int] = None) -> List[Dict]:
        """
        Recupera el historial completo de una sesión desde Cosmos DB.
        
        Args:
            session_id: ID de la sesión
            limit: Número máximo de mensajes a recuperar (None = todos)
            
        Returns:
            Lista de mensajes ordenados cronológicamente
        """
        if not self.enabled:
            return []
        
        try:
            # Consulta particionada para mejor rendimiento
            query = """
                SELECT * FROM c 
                WHERE c.session_id = @session_id 
                AND c.type = 'message'
                ORDER BY c.timestamp ASC
            """
            
            parameters = [{"name": "@session_id", "value": session_id}]
            
            items = list(self.container.query_items(
                query=query,
                parameters=parameters,
                partition_key=session_id,
                enable_cross_partition_query=False
            ))
            
            # Aplicar límite si se especifica
            if limit:
                items = items[-limit:]  # Últimos N mensajes
            
            print(f"📥 Recuperados {len(items)} mensajes de Cosmos DB para sesión: {session_id}")
            return items
            
        except exceptions.CosmosResourceNotFoundError:
            print(f"ℹ️ No se encontró historial para sesión: {session_id}")
            return []
        except Exception as e:
            print(f"❌ Error al recuperar historial de Cosmos DB: {e}")
            return []
    
    def delete_session(self, session_id: str):
        """
        Elimina todos los mensajes de una sesión.
        
        Args:
            session_id: ID de la sesión a eliminar
        """
        if not self.enabled:
            return
        
        try:
            items = self.get_chat_history(session_id)
            
            for item in items:
                self.container.delete_item(
                    item=item['id'],
                    partition_key=session_id
                )
            
            print(f"🗑️ Sesión eliminada: {session_id} ({len(items)} mensajes)")
            
        except Exception as e:
            print(f"❌ Error al eliminar sesión: {e}")
    
    def get_all_sessions(self, limit: int = 50) -> List[str]:
        """
        Obtiene una lista de todos los session_id únicos.
        
        Args:
            limit: Número máximo de sesiones a retornar
            
        Returns:
            Lista de session_ids
        """
        if not self.enabled:
            return []
        
        try:
            query = """
                SELECT DISTINCT c.session_id, MAX(c.timestamp) as last_message
                FROM c 
                WHERE c.type = 'message'
                GROUP BY c.session_id
                ORDER BY MAX(c.timestamp) DESC
                OFFSET 0 LIMIT @limit
            """
            
            parameters = [{"name": "@limit", "value": limit}]
            
            items = list(self.container.query_items(
                query=query,
                parameters=parameters,
                enable_cross_partition_query=True
            ))
            
            session_ids = [item['session_id'] for item in items]
            print(f"📋 Encontradas {len(session_ids)} sesiones activas")
            return session_ids
            
        except Exception as e:
            print(f"❌ Error al obtener lista de sesiones: {e}")
            return []
    
    def cleanup_old_sessions(self, days_old: int = 30):
        """
        Elimina sesiones más antiguas que X días.
        
        Args:
            days_old: Número de días de antigüedad para considerar una sesión como "vieja"
        """
        if not self.enabled:
            return
        
        try:
            from datetime import timedelta
            cutoff_date = (datetime.utcnow() - timedelta(days=days_old)).isoformat()
            
            query = """
                SELECT c.id, c.session_id FROM c 
                WHERE c.timestamp < @cutoff_date 
                AND c.type = 'message'
            """
            
            parameters = [{"name": "@cutoff_date", "value": cutoff_date}]
            
            items = list(self.container.query_items(
                query=query,
                parameters=parameters,
                enable_cross_partition_query=True
            ))
            
            deleted_count = 0
            for item in items:
                self.container.delete_item(
                    item=item['id'],
                    partition_key=item['session_id']
                )
                deleted_count += 1
            
            print(f"🧹 Limpieza completada: {deleted_count} mensajes antiguos eliminados")
            
        except Exception as e:
            print(f"❌ Error en limpieza de sesiones antiguas: {e}")
