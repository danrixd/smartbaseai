import { useState, useEffect } from 'react';
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

  return (
    <div>
      <form onSubmit={addUser} className="mb-4 space-y-2">
        <input
          name="username"
          value={form.username}
          onChange={handleChange}
          placeholder="Username"
          className="border p-2 w-full"
        />
        <input
          name="password"
          type="password"
          value={form.password}
          onChange={handleChange}
          placeholder="Password"
          className="border p-2 w-full"
        />
        <input
          name="tenant_id"
          value={form.tenant_id}
          onChange={handleChange}
          placeholder="Tenant ID (optional)"
          className="border p-2 w-full"
        />
        <select
          name="role"
          value={form.role}
          onChange={handleChange}
          className="border p-2 w-full"
        >
          <option value="user">user</option>
          <option value="admin">admin</option>
          <option value="super_admin">super_admin</option>
        </select>
        <button type="submit" className="px-4 py-2 bg-blue-500 text-white rounded w-full">
          Add User
        </button>
      </form>
      <ul className="list-disc pl-5">
        {users.map((u) => (
          <li key={u.username}>
            {u.username} ({u.role})
            <button
              onClick={() => deleteUser(u.username)}
              className="text-red-500 ml-2"
            >
              Delete
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
