import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import React, { useState, useEffect, lazy, Suspense } from 'react'
import { AuthProvider, useAuth } from '@/contexts/AuthContext'
import ProtectedRoute from '@/components/Auth/ProtectedRoute'
import LoginForm from '@/components/Auth/LoginForm'
import SignUpForm from '@/components/Auth/SignUpForm'
import ForgotPasswordForm from '@/components/Auth/ForgotPasswordForm'
import PasswordResetForm from '@/components/Auth/PasswordResetForm'
import SimpleDashboard from '@/components/SimpleDashboard'
import StringEvaluation from '@/components/StringEvaluation'
import ApplicantManagement from '@/components/ApplicantManagement'
import ApplicationManagement from '@/components/ApplicationManagement'
import ApplicationDetail from '@/components/ApplicationDetail'
import Scoreboard from '@/components/Scoreboard'
// Lazy load chat components to prevent blocking main app
const ChatPanel = lazy(() => import('@/components/ChatPanel'))
const ChatToggle = lazy(() => import('@/components/ChatToggle'))

// Simple auth guard that just hides children when not authenticated (no navigation)
function AuthenticatedOnly({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth()
  if (loading || !user) return null
  return <>{children}</>
}

// Error boundary for chat components
class ChatErrorBoundary extends React.Component<
  { children: React.ReactNode },
  { hasError: boolean }
> {
  constructor(props: { children: React.ReactNode }) {
    super(props)
    this.state = { hasError: false }
  }

  static getDerivedStateFromError() {
    return { hasError: true }
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('Chat component error:', error, errorInfo)
  }

  render() {
    if (this.state.hasError) {
      return null // Don't show anything if chat fails
    }
    return this.props.children
  }
}

function App() {
  const [isChatOpen, setIsChatOpen] = useState(false)
  const [isChatMinimized, setIsChatMinimized] = useState(false)
  const [chatContext, setChatContext] = useState<{
    tld_string?: string;
    current_question?: string;
    application_id?: string;
    page_type?: string;
  }>({})

  // Update chat context based on current route/page
  useEffect(() => {
    const updateChatContext = () => {
      const path = window.location.pathname
      const newContext: typeof chatContext = {}

      // Extract TLD string from evaluation route
      const tldMatch = path.match(/\/evaluation\/([^\/]+)/)
      if (tldMatch) {
        newContext.tld_string = tldMatch[1]
      }

      // Extract application ID from application route
      const appMatch = path.match(/\/applications\/([^\/]+)/)
      if (appMatch) {
        newContext.application_id = appMatch[1]
      }

      // Add page type context
      if (path.includes('/evaluation/')) {
        newContext.page_type = 'evaluation'
      } else if (path.includes('/applications/')) {
        newContext.page_type = 'application'
      } else if (path.includes('/applicants')) {
        newContext.page_type = 'applicants'
      } else if (path.includes('/scoreboard')) {
        newContext.page_type = 'scoreboard'
      } else {
        newContext.page_type = 'dashboard'
      }

      setChatContext(newContext)
    }

    updateChatContext()
    
    // Listen for route changes
    const handlePopState = () => updateChatContext()
    window.addEventListener('popstate', handlePopState)
    
    return () => window.removeEventListener('popstate', handlePopState)
  }, [])

  return (
    <AuthProvider>
      <Router>
        <div className={`transition-all duration-300 ${isChatOpen && !isChatMinimized ? 'mr-96' : isChatOpen ? 'mr-12' : 'mr-0'}`}>
          <Routes>
            {/* Public routes */}
            <Route path="/login" element={<LoginForm />} />
            <Route path="/signup" element={<SignUpForm />} />
            <Route path="/forgot-password" element={<ForgotPasswordForm />} />
            <Route path="/reset-password" element={<PasswordResetForm />} />
            
            {/* Protected routes */}
            <Route path="/" element={
              <ProtectedRoute>
                <SimpleDashboard />
              </ProtectedRoute>
            } />
            <Route path="/evaluation/:tldString" element={
              <ProtectedRoute>
                <StringEvaluation />
              </ProtectedRoute>
            } />
            <Route path="/applicants" element={
              <ProtectedRoute>
                <ApplicantManagement />
              </ProtectedRoute>
            } />
            <Route path="/applications" element={
              <ProtectedRoute>
                <ApplicationManagement />
              </ProtectedRoute>
            } />
            <Route path="/applications/:applicationId" element={
              <ProtectedRoute>
                <ApplicationDetail />
              </ProtectedRoute>
            } />
            <Route path="/scoreboard" element={
              <ProtectedRoute>
                <Scoreboard />
              </ProtectedRoute>
            } />
            {/* Legacy route redirect */}
            <Route path="/applicant" element={
              <ProtectedRoute>
                <ApplicantManagement />
              </ProtectedRoute>
            } />
          </Routes>
        </div>
        
        {/* Chat Components - Only show when authenticated, lazy-loaded and error-isolated */}
        <AuthenticatedOnly>
          <ChatErrorBoundary>
            <Suspense fallback={null}>
              <ChatToggle 
                isOpen={isChatOpen}
                onClick={() => setIsChatOpen(true)}
              />
              <ChatPanel
                isOpen={isChatOpen}
                onClose={() => setIsChatOpen(false)}
                context={chatContext}
                isMinimized={isChatMinimized}
                onMinimizedChange={setIsChatMinimized}
              />
            </Suspense>
          </ChatErrorBoundary>
        </AuthenticatedOnly>
      </Router>
    </AuthProvider>
  )
}

export default App
