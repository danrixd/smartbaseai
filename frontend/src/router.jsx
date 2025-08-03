import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Login from './pages/Login';
import AdminDashboard from './pages/AdminDashboard';
import UserDashboard from './pages/UserDashboard';
import Chat from './pages/Chat';
import Files from './pages/Files';
import Tenants from './pages/Tenants';
import Users from './pages/Users';

function PrivateRoute({ children, allowedRoles }) {
  const token = localStorage.getItem('access_token');
  const role = localStorage.getItem('role');

  if (!token) return <Navigate to="/login" />;
  if (allowedRoles && !allowedRoles.includes(role)) return <Navigate to="/login" />;

  return children;
}

export default function AppRouter() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />

        <Route
          path="/admin/*"
          element={
            <PrivateRoute allowedRoles={['super_admin', 'admin']}>
              <AdminDashboard />
            </PrivateRoute>
          }
        >
          <Route path="tenants" element={<Tenants />} />
          <Route path="users" element={<Users />} />
          <Route index element={<div>Select a section</div>} />
        </Route>
        <Route
          path="/user/*"
          element={
            <PrivateRoute allowedRoles={['user', 'admin', 'super_admin']}>
              <UserDashboard />
            </PrivateRoute>
          }
        >
          <Route path="chat" element={<Chat />} />
          <Route path="files" element={<Files />} />
          <Route index element={<div>Select a section</div>} />
        </Route>

        <Route path="*" element={<Navigate to="/login" />} />
      </Routes>
    </BrowserRouter>
  );
}
