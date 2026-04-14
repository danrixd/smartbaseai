import { useEffect, useState } from 'react';
import api from '../api/api';

const PROVIDERS = [
  { key: 'ollama', label: 'Ollama' },
  { key: 'openai', label: 'OpenAI' },
  { key: 'anthropic', label: 'Anthropic' },
];

export default function ApiStatus() {
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(false);

  const poll = async () => {
    setLoading(true);
    try {
      const res = await api.get('/admin/models/status');
      setStatus(res.data);
    } catch {
      setStatus(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    poll();
    const id = setInterval(poll, 30_000);
    return () => clearInterval(id);
  }, []);

  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-sm font-semibold text-gray-400">API Connections</h3>
        <button
          className="text-[10px] text-gray-500 hover:text-gray-300"
          onClick={poll}
          disabled={loading}
          title="Re-test connectivity"
        >
          {loading ? '…' : '↻'}
        </button>
      </div>
      <div className="space-y-1">
        {PROVIDERS.map(({ key, label }) => {
          const s = status?.[key];
          const ok = s?.ok === true;
          const unknown = !status;
          const dot = unknown
            ? 'bg-gray-500'
            : ok
            ? 'bg-green-500'
            : 'bg-red-500';
          const detail = s?.detail || (unknown ? 'unknown' : '');
          return (
            <div
              key={key}
              className="flex items-center gap-2 p-2 rounded hover:bg-gray-800"
              title={detail}
            >
              <div className={`w-2 h-2 rounded-full ${dot}`}></div>
              <span className="text-sm flex-1 truncate">{label}</span>
              <span className="text-[10px] text-gray-500 truncate max-w-[80px]">
                {unknown ? '' : ok ? 'ok' : 'down'}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
