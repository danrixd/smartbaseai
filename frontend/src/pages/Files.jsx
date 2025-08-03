import { useState, useEffect } from 'react';
import Layout from '../components/Layout';
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
    <Layout>
      <div className="p-4 flex-1 overflow-y-auto">
        <div className="max-w-3xl mx-auto">
          <input
            type="file"
            onChange={handleUpload}
            className="mb-4"
          />
          <table className="min-w-full bg-white border">
            <thead>
              <tr className="bg-gray-100">
                <th className="text-left p-2 border-b">Filename</th>
              </tr>
            </thead>
            <tbody>
              {files.map((f) => (
                <tr key={f.filename} className="border-b last:border-b-0">
                  <td className="p-2">{f.filename}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </Layout>
  );
}
