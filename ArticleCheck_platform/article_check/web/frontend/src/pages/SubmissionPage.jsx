import React, { useState, useEffect } from 'react';
import { CheckSquare, Loader2, CheckCircle, XCircle, AlertTriangle, Upload, FileText } from 'lucide-react';
import { api } from '../api/client';

const JOURNALS = ['IEEE Transactions', 'Elsevier', 'ACM Conference', 'Springer LNCS'];
const STAGES = ['initial', 'double-blind', 'camera-ready'];

export default function SubmissionPage() {
  const [files, setFiles] = useState([]);
  const [journal, setJournal] = useState(JOURNALS[0]);
  const [stage, setStage] = useState(STAGES[0]);
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    try {
      const res = await api.upload(file);
      setFiles(prev => [...prev, { ...res.data, name: file.name }]);
    } catch (err) { alert('上传失败'); }
  };

  const check = async () => {
    if (!files.length) return;
    setLoading(true);
    try {
      const res = await api.submissionCheck(files[0].path, journal, stage);
      setReport(res.data);
    } catch (err) { alert('检查失败: ' + err.message); }
    setLoading(false);
  };

  const statusIcon = (s) => s === 'pass' ? <CheckCircle className="w-4 h-4 text-green-500" /> :
    s === 'fail' ? <XCircle className="w-4 h-4 text-red-500" /> :
    <AlertTriangle className="w-4 h-4 text-amber-500" />;

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div>
        <h1 className="text-xl font-semibold">投稿就绪检查</h1>
        <p className="text-sm text-gray-400 mt-1">目标期刊要求逐条核对，PASS/FAIL 清单式报告</p>
      </div>

      <div className="card p-6 space-y-4">
        <div className="flex items-center gap-4 flex-wrap">
          <button onClick={() => document.getElementById('sub-upload').click()} className="btn-primary flex items-center gap-2">
            <Upload className="w-4 h-4" />上传论文
          </button>
          <input id="sub-upload" type="file" accept=".tex,.docx,.pdf" className="hidden" onChange={handleUpload} />
        </div>
        {files.map((f, i) => (
          <div key={i} className="flex items-center gap-2 text-sm text-gray-600"><FileText className="w-4 h-4" />{f.name}</div>
        ))}
        <div className="grid sm:grid-cols-2 gap-4">
          <div>
            <label className="text-xs text-gray-500 mb-1 block">目标期刊</label>
            <select value={journal} onChange={e => setJournal(e.target.value)} className="input">
              {JOURNALS.map(j => <option key={j}>{j}</option>)}
            </select>
          </div>
          <div>
            <label className="text-xs text-gray-500 mb-1 block">投稿阶段</label>
            <select value={stage} onChange={e => setStage(e.target.value)} className="input">
              {STAGES.map(s => <option key={s}>{s}</option>)}
            </select>
          </div>
        </div>
        <button onClick={check} disabled={loading || !files.length} className="btn-primary flex items-center gap-2">
          {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <CheckSquare className="w-4 h-4" />}
          检查投稿就绪状态
        </button>
      </div>

      {report && (
        <div className="card p-6 space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="font-medium">{report.journal}</h2>
              <p className="text-xs text-gray-400">阶段: {report.stage}</p>
            </div>
            <div className="text-right">
              <div className={`text-lg font-bold ${report.ready ? 'text-green-600' : 'text-red-600'}`}>
                {report.ready ? '✅ 可投稿' : '❌ 需修改'}
              </div>
              <p className="text-xs text-gray-400">{report.passed}/{report.total} 通过</p>
            </div>
          </div>
          <div className="space-y-2">
            {report.items?.map((item, i) => (
              <div key={i} className="flex items-start gap-3 p-3 rounded-lg bg-gray-50">
                {statusIcon(item.status)}
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-medium">{item.name}</div>
                  {item.detail && <div className="text-xs text-gray-400 mt-0.5">{item.detail}</div>}
                  {item.suggestion && <div className="text-xs text-amber-600 mt-0.5">💡 {item.suggestion}</div>}
                </div>
                <span className={`text-xs px-2 py-0.5 rounded-full ${
                  item.status === 'pass' ? 'bg-green-50 text-green-600' :
                  item.status === 'fail' ? 'bg-red-50 text-red-600' : 'bg-yellow-50 text-yellow-600'
                }`}>{item.status}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
