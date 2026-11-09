import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import App from './App';
import { applyTheme, initialTheme } from './hooks/useTheme';
import './styles/index.css';

applyTheme(initialTheme()); // before the first render: no light/dark flash

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
