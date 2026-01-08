// Main App Component

import { BrowserRouter, Routes, Route } from 'react-router-dom';
import AppNavbar from './components/Navbar';
import Dashboard from './pages/Dashboard';
import Documents from './pages/Documents';
import GlobalChat from './pages/GlobalChat';
import DocumentChat from './pages/DocumentChat';
import { NotificationProvider } from './context/NotificationContext';
import './index.css';

function App() {
  return (
    <BrowserRouter>
      <NotificationProvider>
        <div className="d-flex flex-column min-vh-100">
          <AppNavbar />
          <main className="flex-grow-1">
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/documents" element={<Documents />} />
              <Route path="/chat" element={<GlobalChat />} />
              <Route path="/chat/:docId" element={<DocumentChat />} />
            </Routes>
          </main>
        </div>
      </NotificationProvider>
    </BrowserRouter>
  );
}

export default App;

