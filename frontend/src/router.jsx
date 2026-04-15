import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Layout from './components/Layout';
import Login from './pages/Login';
import Chat from './pages/Chat';
import Tenants from './pages/Tenants';
import Users from './pages/Users';
import RagVisualizer from './pages/RagVisualizer';
import Settings from './pages/Settings';
import Vault from './pages/Vault';
import AuditLog from './pages/AuditLog';
import CrossTenantSearch from './pages/CrossTenantSearch';
import UsageDashboard from './pages/UsageDashboard';

function PrivateRoute({ children, allowedRoles }) {
  const token = localStorage.getItem('access_token');
  const role = localStorage.getItem('role');

  if (!token) return <Navigate to="/login" />;
  if (allowedRoles && !allowedRoles.includes(role)) return <Navigate to="/chat" />;

  // Layout wraps every authenticated page so its AppContext.Provider is an
  // ancestor of the page. Without this, pages that call useContext(AppContext)
  // would read the default empty context — the Provider inside a child Layout
  // wouldn't reach them, and activeTenant would never update.
  return <Layout>{children}</Layout>;
}

export default function AppRouter() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route
          path="/chat"
          element={
            <PrivateRoute allowedRoles={['user', 'admin', 'super_admin']}>
              <Chat />
            </PrivateRoute>
          }
        />
        <Route
          path="/rag"
          element={
            <PrivateRoute allowedRoles={['user', 'admin', 'super_admin']}>
              <RagVisualizer />
            </PrivateRoute>
          }
        />
        <Route
          path="/vault"
          element={
            <PrivateRoute allowedRoles={['user', 'admin', 'super_admin']}>
              <Vault />
            </PrivateRoute>
          }
        />
        <Route
          path="/settings"
          element={
            <PrivateRoute allowedRoles={['super_admin']}>
              <Settings />
            </PrivateRoute>
          }
        />
        <Route
          path="/audit"
          element={
            <PrivateRoute allowedRoles={['super_admin']}>
              <AuditLog />
            </PrivateRoute>
          }
        />
        <Route
          path="/search"
          element={
            <PrivateRoute allowedRoles={['super_admin']}>
              <CrossTenantSearch />
            </PrivateRoute>
          }
        />
        <Route
          path="/usage"
          element={
            <PrivateRoute allowedRoles={['super_admin']}>
              <UsageDashboard />
            </PrivateRoute>
          }
        />
        <Route
          path="/tenants"
          element={
            <PrivateRoute allowedRoles={['admin', 'super_admin']}>
              <Tenants />
            </PrivateRoute>
          }
        />
        <Route
          path="/users"
          element={
            <PrivateRoute allowedRoles={['admin', 'super_admin']}>
              <Users />
            </PrivateRoute>
          }
        />
        <Route path="*" element={<Navigate to="/chat" />} />
      </Routes>
    </BrowserRouter>
  );
}
