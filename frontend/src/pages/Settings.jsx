import { useEffect, useState } from 'react';
import api from '../api/api';

const KEYS = [
  {
    key: 'anthropic_api_key',
    label: 'Anthropic API key',
    placeholder: 'sk-ant-…',
    secret: true,
    provider: 'anthropic',
  },
  {
    key: 'openai_api_key',
    label: 'OpenAI API key',
    placeholder: 'sk-…',
    secret: true,
    provider: 'openai',
  },
  {
    key: 'ollama_base_url',
    label: 'Ollama base URL',
    placeholder: 'http://localhost:11434',
    secret: false,
    provider: 'ollama',
  },
];

const MODEL_CHOICES = {
  ollama: ['llama3', 'llama3.2', 'mistral', 'phi3'],
  openai: ['gpt-4o-mini', 'gpt-4o', 'gpt-4-turbo', 'gpt-3.5-turbo'],
  anthropic: ['claude-opus-4-6', 'claude-sonnet-4-6', 'claude-haiku-4-5'],
};

const PROVIDERS = ['ollama', 'openai', 'anthropic'];

function Field({ k, masked, value, onChange, onTest, testResult }) {
  return (
    <div className="bg-white border border-slate-200 rounded p-4">
      <label className="block text-sm font-semibold text-slate-700 mb-1">
        {k.label}
      </label>
      <div className="text-[11px] text-slate-500 mb-2">
        source:{' '}
        <span className="font-mono">
          {masked?.source || 'unset'}
        </span>
        {masked?.preview ? (
          <>
            {' · current: '}
            <span className="font-mono">{masked.preview}</span>
          </>
        ) : null}
      </div>
      <div className="flex gap-2">
        <input
          type={k.secret ? 'password' : 'text'}
          className="flex-1 px-3 py-2 border border-slate-300 rounded text-sm font-mono"
          placeholder={k.placeholder}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          autoComplete="off"
        />
        <button
          className="px-3 py-2 bg-slate-100 hover:bg-slate-200 border border-slate-300 rounded text-sm"
          onClick={onTest}
          title="Test this provider with the current value (or the stored one if blank)"
        >
          Test
        </button>
      </div>
      {testResult && (
        <div
          className={`mt-2 text-xs px-2 py-1 rounded ${
            testResult.ok
              ? 'bg-emerald-50 text-emerald-800 border border-emerald-200'
              : 'bg-rose-50 text-rose-800 border border-rose-200'
          }`}
        >
          {testResult.ok ? '✓ ok' : '✗ failed'} — {testResult.detail}
        </div>
      )}
    </div>
  );
}

export default function Settings() {
  const [masked, setMasked] = useState(null);
  const [drafts, setDrafts] = useState(Object.fromEntries(KEYS.map((k) => [k.key, ''])));
  const [tests, setTests] = useState({});
  const [tenants, setTenants] = useState([]);
  const [tenantConfigs, setTenantConfigs] = useState({});
  const [saving, setSaving] = useState(false);
  const [flash, setFlash] = useState('');

  const loadSettings = async () => {
    const res = await api.get('/admin/settings');
    setMasked(res.data);
  };

  const loadTenants = async () => {
    try {
      const res = await api.get('/admin/tenants');
      const names = Array.isArray(res.data) ? res.data : Object.keys(res.data);
      setTenants(names.map((t) => t.replace(/\s+/g, '')));
    } catch {
      setTenants([]);
    }
  };

  const loadTenant = async (id) => {
    try {
      const res = await api.get(`/admin/tenants/${id}`);
      setTenantConfigs((prev) => ({ ...prev, [id]: res.data }));
    } catch {
      // ignore
    }
  };

  useEffect(() => {
    loadSettings();
    loadTenants();
  }, []);

  useEffect(() => {
    tenants.forEach((t) => loadTenant(t));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tenants.join(',')]);

  const saveAll = async () => {
    setSaving(true);
    try {
      const payload = Object.fromEntries(
        KEYS.map((k) => [k.key, drafts[k.key]]).filter(([, v]) => v !== ''),
      );
      if (Object.keys(payload).length > 0) {
        await api.put('/admin/settings', payload);
      }
      await loadSettings();
      setDrafts(Object.fromEntries(KEYS.map((k) => [k.key, ''])));
      setFlash('Settings saved.');
      setTimeout(() => setFlash(''), 2500);
    } catch (err) {
      setFlash(err.response?.data?.detail || 'Save failed');
    } finally {
      setSaving(false);
    }
  };

  const runTest = async (k) => {
    const body = { provider: k.provider };
    if (drafts[k.key]) {
      if (k.secret) body.api_key = drafts[k.key];
      else body.base_url = drafts[k.key];
    }
    try {
      const res = await api.post('/admin/models/test', body);
      setTests((t) => ({ ...t, [k.key]: res.data }));
    } catch (err) {
      setTests((t) => ({
        ...t,
        [k.key]: { ok: false, detail: err.response?.data?.detail || err.message },
      }));
    }
  };

  const saveTenantConfig = async (id, nextConfig) => {
    try {
      await api.patch(`/admin/tenants/${id}`, {
        tenant_id: id,
        config: nextConfig,
      });
      setTenantConfigs((prev) => ({ ...prev, [id]: nextConfig }));
      setFlash(`Updated ${id}.`);
      setTimeout(() => setFlash(''), 2000);
    } catch (err) {
      setFlash(err.response?.data?.detail || 'Update failed');
    }
  };

  const updateTenantModels = (id, models) => {
    const current = tenantConfigs[id] || {};
    const nextConfig = {
      ...current,
      models,
      // Keep legacy fields in sync with the first entry so older code paths
      // still resolve a sane default even if they haven't migrated yet.
      model_type: models[0]?.provider || current.model_type,
      model_name: models[0]?.name || current.model_name,
    };
    saveTenantConfig(id, nextConfig);
  };

  const addModelRow = (id) => {
    const current = tenantConfigs[id] || {};
    const existing = current.models || [];
    const nextProvider = PROVIDERS[0];
    updateTenantModels(id, [
      ...existing,
      {
        provider: nextProvider,
        name: MODEL_CHOICES[nextProvider][0],
        label: `${nextProvider}/${MODEL_CHOICES[nextProvider][0]}`,
      },
    ]);
  };

  const removeModelRow = (id, idx) => {
    const current = tenantConfigs[id] || {};
    const existing = current.models || [];
    updateTenantModels(id, existing.filter((_, i) => i !== idx));
  };

  const changeModelRow = (id, idx, patch) => {
    const current = tenantConfigs[id] || {};
    const existing = current.models || [];
    const next = existing.map((m, i) => {
      if (i !== idx) return m;
      const merged = { ...m, ...patch };
      if (patch.provider && patch.provider !== m.provider) {
        merged.name = MODEL_CHOICES[patch.provider]?.[0] || '';
      }
      merged.label = merged.label || `${merged.provider}/${merged.name}`;
      return merged;
    });
    updateTenantModels(id, next);
  };

  return (
      <div className="flex-1 overflow-y-auto bg-slate-50 p-6">
        <div className="max-w-5xl mx-auto">
          <h1 className="text-2xl font-bold text-slate-800">Settings</h1>
          <p className="text-sm text-slate-600 mt-1 mb-6">
            Configure LLM provider credentials, test connectivity, and choose the model each
            tenant vault uses. Values saved here take precedence over environment variables.
          </p>

          {flash && (
            <div className="mb-4 text-sm bg-indigo-50 text-indigo-800 border border-indigo-200 rounded p-2">
              {flash}
            </div>
          )}

          <section className="mb-8">
            <h2 className="text-lg font-semibold text-slate-700 mb-3">Provider credentials</h2>
            <div className="space-y-3">
              {KEYS.map((k) => (
                <Field
                  key={k.key}
                  k={k}
                  masked={masked?.[k.key]}
                  value={drafts[k.key]}
                  onChange={(v) => setDrafts((d) => ({ ...d, [k.key]: v }))}
                  onTest={() => runTest(k)}
                  testResult={tests[k.key]}
                />
              ))}
            </div>
            <div className="mt-4 flex gap-2 items-center">
              <button
                className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded text-sm font-medium disabled:bg-slate-400"
                onClick={saveAll}
                disabled={saving}
              >
                {saving ? 'Saving…' : 'Save all'}
              </button>
              <span className="text-xs text-slate-500">
                Leave fields blank to keep the existing value. Type something and save to
                overwrite; clear to fall back to the env var.
              </span>
            </div>
          </section>

          <section className="mb-8">
            <h2 className="text-lg font-semibold text-slate-700 mb-1">
              Per-tenant model list
            </h2>
            <p className="text-xs text-slate-500 mb-3">
              Each tenant can offer multiple LLM providers and models. Users pick from this
              list at chat time — the first row is the default. Add as many as you like.
            </p>
            <div className="space-y-4">
              {tenants.map((tid) => {
                const cfg = tenantConfigs[tid] || {};
                const models = cfg.models || [];
                return (
                  <div
                    key={tid}
                    className="bg-white border border-slate-200 rounded p-4"
                  >
                    <div className="flex items-center justify-between mb-3">
                      <div>
                        <div className="text-sm font-semibold text-slate-700">
                          {cfg.name || tid}
                        </div>
                        <div className="text-xs text-slate-500 font-mono">{tid}</div>
                      </div>
                      <button
                        className="text-xs px-2 py-1 bg-indigo-50 hover:bg-indigo-100 border border-indigo-200 text-indigo-700 rounded"
                        onClick={() => addModelRow(tid)}
                      >
                        + Add model
                      </button>
                    </div>
                    {models.length === 0 && (
                      <div className="text-xs text-slate-400 italic">
                        No models configured — users cannot chat with this tenant until at
                        least one is added. Click "+ Add model".
                      </div>
                    )}
                    <div className="space-y-2">
                      {models.map((m, i) => (
                        <div
                          key={`${i}-${m.provider}-${m.name}`}
                          className="flex flex-wrap items-center gap-2"
                        >
                          <span
                            className={`text-[10px] px-1.5 py-0.5 rounded ${
                              i === 0
                                ? 'bg-emerald-100 text-emerald-800'
                                : 'bg-slate-100 text-slate-500'
                            }`}
                          >
                            {i === 0 ? 'default' : `#${i + 1}`}
                          </span>
                          <select
                            className="px-2 py-1 border border-slate-300 rounded text-xs"
                            value={m.provider}
                            onChange={(e) =>
                              changeModelRow(tid, i, { provider: e.target.value })
                            }
                          >
                            {PROVIDERS.map((p) => (
                              <option key={p} value={p}>
                                {p}
                              </option>
                            ))}
                          </select>
                          <select
                            className="px-2 py-1 border border-slate-300 rounded text-xs min-w-[180px]"
                            value={m.name}
                            onChange={(e) =>
                              changeModelRow(tid, i, { name: e.target.value })
                            }
                          >
                            {(MODEL_CHOICES[m.provider] || [])
                              .concat(
                                MODEL_CHOICES[m.provider]?.includes(m.name) ? [] : [m.name],
                              )
                              .filter(Boolean)
                              .map((c) => (
                                <option key={c} value={c}>
                                  {c}
                                </option>
                              ))}
                          </select>
                          <input
                            type="text"
                            className="px-2 py-1 border border-slate-300 rounded text-xs flex-1 min-w-[140px]"
                            placeholder="Friendly label"
                            value={m.label || ''}
                            onChange={(e) =>
                              changeModelRow(tid, i, { label: e.target.value })
                            }
                          />
                          <button
                            className="text-xs px-2 py-1 bg-rose-50 hover:bg-rose-100 border border-rose-200 text-rose-700 rounded"
                            onClick={() => removeModelRow(tid, i)}
                          >
                            Remove
                          </button>
                        </div>
                      ))}
                    </div>
                  </div>
                );
              })}
              {tenants.length === 0 && (
                <div className="text-sm text-slate-500">No tenants loaded.</div>
              )}
            </div>
          </section>
        </div>
      </div>
  );
}
