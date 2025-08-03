import { useState, useEffect, useCallback } from 'react';
import api from '../api/api';

export default function Chat() {
  const [sessionId] = useState(() => crypto.randomUUID());
  const [input, setInput] = useState('');
  const [history, setHistory] = useState([]);
  const tenantId = localStorage.getItem('tenant_id');

  const loadHistory = useCallback(async () => {
    const res = await api.get('/chat/history', { params: { session_id: sessionId } });
    setHistory(res.data.history || []);
  }, [sessionId]);

  useEffect(() => {
    loadHistory();
  }, [loadHistory]);

  const sendMessage = async (e) => {
    e.preventDefault();
    if (!input.trim()) return;
    await api.post('/chat/message', {
      session_id: sessionId,
      tenant_id: tenantId,
      message: input,
    });
    setInput('');
    await loadHistory();
  };

  return (
    <div>
      <div className="h-64 overflow-y-auto border p-2 mb-4">
        {history.map((msg, idx) => (
          <div
            key={idx}
            className={`mb-2 ${msg.sender === 'user' ? 'text-right' : 'text-left'}`}
          >
            <span className="inline-block px-2 py-1 bg-gray-200 rounded">
              {msg.message}
            </span>
          </div>
        ))}
      </div>
      <form onSubmit={sendMessage} className="flex space-x-2">
        <input
          className="flex-1 border p-2 rounded"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Type your message"
        />
        <button
          type="submit"
          className="px-4 py-2 bg-blue-500 text-white rounded"
        >
          Send
        </button>
      </form>
    </div>
  );
}
