import { useState, useEffect } from 'react';
import api from '../api/api';

export default function Tenants() {
  const [tenants, setTenants] = useState([]);
  const [tenantId, setTenantId] = useState('');

  const loadTenants = async () => {
    try {
      const res = await api.get('/admin/tenants');
      setTenants(res.data);
    } catch {
      setTenants([]);
    }
  };

  useEffect(() => {
    loadTenants();
  }, []);

  const addTenant = async (e) => {
    e.preventDefault();
    if (!tenantId) return;
    await api.post('/admin/tenants', { tenant_id: tenantId, config: {} });
    setTenantId('');
    loadTenants();
  };

  const deleteTenant = async (id) => {
    await api.delete(`/admin/tenants/${id}`);
    loadTenants();
  };

  return (
    <div>
      <form onSubmit={addTenant} className="mb-4 flex space-x-2">
        <input
          className="border p-2 flex-1"
          value={tenantId}
          onChange={(e) => setTenantId(e.target.value)}
          placeholder="Tenant ID"
        />
        <button type="submit" className="px-4 py-2 bg-blue-500 text-white rounded">
          Add
        </button>
      </form>
      <ul className="list-disc pl-5">
        {tenants.map((t) => (
          <li key={t}>
            {t}
            <button
              onClick={() => deleteTenant(t)}
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
