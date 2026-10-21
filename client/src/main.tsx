import React, { StrictMode } from 'react'
import './index.css'
import App from '@/App.tsx'
import { createRoot } from 'react-dom/client'

// Extend HTMLElement to include _reactRoot property
declare global {
  interface HTMLElement {
    _reactRoot?: any
  }
}

// Error boundary component for mobile debugging
class ErrorBoundary extends React.Component<
  { children: React.ReactNode },
  { hasError: boolean; error?: Error }
> {
  constructor(props: { children: React.ReactNode }) {
    super(props)
    this.state = { hasError: false }
  }

  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('React Error Boundary caught an error:', error, errorInfo)
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen flex items-center justify-center bg-gray-50 p-4">
          <div className="bg-white p-6 rounded-lg shadow-lg max-w-md w-full">
            <h2 className="text-lg font-semibold text-red-600 mb-2">Something went wrong</h2>
            <p className="text-gray-600 mb-4">Please refresh the page and try again.</p>
            <button 
              onClick={() => window.location.reload()}
              className="w-full bg-blue-600 text-white py-2 px-4 rounded hover:bg-blue-700"
            >
              Refresh Page
            </button>
            {process.env.NODE_ENV === 'development' && (
              <details className="mt-4">
                <summary className="cursor-pointer text-sm text-gray-500">Error Details</summary>
                <pre className="mt-2 text-xs text-red-500 whitespace-pre-wrap">
                  {this.state.error?.toString()}
                </pre>
              </details>
            )}
          </div>
        </div>
      )
    }

    return this.props.children
  }
}

// Dev console helpers — lazily loaded to avoid import side-effects
if (typeof window !== 'undefined' && import.meta.env.DEV) {
  ;(window as any).devHelpers = async () => {
    const api = await import('@/lib/supabase-api')
    ;(window as any).generateApplicationAnswers = api.generateApplicationAnswers
    ;(window as any).triggerFullApplicationGeneration = api.triggerFullApplicationGeneration
    ;(window as any).createApplications = api.createApplications
    ;(window as any).getTldApplications = api.getTldApplications
    ;(window as any).deleteApplication = api.deleteApplication
    console.log('Dev helpers loaded: generateApplicationAnswers, triggerFullApplicationGeneration, createApplications, getTldApplications, deleteApplication')
  }
}

const rootElement = document.getElementById('root')
if (!rootElement) {
  throw new Error('Root element not found')
}

// Prevent multiple root creation in development
if (!rootElement._reactRoot) {
  const root = createRoot(rootElement)
  rootElement._reactRoot = root
  
  root.render(
    <StrictMode>
      <ErrorBoundary>
        <App />
      </ErrorBoundary>
    </StrictMode>
  )
}
