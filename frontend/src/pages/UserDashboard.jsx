import { Link, Outlet } from 'react-router-dom';

export default function UserDashboard() {
  return (
    <div className="p-8">
      <h1 className="text-3xl font-bold mb-4">User Dashboard</h1>
      <nav className="mb-6 space-x-4">
        <Link className="text-blue-500" to="/user/chat">
          Chat
        </Link>
        <Link className="text-blue-500" to="/user/files">
          Files
        </Link>
      </nav>
      <Outlet />
    </div>
  );
}
