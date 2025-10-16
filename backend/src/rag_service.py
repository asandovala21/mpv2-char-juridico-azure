from typing import List, Dict
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.documents import Document
from langchain_openai import AzureChatOpenAI
from langchain.schema import SystemMessage, HumanMessage, AIMessage
from langchain.memory import ConversationBufferWindowMemory
from .search_retriever import AzureHybridSearchRetriever
from .config import AZURE_OPENAI_CHAT_DEPLOYMENT, AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY, USE_COSMOS_DB, AZURE_OPENAI_CLASSIFICATION_DEPLOYMENT
from .cosmos_manager import CosmosDBManager

# CLAVE: Diccionario para almacenar la memoria en RAM (fallback)
session_memories: Dict[str, ConversationBufferWindowMemory] = {}

# Instancia global de Cosmos DB Manager
cosmos_db_manager = CosmosDBManager()

def get_session_memory(session_id: str) -> ConversationBufferWindowMemory:
    """Devuelve o crea una nueva memoria de chat para el ID de sesión."""
    if session_id not in session_memories:
        print(f"🔧 Creando nueva memoria en RAM para sesión: {session_id}")
        session_memories[session_id] = ConversationBufferWindowMemory(
            k=5, 
            memory_key="chat_history", 
            return_messages=True
        )
    return session_memories[session_id]

class RAGService:
    def __init__(self):
        self.retriever = AzureHybridSearchRetriever()
        
        # LLM principal para respuestas
        self.llm = AzureChatOpenAI(
            azure_deployment=AZURE_OPENAI_CHAT_DEPLOYMENT,
            openai_api_version="2024-02-01",
            azure_endpoint=AZURE_OPENAI_ENDPOINT,
            openai_api_key=AZURE_OPENAI_API_KEY,
            temperature=0.1
        )
        
        # LLM más pequeño para clasificación (opcional)
        self.classification_llm = AzureChatOpenAI(
            azure_deployment=AZURE_OPENAI_CLASSIFICATION_DEPLOYMENT,
            openai_api_version="2024-02-01",
            azure_endpoint=AZURE_OPENAI_ENDPOINT,
            openai_api_key=AZURE_OPENAI_API_KEY,
            temperature=0.0  # Temperatura más baja para clasificación
        )
        
        self.prompt = ChatPromptTemplate.from_messages([
            SystemMessage(
                content=(
                    "Eres un asistente legal experto en dictámenes de la Contraloría General de la República. "
                    "Responde a la pregunta basándote **únicamente** en el contexto extraído. "
                    "Si no puedes encontrar la respuesta en el contexto, indica que la información no está disponible. "
                    "Cita las fuentes relevantes al final de la respuesta, haciendo referencia al 'numero_dictamen'. "
                    "Contexto recuperado: {context}"
                )
            ),
            MessagesPlaceholder(variable_name="chat_history"), 
            ("human", "{query}"),
        ])
        
        # Prompt para conversaciones generales (sin búsqueda)
        self.conversational_prompt = ChatPromptTemplate.from_messages([
            SystemMessage(
                content=(
                    "Eres un asistente especializado en dictámenes de la Contraloría General de la República de Chile. "
                    "Tu función es responder preguntas generales sobre la CGR y sus dictámenes usando tus conocimientos generales. "
                    "\n\nInstrucciones específicas:"
                    "\n- Para preguntas como '¿Qué es un dictamen CGR?', explica el concepto general de dictamen en el contexto de la CGR"
                    "\n- Para preguntas sobre la función de la CGR, explica su rol como órgano contralor del Estado"
                    "\n- Para preguntas sobre tipos de dictámenes, menciona las categorías principales (preventivos, reparos, etc.)"
                    "\n- Siempre mantén un tono institucional pero accesible"
                    "\n- Si la pregunta es muy específica sobre un caso particular, sugiere que se formule de manera más específica"
                    "\n- Enfócate siempre en el contexto de la Contraloría General de la República de Chile"
                )
            ),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{query}"),
        ])

    def _needs_search(self, query: str, session_id: str) -> bool:
        """
        Determina si la consulta requiere búsqueda de información usando un LLM pequeño
        para clasificación de intención, considerando el historial de conversación.
        
        Returns:
            True si necesita búsqueda específica, False si es conversacional o general
        """
        try:
            # Cargar historial para el contexto
            if cosmos_db_manager.enabled:
                history_messages = self._load_history_from_cosmos(session_id, limit=5)
            else:
                memory = get_session_memory(session_id)
                history_messages = memory.load_memory_variables({})['chat_history']
            
            # Palabras clave como contexto para el LLM clasificador
            conversational_keywords = [
                'hola', 'hello', 'hi', 'buenos días', 'buenas tardes', 'buenas noches',
                'chao', 'adiós', 'hasta luego', 'nos vemos', 'bye',
                'cómo estás', 'como estas', 'qué tal', 'que tal',
                'gracias', 'muchas gracias', 'ok', 'vale', 'entendido',
                'quién eres', 'quien eres', 'qué haces', 'que haces',
                'ayuda', 'help'
            ]
            
            general_cgr_keywords = [
                'qué es un dictamen', 'que es un dictamen', 'qué es dictamen', 'que es dictamen',
                'qué es la contraloría', 'que es la contraloria', 'qué es cgr', 'que es cgr',
                'qué hace la contraloría', 'que hace la contraloria', 'función de la contraloría',
                'función de la contraloria', 'para qué sirve la contraloría', 'para que sirve la contraloria',
                'qué es contraloría general', 'que es contraloria general', 'definición de dictamen',
                'definicion de dictamen', 'concepto de dictamen', 'significado de dictamen',
                'qué significa dictamen', 'que significa dictamen', 'tipos de dictamen',
                'clases de dictamen', 'categorías de dictamen', 'categorias de dictamen'
            ]
            
            specific_search_keywords = [
                'caso específico', 'caso especifico', 'ejemplo concreto',
                'dictamen número', 'dictamen numero',
                'normativa específica',
                'normativa especifica', 'artículo específico', 'articulo especifico',
                'busca información sobre', 'encuentra información', 'consulta específica',
                'consulta especifica', 'documento específico', 'documento especifico',
                'dictamen de fecha',
                'normativa de', 'reglamento de', 'ley de'
            ]
            
            specific_legal_keywords = [
                'cuáles son los dictámenes de la ley', 'cuales son los dictamenes de la ley',
                'dictámenes de la ley', 'dictamenes de la ley', 'ley número', 'ley numero',
                'últimos dictámenes de', 'ultimos dictamenes de', 'dictámenes más recientes',
                'dictamenes mas recientes', 'dictámenes asociados a', 'dictamenes asociados a',
                'concepto jurídico', 'concepto juridico', 'ley karin', 'licencias médicas',
                'licencias medicas', 'contratación pública', 'contratacion publica',
                'compras públicas', 'compras publicas', 'normativa de', 'reglamento de',
                'cuáles son los dictámenes', 'cuales son los dictamenes', 'listado de dictámenes',
                'listado de dictamenes', 'dictámenes sobre', 'dictamenes sobre'
            ]
            
            # Prompt para el LLM clasificador con historial
            classification_prompt = ChatPromptTemplate.from_messages([
                SystemMessage(
                    content=(
                        "Eres un clasificador de intenciones especializado en consultas sobre dictámenes de la Contraloría General de la República de Chile. "
                        "Tu tarea es determinar si una consulta requiere búsqueda específica en la base de conocimiento o puede responderse con conocimientos generales. "
                        "\n\nRevisa toda la conversación y la consulta del usuario y determina si la pregunta del usuario ya fue respondida o no: "
                        "\n\nSi la pregunta ya fue respondida en la conversación, se refiere a un saludo, responde como una conversación general, pero vuelve a insistir en qué puedes ayudar sobre dictámenes. "
                        "Si la pregunta implica **SUMAR** o **contar** dictámenes o conceptos sobre los dictámenes, responde que no puedes realizar estas operaciones, sólo búsqueda semántica. "
                        "Si la pregunta no fue respondida previamente, responde lo mismo que antes. No importa si sabes cómo responder la pregunta con tu propio conocimiento; simplemente verifica si la pregunta específica ya fue respondida. "
                        "NO JUZGUES EN BASE A TU CONOCIMIENTO ACTUAL. Cualquier cosa que no haya sido respondida previamente debe responderse con la base de datos. "
                        "\n\nCategorías de clasificación:"
                        "\n1. CONVERSACIONAL: Saludos, despedidas, preguntas sobre el asistente, preguntas ya respondidas"
                        "\n2. GENERAL_CGR: Preguntas conceptuales sobre la CGR, definiciones, funciones generales"
                        "\n3. ESPECIFICA: Consultas que requieren información específica de dictámenes, preguntas no respondidas previamente"
                        "\n4. LEGAL_LIST: Consultas sobre listado de dictámenes asociados a leyes específicas o conceptos jurídicos (ej: 'cuáles son los dictámenes de la ley X', 'últimos dictámenes sobre licencias médicas')"
                        "\n\nPalabras clave de referencia:"
                        f"\n- Conversacional: {', '.join(conversational_keywords[:10])}..."
                        f"\n- General CGR: {', '.join(general_cgr_keywords[:10])}..."
                        f"\n- Específica: {', '.join(specific_search_keywords[:10])}..."
                        f"\n- Legal List: {', '.join(specific_legal_keywords[:10])}..."
                        "\n\nResponde ÚNICAMENTE con una de estas opciones: CONVERSACIONAL, GENERAL_CGR, ESPECIFICA, o LEGAL_LIST"
                    )
                ),
                MessagesPlaceholder(variable_name="chat_history"),
                ("human", f"# User question:\n# user:\n{query}")
            ])
            
            # Usar un modelo más pequeño para clasificación
            classification_llm = self.classification_llm
            
            # Clasificar la consulta con historial
            formatted_prompt = classification_prompt.format_messages(
                chat_history=history_messages,
                query=query
            )
            classification_result = classification_llm.invoke(formatted_prompt).content.strip().upper()
            
            print(f"🤖 Clasificación LLM para '{query}': {classification_result}")
            
            # Determinar si necesita búsqueda basado en la clasificación
            if classification_result == "CONVERSACIONAL":
                print(f"🗣️ Consulta conversacional detectada: '{query}' - No se requiere búsqueda")
                return False
            elif classification_result == "GENERAL_CGR":
                print(f"📚 Pregunta general sobre CGR detectada: '{query}' - Usando conocimientos generales del LLM")
                return False
            elif classification_result == "LEGAL_LIST":
                print(f"📋 Consulta de listado legal detectada: '{query}' - Búsqueda especializada")
                return True
            elif classification_result == "ESPECIFICA":
                print(f"🔍 Consulta específica detectada: '{query}' - Se requiere búsqueda")
                return True
            else:
                # Fallback: si el LLM no responde correctamente, usar lógica de respaldo
                print(f"⚠️ Clasificación inesperada '{classification_result}' para '{query}' - Usando lógica de respaldo")
                return self._fallback_classification(query)
                
        except Exception as e:
            print(f"⚠️ Error en clasificación LLM para '{query}': {e} - Usando lógica de respaldo")
            return self._fallback_classification(query)
    
    def _detect_search_type(self, query: str) -> str:
        """
        Detecta el tipo específico de búsqueda requerida.
        """
        legal_list_indicators = [
            'cuáles son los dictámenes', 'cuales son los dictamenes',
            'últimos dictámenes', 'ultimos dictamenes', 'dictámenes más recientes',
            'dictamenes mas recientes', 'dictámenes de la ley', 'dictamenes de la ley',
            'ley número', 'ley numero', 'concepto jurídico', 'concepto juridico',
            'listado de dictámenes', 'listado de dictamenes', 'dictámenes sobre',
            'dictamenes sobre', 'dictámenes asociados a', 'dictamenes asociados a'
        ]
        
        query_lower = query.lower()
        for indicator in legal_list_indicators:
            if indicator in query_lower:
                return "LEGAL_LIST"
        
        return "STANDARD"
    
    def _generate_legal_list_table(self, documents: List[Document], query: str) -> str:
        """
        Genera una tabla estructurada con los dictámenes encontrados.
        """
        table_rows = []
        
        for i, doc in enumerate(documents, 1):
            metadata = doc.metadata
            
            # Formatear fecha
            fecha = metadata.get("fecha", "N/A")
            if fecha != "N/A" and isinstance(fecha, str):
                try:
                    from datetime import datetime
                    fecha_obj = datetime.fromisoformat(fecha.replace('Z', '+00:00'))
                    fecha_formatted = fecha_obj.strftime("%d/%m/%Y")
                except:
                    fecha_formatted = fecha
            else:
                fecha_formatted = metadata.get("ano", "N/A")
            
            # Truncar resumen si es muy largo
            resumen = metadata.get("resumen", "Resumen no disponible")
            if len(resumen) > 150:
                resumen = resumen[:147] + "..."
            
            # Formatear leyes aplicadas
            leyes = metadata.get("leyes_aplicadas", "N/A")
            if len(leyes) > 100:
                leyes = leyes[:97] + "..."
            
            # Formatear dictámenes aplicados
            dictamenes = metadata.get("dictamenes_aplicados", "N/A")
            if len(dictamenes) > 100:
                dictamenes = dictamenes[:97] + "..."
            
            # Crear fila de tabla
            row = f"""
**{i}. Dictamen {metadata.get('numero_dictamen', 'N/A')}**

| Campo | Información |
|-------|-------------|
| **Número** | {metadata.get('numero_dictamen', 'N/A')} |
| **Año** | {metadata.get('ano', 'N/A')} |
| **Fecha** | {fecha_formatted} |
| **Resumen** | {resumen} |
| **Leyes Aplicadas** | {leyes} |
| **Dictámenes Aplicados** | {dictamenes} |
| **URL** | [{metadata.get('url', 'N/A')}]({metadata.get('url', '#')}) |

---
"""
            table_rows.append(row)
        
        # Crear respuesta completa
        response = f"""
## 📋 Dictámenes Encontrados

Basado en tu consulta: *"{query}"*

Se encontraron {len(documents)} dictámenes relacionados:

{''.join(table_rows)}

**Nota:** Estos son los dictámenes más recientes relacionados con tu consulta. Para información más detallada, puedes acceder directamente a cada dictamen usando los enlaces proporcionados.
"""
        
        return response
    
    def _fallback_classification(self, query: str) -> bool:
        """
        Lógica de respaldo para clasificación cuando el LLM falla.
        """
        query_lower = query.lower().strip()
        
        # Patrones conversacionales simples
        conversational_patterns = ['hola', 'hello', 'hi', 'gracias', 'chao', 'adiós']
        if any(pattern in query_lower for pattern in conversational_patterns) and len(query_lower) < 30:
            print(f"🗣️ Fallback: Consulta conversacional detectada: '{query}' - No se requiere búsqueda")
            return False
        
        # Patrones generales sobre CGR
        general_patterns = ['qué es un dictamen', 'qué es la contraloría', 'qué hace la contraloría']
        if any(pattern in query_lower for pattern in general_patterns):
            print(f"📚 Fallback: Pregunta general sobre CGR detectada: '{query}' - Usando conocimientos generales del LLM")
            return False
        
        # Por defecto, hacer búsqueda
        print(f"🔍 Fallback: Consulta genérica: '{query}' - Se requiere búsqueda (por defecto)")
        return True
    
    def _rewrite_query(self, original_query: str, history_messages: List) -> str:
        """
        Reescribe la consulta del usuario usando el LLM y el historial de conversación
        para hacerla standalone y optimizada para la búsqueda.
        """
        # Si no hay historial, devolver la query original
        if not history_messages:
            print(f"📝 Sin historial previo. Usando query original: '{original_query}'")
            return original_query
        
        # Prompt para reescribir la query
        rewrite_prompt = ChatPromptTemplate.from_messages([
            SystemMessage(
                content=(
                    "Eres un asistente experto en reformular preguntas sobre dictámenes de la Contraloría General de la República. "
                    "Tu tarea es reescribir la pregunta del usuario para que sea una consulta standalone "
                    "(que se entienda sin contexto previo) y optimizada para búsqueda semántica. "
                    "\n\nInstrucciones:"
                    "\n- Incorpora el contexto relevante del historial de conversación"
                    "\n- Haz que la pregunta sea clara y específica"
                    "\n- Mantén los términos legales y técnicos importantes"
                    "\n- Si la pregunta se refiere a algo mencionado anteriormente, inclúyelo explícitamente"
                    "\n- Responde SOLO con la pregunta reescrita, sin explicaciones adicionales"
                )
            ),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "Pregunta original del usuario: {original_query}\n\nPregunta reescrita:")
        ])
        
        try:
            formatted_prompt = rewrite_prompt.format_messages(
                chat_history=history_messages,
                original_query=original_query
            )
            
            rewritten_query = self.llm.invoke(formatted_prompt).content.strip()
            print(f"📝 Query Original: '{original_query}'")
            print(f"✨ Query Reescrita: '{rewritten_query}'")
            
            return rewritten_query
        
        except Exception as e:
            print(f"⚠️ Error al reescribir query: {e}. Usando query original.")
            return original_query

    def generate_response(self, session_id: str, query: str, use_two_vectors: bool) -> Dict:
        
        # Cargar historial
        if cosmos_db_manager.enabled:
            history_messages = self._load_history_from_cosmos(session_id)
        else:
            memory = get_session_memory(session_id)
            history_messages = memory.load_memory_variables({})['chat_history']
        
        # 1. Detectar si la consulta necesita búsqueda
        needs_search = self._needs_search(query, session_id)
        
        if not needs_search:
            # FLUJO CONVERSACIONAL: Sin búsqueda, sin fuentes
            print(f"💬 Respuesta conversacional directa para: '{query}'")
            
            formatted_prompt = self.conversational_prompt.format_messages(
                chat_history=history_messages,
                query=query
            )
            
            llm_response = self.llm.invoke(formatted_prompt).content
            
            # Guardar en historial (sin fuentes)
            if cosmos_db_manager.enabled:
                cosmos_db_manager.save_message(session_id, "user", query)
                cosmos_db_manager.save_message(session_id, "assistant", llm_response, [])
            else:
                memory = get_session_memory(session_id)
                memory.save_context({"input": query}, {"output": llm_response})
            
            return {
                "response": llm_response,
                "sources": []  # Sin fuentes para consultas conversacionales
            }
        
        # 2. Detectar tipo de búsqueda específica
        search_type = self._detect_search_type(query)
        
        if search_type == "LEGAL_LIST":
            # FLUJO ESPECIALIZADO: Listado de dictámenes por ley/concepto
            print(f"📋 Búsqueda especializada para listado de dictámenes: '{query}'")
            
            # Realizar búsqueda especializada
            documents = self.search_retriever.run_legal_list_search(query, limit=3)
            
            if not documents:
                llm_response = "No se encontraron dictámenes relacionados con tu consulta."
                
                # Guardar en historial
                if cosmos_db_manager.enabled:
                    cosmos_db_manager.save_message(session_id, "user", query)
                    cosmos_db_manager.save_message(session_id, "assistant", llm_response, [])
                else:
                    memory = get_session_memory(session_id)
                    memory.save_context({"input": query}, {"output": llm_response})
                
                return {
                    "response": llm_response,
                    "sources": []
                }
            
            # Generar tabla estructurada
            table_response = self._generate_legal_list_table(documents, query)
            
            # Guardar en historial
            sources = [{"numero_dictamen": doc.metadata.get("numero_dictamen"), 
                       "url": doc.metadata.get("url")} for doc in documents]
            
            if cosmos_db_manager.enabled:
                cosmos_db_manager.save_message(session_id, "user", query)
                cosmos_db_manager.save_message(session_id, "assistant", table_response, sources)
            else:
                memory = get_session_memory(session_id)
                memory.save_context({"input": query}, {"output": table_response})
            
            return {
                "response": table_response,
                "sources": sources
            }
        
        # FLUJO RAG ESTÁNDAR: Para consultas específicas sobre dictámenes
        print(f"🔍 Respuesta con búsqueda RAG estándar para: '{query}'")
        
        # 3. Query Rewriting: Reescribir la consulta usando el historial
        rewritten_query = self._rewrite_query(query, history_messages)
        
        # 4. Búsqueda de Contexto (usando la query reescrita)
        retrieved_documents = self.retriever.run_hybrid_search(
            query_text=rewritten_query, 
            use_two_vectors=use_two_vectors
        )
        
        # 4. Formato del Contexto
        context_text = "\n---\n".join([f"Fuente: {doc.metadata.get('source', 'N/A')}\nContenido: {doc.page_content}" 
                                      for doc in retrieved_documents])
        
        # 5. Formatear Prompt con el historial (usando la query original para la respuesta)
        formatted_prompt = self.prompt.format_messages(
            context=context_text,
            chat_history=history_messages, 
            query=query  # Usamos la query original para que el LLM responda a lo que el usuario preguntó
        )
        
        # 6. Llamada al LLM
        llm_response = self.llm.invoke(formatted_prompt).content
        
        # 7. Formato de las fuentes
        sources_list = [{
            "source": doc.metadata.get("source", "N/A"),
            "url": doc.metadata.get("url", ""),
            "score": doc.metadata.get("score", 0.0)
        } for doc in retrieved_documents]
        
        # 8. Guardar la interacción
        if cosmos_db_manager.enabled:
            cosmos_db_manager.save_message(session_id, "user", query)
            cosmos_db_manager.save_message(session_id, "assistant", llm_response, sources_list)
        else:
            memory = get_session_memory(session_id)
            memory.save_context({"input": query}, {"output": llm_response})

        return {
            "response": llm_response,
            "sources": sources_list
        }
    
    def _load_history_from_cosmos(self, session_id: str, limit: int = 10) -> List:
        """Carga el historial desde Cosmos DB y lo convierte al formato LangChain."""
        cosmos_history = cosmos_db_manager.get_chat_history(session_id, limit=limit)
        
        langchain_messages = []
        for msg in cosmos_history:
            if msg['role'] == 'user':
                langchain_messages.append(HumanMessage(content=msg['content']))
            elif msg['role'] == 'assistant':
                langchain_messages.append(AIMessage(content=msg['content']))
        
        return langchain_messages
    
    def get_formatted_history(self, session_id: str) -> List[Dict]:
        """Convierte el historial a un formato JSON para el Frontend."""
        if cosmos_db_manager.enabled:
            # Obtener desde Cosmos DB
            cosmos_history = cosmos_db_manager.get_chat_history(session_id)
            formatted_history = []
            
            for msg in cosmos_history:
                formatted_history.append({
                    'role': msg['role'],
                    'content': msg['content'],
                    'sources': msg.get('sources', [])
                })
            
            return formatted_history
        else:
            # Obtener desde memoria RAM
            memory = get_session_memory(session_id)
            history_messages = memory.load_memory_variables({})['chat_history']
            
            formatted_history = []
            for msg in history_messages:
                role = 'user' if msg.type == 'human' else 'assistant'
                formatted_history.append({'role': role, 'content': msg.content, 'sources': []}) 
                
            return formatted_history
