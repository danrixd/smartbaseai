import { useState, useEffect } from 'react';
import api from '../api/api';

export default function Files() {
  const [files, setFiles] = useState([]);

  const loadFiles = async () => {
    const res = await api.get('/files/list');
    setFiles(res.data);
  };

  useEffect(() => {
    loadFiles();
  }, []);

  const handleUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    const formData = new FormData();
    formData.append('file', file);
    await api.post('/files/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    e.target.value = '';
    loadFiles();
  };

  return (
    <div>
      <input type="file" onChange={handleUpload} className="mb-4" />
      <ul className="list-disc pl-5">
        {files.map((f) => (
          <li key={f.filename}>{f.filename}</li>
        ))}
      </ul>
    </div>
  );
}
