import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';

export default function Layout({ children }) {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const role = localStorage.getItem('role');
  const navigate = useNavigate();

  const logout = () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('role');
    localStorage.removeItem('tenant_id');
    navigate('/login');
  };

  return (
    <div className="flex h-screen overflow-hidden bg-gray-50 text-gray-800">
      {/* Sidebar */}
      <div
        className={`w-64 bg-gray-900 text-white flex flex-col h-full transition-all duration-300 ease-in-out ${sidebarOpen ? '' : '-ml-64'}`}
      >
        <div className="p-4 border-b border-gray-700">
          <button
            className="w-full flex items-center justify-center gap-2 bg-gray-700 hover:bg-gray-600 text-white py-2 px-4 rounded-md transition-colors"
            onClick={() => navigate('/chat')}
          >
            <i className="fas fa-comments"></i>
            <span>New Chat</span>
          </button>
        </div>

        <div className="flex-1 overflow-y-auto">
          <div className="p-4 border-b border-gray-700">
            <h3 className="text-sm font-semibold text-gray-400 mb-2">Navigation</h3>
            <nav className="space-y-1">
              <Link className="block p-2 rounded hover:bg-gray-800" to="/chat">
                Chat
              </Link>
              <Link className="block p-2 rounded hover:bg-gray-800" to="/files">
                Files
              </Link>
              {(role === 'admin' || role === 'super_admin') && (
                <>
                  <Link className="block p-2 rounded hover:bg-gray-800" to="/tenants">
                    Tenants
                  </Link>
                  <Link className="block p-2 rounded hover:bg-gray-800" to="/users">
                    Users
                  </Link>
                </>
              )}
            </nav>
          </div>

          <div className="p-4">
            <h3 className="text-sm font-semibold text-gray-400 mb-2">API Connections</h3>
            <div className="space-y-2">
              <div className="flex items-center gap-2 p-2 rounded hover:bg-gray-800">
                <div className="w-2 h-2 rounded-full bg-green-500"></div>
                <span className="text-sm">OpenAI API</span>
              </div>
              <div className="flex items-center gap-2 p-2 rounded hover:bg-gray-800">
                <div className="w-2 h-2 rounded-full bg-green-500"></div>
                <span className="text-sm">Local Model</span>
              </div>
            </div>
          </div>
        </div>

        <div className="p-4 border-t border-gray-700">
          <div
            className="flex items-center gap-3 cursor-pointer hover:bg-gray-800 p-2 rounded"
            onClick={logout}
          >
            <div className="w-8 h-8 rounded-full bg-purple-600 flex items-center justify-center">
              <span className="text-sm font-semibold">AI</span>
            </div>
            <div>
              <p className="text-sm font-medium">Logout</p>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col h-full overflow-hidden">
        {/* Header */}
        <header className="bg-white border-b border-gray-200 p-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <button
              className="text-gray-600 hover:text-gray-900"
              onClick={() => setSidebarOpen(!sidebarOpen)}
            >
              <i className="fas fa-bars"></i>
            </button>
            <h1 className="text-xl font-semibold">AI Assistant</h1>
          </div>

          <div className="flex items-center gap-4">
            <button
              className="text-gray-600 hover:text-gray-900"
              onClick={() => setSettingsOpen(true)}
            >
              <i className="fas fa-cog"></i>
            </button>
          </div>
        </header>

        {/* Content */}
        <main className="flex-1 flex flex-col overflow-hidden">{children}</main>
      </div>

      {/* Settings Modal */}
      {settingsOpen && (
        <div
          className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
          onClick={() => setSettingsOpen(false)}
        >
          <div
            className="bg-white rounded-lg shadow-xl w-full max-w-md max-h-[90vh] overflow-y-auto"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-xl font-semibold">Settings</h3>
                <button
                  className="text-gray-500 hover:text-gray-700"
                  onClick={() => setSettingsOpen(false)}
                >
                  <i className="fas fa-times"></i>
                </button>
              </div>
              <div className="space-y-6">
                <p className="text-sm text-gray-600">
                  Settings content goes here.
                </p>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
