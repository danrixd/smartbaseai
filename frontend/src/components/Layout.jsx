import { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import api from '../api/api';
import AppContext from '../store/AppContext';
import ApiStatus from './ApiStatus';

export default function Layout({ children }) {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [sessions, setSessions] = useState([]);
  const [tenants, setTenants] = useState([]);
  const [activeTenant, setActiveTenant] = useState(
    (localStorage.getItem('active_tenant') || '').replace(/\s+/g, '')
  );
  const role = localStorage.getItem('role');
  const navigate = useNavigate();

  const logout = () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('role');
    localStorage.removeItem('tenant_id');
    localStorage.removeItem('active_tenant');
    navigate('/login');
  };

  const createSession = () => {
    const id = crypto.randomUUID();
    setSessions((prev) => [{ id, title: 'New Chat' }, ...prev]);
    navigate(`/chat?session=${id}`);
  };

  useEffect(() => {
    if (role === 'super_admin') {
      api
        .get('/admin/tenants')
        .then((res) =>
          setTenants(
            Array.isArray(res.data)
              ? res.data.map((t) => t.replace(/\s+/g, ''))
              : Object.keys(res.data).map((t) => t.replace(/\s+/g, ''))
          )
        )
        .catch(() => setTenants([]));
    } else {
      const t = (localStorage.getItem('tenant_id') || '').replace(/\s+/g, '');
      setTenants(t ? [t] : []);
      setActiveTenant(t || '');
      if (t) localStorage.setItem('active_tenant', t);
    }
  }, [role]);

  useEffect(() => {
    api
      .get('/chat/sessions')
      .then((res) => setSessions(res.data.sessions || []))
      .catch(() => setSessions([]));
  }, []);

  // Intentionally NOT auto-selecting a tenant for super_admin — they must
  // pick a vault from the top-right dropdown before any per-vault page loads.
  useEffect(() => {
    if (role !== 'super_admin' && !activeTenant && tenants.length > 0) {
      setActiveTenant(tenants[0]);
      localStorage.setItem('active_tenant', tenants[0]);
    }
  }, [role, activeTenant, tenants]);

  const updateActiveTenant = (t) => {
    const id = (t || '').replace(/\s+/g, '');
    setActiveTenant(id);
    localStorage.setItem('active_tenant', id);
  };

  const deleteSession = async (id) => {
    try {
      await api.delete(`/chat/session/${id}`);
      setSessions((prev) => prev.filter((s) => s.id !== id));
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <AppContext.Provider
      value={{ sessions, setSessions, activeTenant, setActiveTenant: updateActiveTenant, tenants }}
    >
      <div className="flex h-screen overflow-hidden bg-gray-50 text-gray-800">
        {/* Sidebar */}
        <div
          className={`w-64 bg-gray-900 text-white flex flex-col h-full transition-all duration-300 ease-in-out ${sidebarOpen ? '' : '-ml-64'}`}
        >
          <div className="p-4 border-b border-gray-700">
            <button
              className="w-full flex items-center justify-center gap-2 bg-gray-700 hover:bg-gray-600 text-white py-2 px-4 rounded-md transition-colors"
              onClick={createSession}
            >
              <i className="fas fa-plus"></i>
              <span>New Chat</span>
            </button>
          </div>

          <div className="flex-1 overflow-y-auto">
            <div className="p-4">
              <h3 className="text-sm font-semibold text-gray-400 mb-2">Chat History</h3>
              <ul className="space-y-1">
                {sessions.map((s) => (
                  <li
                    key={s.id}
                    className="flex items-center gap-3 p-2 rounded hover:bg-gray-800 cursor-pointer"
                  >
                    <i className="fas fa-comment text-gray-400" onClick={() => navigate(`/chat?session=${s.id}`)}></i>
                    <span
                      className="flex-1 text-sm truncate"
                      onClick={() => navigate(`/chat?session=${s.id}`)}
                    >
                      {s.title}
                    </span>
                    <button
                      className="text-gray-400 hover:text-red-500"
                      onClick={(e) => {
                        e.stopPropagation();
                        deleteSession(s.id);
                      }}
                    >
                      <i className="fas fa-trash"></i>
                    </button>
                  </li>
                ))}
              </ul>
            </div>

            <div className="p-4 border-t border-gray-700">
              <h3 className="text-sm font-semibold text-gray-400 mb-2">Navigation</h3>
              <nav className="space-y-1">
                <Link className="block p-2 rounded hover:bg-gray-800" to="/chat">
                  Chat
                </Link>
                <Link className="block p-2 rounded hover:bg-gray-800" to="/vault">
                  Vault
                </Link>
                <Link className="block p-2 rounded hover:bg-gray-800" to="/rag">
                  RAG Visualizer
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
                {role === 'super_admin' && (
                  <Link className="block p-2 rounded hover:bg-gray-800" to="/settings">
                    Settings
                  </Link>
                )}
              </nav>
            </div>

            <div className="p-4 border-t border-gray-700">
              <ApiStatus />
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
              {role === 'super_admin' && tenants.length > 0 && (
                <div className="flex items-center gap-2">
                  <span className="text-xs text-gray-500">Active vault:</span>
                  <select
                    value={activeTenant || ''}
                    onChange={(e) => updateActiveTenant(e.target.value)}
                    className="px-2 py-1 border border-gray-300 rounded text-sm"
                  >
                    <option value="">— choose a vault —</option>
                    {tenants.map((t) => (
                      <option key={t} value={t}>
                        {t}
                      </option>
                    ))}
                  </select>
                </div>
              )}
              {role === 'super_admin' && (
                <button
                  className="text-gray-600 hover:text-gray-900"
                  onClick={() => navigate('/settings')}
                  title="Settings"
                >
                  <i className="fas fa-cog"></i>
                </button>
              )}
            </div>
          </header>

          {/* Content */}
          <main className="flex-1 flex flex-col overflow-hidden">{children}</main>
        </div>
      </div>
    </AppContext.Provider>
  );
}
