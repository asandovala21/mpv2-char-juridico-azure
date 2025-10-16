from quart import Quart, request, jsonify
from quart_cors import cors
import uuid
from .rag_service import RAGService

app = Quart(__name__)
app = cors(app, allow_origin="*") 

rag_service = RAGService()
# Nota: CosmosDBManager se inicializa dentro de RAGService 

@app.route("/chat", methods=["POST"])
async def chat_handler():
    """
    Maneja las solicitudes de chat, usando la memoria en RAM para el historial.
    """
    try:
        data = await request.get_json()
        user_query = data.get("query", "")
        session_id = data.get("session_id", str(uuid.uuid4()))
        use_two_vectors = data.get("use_two_vectors", False) 

        if not user_query:
            return jsonify({"error": "Consulta vacía", "session_id": session_id}), 400

        print(f"[{session_id}] Nueva consulta: '{user_query[:50]}...'. Doble Vector: {use_two_vectors}")
        
        # 1. Generar respuesta RAG (guarda la conversación en memoria RAM)
        result = rag_service.generate_response(
            session_id=session_id, 
            query=user_query, 
            use_two_vectors=use_two_vectors
        )
        
        # 2. Obtener el historial completo actualizado desde el servicio RAG
        updated_history = rag_service.get_formatted_history(session_id)
        
        # CLAVE: Asegurarse de que el último mensaje del historial (el del asistente)
        # tenga las fuentes adjuntas, ya que el servicio RAG solo devuelve el texto y las fuentes.
        if updated_history and updated_history[-1]['role'] == 'assistant':
             updated_history[-1]['sources'] = result['sources']


        # 3. Enviar respuesta final
        return jsonify({
            "response": result['response'],
            "sources": result['sources'],
            "session_id": session_id,
            "history": updated_history
        })
    
    except Exception as e:
        print(f"Error fatal en el chat_handler: {e}")
        return jsonify({
            "error": f"Error interno del servidor: {e}", 
            "session_id": session_id,
            "history": rag_service.get_formatted_history(session_id) if 'rag_service' in locals() else []
        }), 500
