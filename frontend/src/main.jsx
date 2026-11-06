import React from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import App from './App'
import { UIProvider } from './components/UIContext'
import { AuthProvider } from './context/AuthContext'
import './styles/base.css'
import './styles/layout.css'
import './styles/public.css'
import './styles/app-pages.css'
import './styles/chat.css'
import './styles/documents.css'
import './styles/vault.css'
import './styles/brief.css'
import './styles/tools.css'
import './styles/emergency.css'
import './styles/marketplace.css'
import './styles/admin.css'
import './styles/community.css'
import './styles/lawyer-portal.css'
import './styles/settings.css'
import './styles/states.css'

createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <BrowserRouter>
      <UIProvider>
        <AuthProvider>
          <App />
        </AuthProvider>
      </UIProvider>
    </BrowserRouter>
  </React.StrictMode>
)
