import React, { useState, useEffect } from 'react';
import { TextField, Icon } from '@fluentui/react';
import './ChatContainer.css';
import config from './config';

// Usar la configuración centralizada
const API_URL = config.CHAT_ENDPOINT;

const LoadingSpinner = () => (
    <div className="loading-spinner">
        <div className="spinner-circle"></div>
    </div>
);

const MessageBubble = ({ msg }) => (
    <div className={`message-bubble ${msg.role}`}>
        <div className="message-content">
            <div className="message-text">{msg.content}</div>
            {msg.role === 'assistant' && msg.sources && msg.sources.length > 0 && (
                <div className="message-sources">
                    <div className="sources-title">Fuentes:</div>
                {[...new Map(msg.sources.map(item => [item['source'], item])).values()].slice(0, 3).map((source, idx) => (
                        <div key={idx} className="source-item">
                            <span className="source-title">{source.source}</span>
                            <span className="source-score">({source.score.toFixed(2)})</span>
                        </div>
                    ))}
                </div>
            )}
        </div>
    </div>
);

const SuggestedQuestion = ({ question, onClick }) => (
    <button className="suggested-question" onClick={() => onClick(question)}>
        <div className="question-icon">
            <Icon iconName="Message" />
        </div>
        <p className="question-text">{question}</p>
    </button>
);

const InfoCard = ({ icon, title, description, color }) => (
    <div className="info-card">
        <div className={`info-icon ${color}`}>
            <Icon iconName={icon} />
        </div>
        <h4 className="info-title">{title}</h4>
        <p className="info-description">{description}</p>
    </div>
);

export default function ChatContainer() {
    const [sidebarOpen, setSidebarOpen] = useState(true);
    const [messages, setMessages] = useState([]);
    const [inputValue, setInputValue] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [sessionID, setSessionID] = useState(() => localStorage.getItem('sessionID') || new Date().getTime().toString());

    const suggestedQuestions = [
        "¿Qué es un dictamen CGR?",
        "Consultar sobre licitaciones públicas",
        "Información sobre adquisiciones",
        "Normativa de recursos públicos"
    ];

    useEffect(() => {
        localStorage.setItem('sessionID', sessionID);
    }, [sessionID]);

    const handleSendMessage = async () => {
        if (!inputValue.trim() || isLoading) return;

        const userMessage = { content: inputValue, role: 'user' };
        setMessages(prev => [...prev, userMessage]);
        setInputValue('');
        setIsLoading(true);

        try {
            const response = await fetch(API_URL, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    query: inputValue, 
                    use_two_vectors: true,
                    session_id: sessionID
                })
            });

            if (!response.ok) throw new Error('Error en la respuesta');

            const data = await response.json();
            const botMessage = { 
                content: data.response, 
                role: 'assistant',
                sources: data.sources || []
            };
            setMessages(prev => [...prev, botMessage]);
        } catch (error) {
            console.error('Error:', error);
            const errorMessage = { 
                content: 'Lo siento, hubo un error al procesar tu consulta. Por favor, inténtalo de nuevo.', 
                role: 'assistant' 
            };
            setMessages(prev => [...prev, errorMessage]);
        } finally {
            setIsLoading(false);
        }
    };
    
    const handleSuggestedClick = (question) => {
        setInputValue(question);
    };

    return (
        <div className="chat-container">
            {/* Sidebar */}
            <div className={`sidebar ${sidebarOpen ? 'open' : 'collapsed'}`}>
                <div className="sidebar-header">
                    <div className="logo-container">
                        <img 
                            src="/images/logocgr.svg" 
                            alt="Logo CGR" 
                            className="logo-cgr"
                        />
                    </div>
                    <div className="sidebar-title">
                        <h3 className="main-title">JURISPRUDENCIA</h3>
                        <p className="sub-title">Asistente IA</p>
                    </div>
                </div>

                <div className="sidebar-menu">
                    <button className="menu-item">
                        <Icon iconName="Add" />
                        <span>Nuevo chat</span>
                    </button>
                    <button className="menu-item">
                        <Icon iconName="Clock" />
                        <span>Historial</span>
                    </button>
                    <button className="menu-item">
                        <Icon iconName="TextDocument" />
                        <span>Glosario</span>
                    </button>
                    <button className="menu-item">
                        <Icon iconName="Help" />
                        <span>Soporte</span>
                    </button>
                </div>

                <div className="sidebar-footer">
                    <div className="footer-text">
                        <p className="footer-title">CONTRALORÍA GENERAL</p>
                        <p className="footer-subtitle">Por el cuidado y buen uso</p>
                        <p className="footer-subtitle">de los recursos públicos</p>
                    </div>
                </div>
            </div>

            {/* Main Content */}
            <div className="main-content">
                {/* Header */}
                <header className="chat-header">
                    <div className="header-left">
                        <button 
                            className="menu-toggle"
                            onClick={() => setSidebarOpen(!sidebarOpen)}
                        >
                            <Icon iconName="GlobalNavButton" />
                        </button>
                        <img 
                            src="/images/logocgr.svg" 
                            alt="Logo CGR"
                            className="header-logo"
                        />
                        <div className="header-text">
                            <h1>Asistente de Dictámenes CGR</h1>
                            <p>Contraloría General de la República de Chile</p>
                        </div>
                    </div>
                    <button className="refresh-button">
                        Actualizar
                    </button>
                </header>

                {/* Chat Area */}
                <div className="chat-area">
                    <div className="chat-messages">
                        {messages.length === 0 ? (
                            <div className="welcome-container">
                                {/* Welcome Card */}
                                <div className="welcome-card">
                                    <div className="welcome-icon">
                                        <Icon iconName="Lightbulb" />
                                    </div>
                                    <h2 className="welcome-title">¡Hola! Soy tu asistente de dictámenes</h2>
                                    <p className="welcome-description">
                                        Estoy aquí para ayudarte con consultas sobre dictámenes, normativas y procedimientos de la Contraloría General de la República de Chile.
                                    </p>
                                </div>

                                {/* Suggested Questions */}
                                <div className="suggested-section">
                                    <h3 className="suggested-title">Consultas frecuentes</h3>
                                    <div className="suggested-grid">
                                        {suggestedQuestions.map((question, idx) => (
                                            <SuggestedQuestion 
                                                key={idx} 
                                                question={question} 
                                                onClick={handleSuggestedClick}
                                            />
                                        ))}
                                    </div>
                                </div>

                                {/* Info Cards */}
                                <div className="info-grid">
                                    <InfoCard 
                                        icon="TextDocument" 
                                        title="Base de conocimiento" 
                                        description="Acceso a miles de dictámenes y resoluciones"
                                        color="pink"
                                    />
                                    <InfoCard 
                                        icon="Lightbulb" 
                                        title="Inteligencia Artificial" 
                                        description="Respuestas precisas y contextualizadas"
                                        color="teal"
                                    />
                                    <InfoCard 
                                        icon="Clock" 
                                        title="Disponible 24/7" 
                                        description="Consulta cuando lo necesites"
                                        color="gray"
                                    />
                                </div>
                            </div>
                        ) : (
                            <div className="messages-container">
                                {messages.map((msg, idx) => (
                                    <MessageBubble key={idx} msg={msg} />
                                ))}
                                {isLoading && (
                                    <div className="message-bubble assistant">
                                        <div className="message-content">
                                            <LoadingSpinner />
                                            <span className="loading-text">Procesando tu consulta...</span>
                                        </div>
                                    </div>
                                )}
                            </div>
                        )}
                    </div>
                </div>

                {/* Input Area */}
                <div className="input-section">
                    <div className="input-container">
                        <div className="input-field">
                <TextField
                                multiline
                                value={inputValue}
                                onChange={(e) => setInputValue(e.target.value)}
                                placeholder="Escribe tu consulta aquí..."
                                styles={{
                                    root: { width: '100%' },
                                    field: { 
                                        minHeight: '56px',
                                        maxHeight: '200px',
                                        fontSize: '14px',
                                        padding: '16px 20px',
                                        border: '2px solid #E2E8F0',
                                        borderRadius: '16px',
                                        backgroundColor: '#F8FAFC',
                                        transition: 'border-color 0.2s'
                                    },
                                    fieldGroup: { 
                                        border: 'none',
                                        '&:focus-within': {
                                            border: '2px solid #1e3a5f'
                                        }
                                    }
                                }}
                                onKeyPress={(e) => {
                                    if (e.key === 'Enter' && !e.shiftKey) {
                                        e.preventDefault();
                                        handleSendMessage();
                                    }
                                }}
                            />
                        </div>
                        <button
                            className="send-button"
                            onClick={handleSendMessage}
                            disabled={!inputValue.trim() || isLoading}
                        >
                            <Icon iconName="Send" />
                        </button>
                    </div>
                    <p className="input-disclaimer">
                        Este asistente usa IA para proporcionar información. Verifica siempre los datos oficiales.
                    </p>
                </div>
            </div>
        </div>
    );
}