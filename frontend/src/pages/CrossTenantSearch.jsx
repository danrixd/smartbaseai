import { useEffect, useState } from 'react';
import api from '../api/api';

export default function CrossTenantSearch() {
  const [query, setQuery] = useState('');
  const [tenants, setTenants] = useState([]);
  const [selected, setSelected] = useState(new Set());
  const [hits, setHits] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    api
      .get('/admin/tenants')
      .then((res) => {
        const list = Array.isArray(res.data) ? res.data : Object.keys(res.data || {});
        setTenants(list);
        setSelected(new Set(list));
      })
      .catch(() => setTenants([]));
  }, []);

  const toggleTenant = (t) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(t)) next.delete(t);
      else next.add(t);
      return next;
    });
  };

  const run = async () => {
    const q = query.trim();
    if (!q) return;
    setLoading(true);
    setError('');
    try {
      const params = { q, top_k: 5 };
      if (selected.size > 0 && selected.size < tenants.length) {
        params.tenants = Array.from(selected).join(',');
      }
      const res = await api.get('/admin/search', { params });
      setHits(res.data?.hits || []);
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
      setHits([]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex-1 overflow-y-auto bg-slate-50 p-6">
      <div className="max-w-5xl mx-auto">
        <h1 className="text-2xl font-bold text-slate-800">Cross-tenant search</h1>
        <p className="text-sm text-slate-600 mt-1 mb-4">
          Run a hybrid retrieval query across any combination of vaults and see which
          tenants contain relevant content. Super-admin only.
        </p>

        <div className="bg-white border border-slate-200 rounded p-4 mb-4 shadow-sm">
          <div className="flex gap-2 mb-3">
            <input
              type="text"
              className="flex-1 px-3 py-2 text-sm border border-slate-300 rounded focus:outline-none focus:border-indigo-400"
              placeholder="e.g. quokka, hubble tension, net income 2022, Dr. Inbar Katz…"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && run()}
            />
            <button
              className="px-4 py-2 text-sm bg-indigo-600 hover:bg-indigo-700 text-white rounded disabled:bg-slate-400"
              onClick={run}
              disabled={loading}
            >
              {loading ? 'Searching…' : 'Search'}
            </button>
          </div>
          <div className="flex flex-wrap gap-1.5">
            {tenants.map((t) => {
              const on = selected.has(t);
              return (
                <button
                  key={t}
                  className={`text-[11px] px-2 py-0.5 rounded border ${
                    on
                      ? 'bg-indigo-100 border-indigo-300 text-indigo-800'
                      : 'bg-slate-50 border-slate-200 text-slate-500'
                  }`}
                  onClick={() => toggleTenant(t)}
                >
                  {t}
                </button>
              );
            })}
            <button
              className="text-[10px] text-slate-400 ml-2 hover:text-slate-600"
              onClick={() => setSelected(new Set(tenants))}
            >
              select all
            </button>
            <button
              className="text-[10px] text-slate-400 hover:text-slate-600"
              onClick={() => setSelected(new Set())}
            >
              clear
            </button>
          </div>
        </div>

        {error && (
          <div className="mb-3 text-sm bg-rose-50 text-rose-700 border border-rose-200 rounded p-2">
            {error}
          </div>
        )}

        <div className="space-y-2">
          {hits.map((h, i) => (
            <div key={i} className="bg-white border border-slate-200 rounded p-3">
              <div className="flex items-center gap-2 text-[11px] text-slate-500 mb-1">
                <span className="px-1.5 py-0.5 rounded bg-indigo-100 text-indigo-800 font-mono">
                  {h.tenant_id}
                </span>
                <span className="px-1.5 py-0.5 rounded bg-slate-100 text-slate-600">
                  {h.source}
                </span>
                <span className="font-mono">
                  {h.score != null ? `d=${h.score.toFixed(3)}` : 'keyword'}
                </span>
                <span className="font-mono text-slate-700 truncate">{h.path || h.filename}</span>
              </div>
              <div className="text-xs text-slate-700 whitespace-pre-wrap font-mono">
                {h.preview}
              </div>
            </div>
          ))}
          {!loading && hits.length === 0 && query && (
            <div className="text-sm text-slate-400 text-center p-6">
              No hits — try a different query or include more tenants.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
