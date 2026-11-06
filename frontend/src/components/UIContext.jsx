import { createContext, useCallback, useContext, useRef, useState } from 'react'
import { CheckCircle2, Info, X } from 'lucide-react'
import { setApiLanguage } from '../api/client'

const UIContext = createContext(null)

export function UIProvider({ children }) {
  const [toasts, setToasts] = useState([])
  const [language, setLanguageState] = useState('English')
  const idRef = useRef(0)

  // Keep the API's Accept-Language header in sync with the UI language.
  const setLanguage = useCallback(l => {
    setLanguageState(l)
    setApiLanguage(l === 'English' ? 'en' : 'ur')
  }, [])

  const toast = useCallback((message, type = 'success') => {
    const id = ++idRef.current
    setToasts(t => [...t, { id, message, type }])
    setTimeout(() => setToasts(t => t.filter(x => x.id !== id)), 3200)
  }, [])

  const dismiss = id => setToasts(t => t.filter(x => x.id !== id))

  return (
    <UIContext.Provider value={{ toast, language, setLanguage }}>
      {children}
      <div className="toast-stack" aria-live="polite">
        {toasts.map(t => (
          <div key={t.id} className={`toast toast-${t.type}`}>
            {t.type === 'success' ? <CheckCircle2 size={18} /> : <Info size={18} />}
            <span>{t.message}</span>
            <button className="icon-btn-plain" onClick={() => dismiss(t.id)} aria-label="Dismiss"><X size={15} /></button>
          </div>
        ))}
      </div>
    </UIContext.Provider>
  )
}

export const useUI = () => useContext(UIContext)
