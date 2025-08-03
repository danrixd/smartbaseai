import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Login from './pages/Login';
import Chat from './pages/Chat';
import Files from './pages/Files';
import Tenants from './pages/Tenants';
import Users from './pages/Users';

function PrivateRoute({ children, allowedRoles }) {
  const token = localStorage.getItem('access_token');
  const role = localStorage.getItem('role');

  if (!token) return <Navigate to="/login" />;
  if (allowedRoles && !allowedRoles.includes(role)) return <Navigate to="/chat" />;

  return children;
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
          path="/files"
          element={
            <PrivateRoute allowedRoles={['user', 'admin', 'super_admin']}>
              <Files />
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
