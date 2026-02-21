// Main App Component with Error Boundary and Voice Provider

import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { Component, type ReactNode } from 'react';
import AppNavbar from './components/Navbar';
import Dashboard from './pages/Dashboard';
import Documents from './pages/Documents';
import DocumentChat from './pages/DocumentChat';
import { NotificationProvider } from './context/NotificationContext';
import { VoiceProvider } from './context/VoiceContext';
import './index.css';

// Error Boundary — catches rendering errors so the app never shows a white screen
interface ErrorBoundaryProps {
  children: ReactNode;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('App Error:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="d-flex flex-column align-items-center justify-content-center min-vh-100"
          style={{ background: 'var(--bg-primary, #0a0a1a)', color: 'white', padding: '2rem' }}>
          <div style={{ fontSize: '4rem', marginBottom: '1rem' }}>⚠️</div>
          <h2>Something went wrong</h2>
          <p className="text-secondary text-center" style={{ maxWidth: '500px' }}>
            An unexpected error occurred. Please refresh the page to continue.
          </p>
          <button
            className="btn btn-gradient mt-3"
            style={{
              background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
              border: 'none',
              color: 'white',
              padding: '10px 24px',
              borderRadius: '8px',
              cursor: 'pointer',
            }}
            onClick={() => {
              this.setState({ hasError: false, error: null });
              window.location.href = '/';
            }}
          >
            🔄 Refresh App
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}

function App() {
  return (
    <ErrorBoundary>
      <BrowserRouter>
        <VoiceProvider>
          <NotificationProvider>
            <div className="d-flex flex-column min-vh-100">
              <AppNavbar />
              <main className="flex-grow-1">
                <Routes>
                  <Route path="/" element={<Dashboard />} />
                  <Route path="/documents" element={<Documents />} />
                  <Route path="/chat/:docId" element={<DocumentChat />} />
                </Routes>
              </main>
            </div>
          </NotificationProvider>
        </VoiceProvider>
      </BrowserRouter>
    </ErrorBoundary>
  );
}

export default App;
