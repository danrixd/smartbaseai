import { useState, useEffect } from 'react';
import Layout from '../components/Layout';
import api from '../api/api';

export default function Users() {
  const [users, setUsers] = useState([]);
  const [form, setForm] = useState({
    username: '',
    password: '',
    role: 'user',
    tenant_id: '',
  });

  const loadUsers = async () => {
    const res = await api.get('/admin/users');
    setUsers(res.data);
  };

  useEffect(() => {
    loadUsers();
  }, []);

  const handleChange = (e) => {
    setForm({ ...form, [e.target.name]: e.target.value });
  };

  const addUser = async (e) => {
    e.preventDefault();
    await api.post('/admin/users', form);
    setForm({ username: '', password: '', role: 'user', tenant_id: '' });
    loadUsers();
  };

  const deleteUser = async (username) => {
    await api.delete(`/admin/users/${username}`);
    loadUsers();
  };

  const editUser = (username) => {
    alert(`Edit user ${username} - not implemented`);
  };

  return (
    <Layout>
      <div className="p-4 flex-1 overflow-y-auto">
        <div className="max-w-3xl mx-auto">
          <form onSubmit={addUser} className="mb-4 grid grid-cols-1 md:grid-cols-2 gap-2">
            <input
              name="username"
              value={form.username}
              onChange={handleChange}
              placeholder="Username"
              className="border p-2 rounded"
            />
            <input
              name="password"
              type="password"
              value={form.password}
              onChange={handleChange}
              placeholder="Password"
              className="border p-2 rounded"
            />
            <input
              name="tenant_id"
              value={form.tenant_id}
              onChange={handleChange}
              placeholder="Tenant ID (optional)"
              className="border p-2 rounded"
            />
            <select
              name="role"
              value={form.role}
              onChange={handleChange}
              className="border p-2 rounded"
            >
              <option value="user">user</option>
              <option value="admin">admin</option>
              <option value="super_admin">super_admin</option>
            </select>
            <button
              type="submit"
              className="px-4 py-2 bg-blue-500 text-white rounded col-span-1 md:col-span-2"
            >
              Add User
            </button>
          </form>

          <table className="min-w-full bg-white border">
            <thead>
              <tr className="bg-gray-100">
                <th className="text-left p-2 border-b">Username</th>
                <th className="text-left p-2 border-b">Role</th>
                <th className="text-left p-2 border-b">Tenant</th>
                <th className="p-2 border-b">Actions</th>
              </tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.username} className="border-b last:border-b-0">
                  <td className="p-2">{u.username}</td>
                  <td className="p-2">{u.role}</td>
                  <td className="p-2">{u.tenant_id || '-'}</td>
                  <td className="p-2 text-right space-x-2">
                    <button
                      onClick={() => editUser(u.username)}
                      className="text-blue-500 hover:underline"
                    >
                      Edit
                    </button>
                    <button
                      onClick={() => deleteUser(u.username)}
                      className="text-red-500 hover:underline"
                    >
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </Layout>
  );
}
