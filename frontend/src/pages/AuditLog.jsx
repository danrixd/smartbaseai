import { useEffect, useState } from 'react';
import api from '../api/api';

export default function AuditLog() {
  const [rows, setRows] = useState([]);
  const [total, setTotal] = useState(0);
  const [filter, setFilter] = useState({ username: '', action: '' });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const load = async () => {
    setLoading(true);
    setError('');
    try {
      const params = { limit: 200, offset: 0 };
      if (filter.username) params.username = filter.username;
      if (filter.action) params.action = filter.action;
      const res = await api.get('/admin/audit-log', { params });
      setRows(res.data?.logs || []);
      setTotal(res.data?.total || 0);
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="flex-1 overflow-y-auto bg-slate-50 p-6">
      <div className="max-w-6xl mx-auto">
        <h1 className="text-2xl font-bold text-slate-800">Audit log</h1>
        <p className="text-sm text-slate-600 mt-1 mb-4">
          Every authenticated action against the backend — login, chat, vault edit, tenant
          CRUD, settings change — is recorded in <code>audit_logs</code>. Super-admin only.
        </p>

        <div className="bg-white border border-slate-200 rounded p-3 mb-4 flex flex-wrap items-end gap-2">
          <label className="text-xs text-slate-600">
            Username
            <input
              type="text"
              value={filter.username}
              onChange={(e) => setFilter((f) => ({ ...f, username: e.target.value }))}
              className="block mt-0.5 px-2 py-1 text-xs border border-slate-300 rounded"
              placeholder="any"
            />
          </label>
          <label className="text-xs text-slate-600">
            Action contains
            <input
              type="text"
              value={filter.action}
              onChange={(e) => setFilter((f) => ({ ...f, action: e.target.value }))}
              className="block mt-0.5 px-2 py-1 text-xs border border-slate-300 rounded"
              placeholder="chat_message, edit_vault_file, ..."
            />
          </label>
          <button
            className="px-3 py-1 text-xs bg-indigo-600 hover:bg-indigo-700 text-white rounded"
            onClick={load}
            disabled={loading}
          >
            {loading ? 'Loading…' : 'Search'}
          </button>
          <span className="text-xs text-slate-500 ml-auto">
            {total.toLocaleString()} total matches
          </span>
        </div>

        {error && (
          <div className="mb-3 text-sm bg-rose-50 text-rose-700 border border-rose-200 rounded p-2">
            {error}
          </div>
        )}

        <div className="bg-white border border-slate-200 rounded overflow-hidden">
          <table className="min-w-full text-xs">
            <thead>
              <tr className="bg-slate-50 text-slate-500">
                <th className="text-left p-2">Time</th>
                <th className="text-left p-2">User</th>
                <th className="text-left p-2">Action</th>
                <th className="text-left p-2">Details</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.id} className="border-t border-slate-100">
                  <td className="p-2 font-mono text-slate-500 whitespace-nowrap">
                    {r.created_at?.slice(0, 19).replace('T', ' ')}
                  </td>
                  <td className="p-2 font-mono text-slate-700">{r.username}</td>
                  <td className="p-2">
                    <span className="text-[11px] px-1.5 py-0.5 rounded bg-slate-100 text-slate-700 font-mono">
                      {r.action}
                    </span>
                  </td>
                  <td className="p-2 text-slate-600 font-mono truncate max-w-[500px]">
                    {r.details || '—'}
                  </td>
                </tr>
              ))}
              {rows.length === 0 && !loading && (
                <tr>
                  <td colSpan="4" className="p-4 text-center text-slate-400">
                    no events match
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
