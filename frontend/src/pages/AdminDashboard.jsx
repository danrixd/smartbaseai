import { Link, Outlet } from 'react-router-dom';

export default function AdminDashboard() {
  return (
    <div className="p-8">
      <h1 className="text-3xl font-bold mb-4">Admin Dashboard</h1>
      <nav className="mb-6 space-x-4">
        <Link className="text-blue-500" to="/admin/tenants">
          Tenants
        </Link>
        <Link className="text-blue-500" to="/admin/users">
          Users
        </Link>
      </nav>
      <Outlet />
    </div>
  );
}
