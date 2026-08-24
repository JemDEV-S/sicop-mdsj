import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import App from './app/App';
// Tipografía institucional del Panel Interno v2 (IBM Plex), auto-hospedada
// (sin llamadas a Google Fonts en runtime). Pesos usados: 400/500/600/700 sans,
// 400/500/600 mono.
import '@fontsource/ibm-plex-sans/400.css';
import '@fontsource/ibm-plex-sans/500.css';
import '@fontsource/ibm-plex-sans/600.css';
import '@fontsource/ibm-plex-sans/700.css';
import '@fontsource/ibm-plex-mono/400.css';
import '@fontsource/ibm-plex-mono/500.css';
import '@fontsource/ibm-plex-mono/600.css';
import './styles/globals.css';

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
