import { useEffect, useState } from 'react';
import api from '../api/api';

export default function UsageDashboard() {
  const [rollup, setRollup] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const load = async () => {
    setLoading(true);
    try {
      const res = await api.get('/admin/usage', { params: { limit: 120 } });
      setRollup(res.data?.rollup || []);
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const totalCost = rollup.reduce((s, r) => s + (r.est_cost_usd || 0), 0);
  const totalReq = rollup.reduce((s, r) => s + (r.request_count || 0), 0);
  const totalTokens = rollup.reduce(
    (s, r) => s + (r.input_tokens || 0) + (r.output_tokens || 0),
    0,
  );

  return (
    <div className="flex-1 overflow-y-auto bg-slate-50 p-6">
      <div className="max-w-6xl mx-auto">
        <h1 className="text-2xl font-bold text-slate-800">LLM usage</h1>
        <p className="text-sm text-slate-600 mt-1 mb-4">
          Per-day × per-tenant × per-provider rollup of token counts, request counts,
          average latency, and estimated cost. Cost figures use blended prices per 1M
          tokens from Anthropic / OpenAI published rates — informational only.
        </p>

        {error && (
          <div className="mb-3 text-sm bg-rose-50 text-rose-700 border border-rose-200 rounded p-2">
            {error}
          </div>
        )}

        <div className="grid grid-cols-3 gap-3 mb-4">
          <div className="bg-white border border-slate-200 rounded p-4">
            <div className="text-[11px] text-slate-500 uppercase">Total requests</div>
            <div className="text-2xl font-bold text-slate-800">
              {totalReq.toLocaleString()}
            </div>
          </div>
          <div className="bg-white border border-slate-200 rounded p-4">
            <div className="text-[11px] text-slate-500 uppercase">Total tokens</div>
            <div className="text-2xl font-bold text-slate-800">
              {totalTokens.toLocaleString()}
            </div>
          </div>
          <div className="bg-white border border-slate-200 rounded p-4">
            <div className="text-[11px] text-slate-500 uppercase">Est. cost</div>
            <div className="text-2xl font-bold text-slate-800">
              ${totalCost.toFixed(4)}
            </div>
          </div>
        </div>

        <div className="bg-white border border-slate-200 rounded overflow-hidden">
          <table className="min-w-full text-xs">
            <thead>
              <tr className="bg-slate-50 text-slate-500">
                <th className="text-left p-2">Day</th>
                <th className="text-left p-2">Tenant</th>
                <th className="text-left p-2">Provider / model</th>
                <th className="text-right p-2">Requests</th>
                <th className="text-right p-2">Input</th>
                <th className="text-right p-2">Output</th>
                <th className="text-right p-2">Cache read</th>
                <th className="text-right p-2">Avg latency</th>
                <th className="text-right p-2">Est. cost</th>
              </tr>
            </thead>
            <tbody>
              {rollup.map((r, i) => (
                <tr key={i} className="border-t border-slate-100">
                  <td className="p-2 font-mono">{r.day}</td>
                  <td className="p-2 font-mono text-indigo-700">{r.tenant_id}</td>
                  <td className="p-2 font-mono">
                    {r.provider} / {r.model_name}
                  </td>
                  <td className="p-2 text-right">{r.request_count.toLocaleString()}</td>
                  <td className="p-2 text-right">{r.input_tokens.toLocaleString()}</td>
                  <td className="p-2 text-right">{r.output_tokens.toLocaleString()}</td>
                  <td className="p-2 text-right text-emerald-700">
                    {r.cache_read_tokens.toLocaleString()}
                  </td>
                  <td className="p-2 text-right">{r.avg_latency_ms.toFixed(0)} ms</td>
                  <td className="p-2 text-right font-mono">${r.est_cost_usd.toFixed(4)}</td>
                </tr>
              ))}
              {rollup.length === 0 && !loading && (
                <tr>
                  <td colSpan="9" className="p-4 text-center text-slate-400">
                    No usage recorded yet — run a chat query to generate data.
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
