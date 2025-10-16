import React from 'react';
import ReactDOM from 'react-dom/client';
import './index.css';
import ChatContainer from './ChatContainer'; 
import { initializeIcons } from '@fluentui/react';

// Inicializa los iconos de FluentUI
initializeIcons(); 

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    {/* Monta el componente principal de chat */}
    <ChatContainer /> 
  </React.StrictMode>
);
