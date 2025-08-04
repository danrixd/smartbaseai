import { useState, useEffect } from 'react';
import Layout from '../components/Layout';
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

  const editTenant = (id) => {
    alert(`Edit tenant ${id} - not implemented`);
  };

  return (
    <Layout>
      <div className="p-4 flex-1 overflow-y-auto">
        <div className="max-w-3xl mx-auto">
          <form onSubmit={addTenant} className="mb-4 flex space-x-2">
            <input
              className="border p-2 flex-1 rounded"
              value={tenantId}
              onChange={(e) => setTenantId(e.target.value)}
              placeholder="Tenant ID"
            />
            <button
              type="submit"
              className="px-4 py-2 bg-blue-500 text-white rounded"
            >
              Add
            </button>
          </form>
          <table className="min-w-full bg-white border">
            <thead>
              <tr className="bg-gray-100">
                <th className="text-left p-2 border-b">Tenant ID</th>
                <th className="p-2 border-b">Actions</th>
              </tr>
            </thead>
            <tbody>
              {tenants.map((t) => (
                <tr key={t} className="border-b last:border-b-0">
                  <td className="p-2">{t}</td>
                  <td className="p-2 text-right space-x-2">
                    <button
                      onClick={() => editTenant(t)}
                      className="text-blue-500 hover:underline"
                    >
                      Edit
                    </button>
                    <button
                      onClick={() => deleteTenant(t)}
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
