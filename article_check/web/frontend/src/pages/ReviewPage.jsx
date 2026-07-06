import React, { useState, useRef, useCallback } from 'react';
import { Upload, FileText, Loader2, CheckCircle, AlertTriangle, FileWarning, ExternalLink, Search } from 'lucide-react';
import { api } from '../api/client';

export default function ReviewPage() {
  const [files, setFiles] = useState([]);
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [streaming, setStreaming] = useState(false);
  const [deepReview, setDeepReview] = useState(false);
  const [uploading, setUploading] = useState(false);
  const inputRef = useRef();

  const handleUpload = useCallback(async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    try {
      const res = await api.upload(file);
      setFiles(prev => [...prev, { ...res.data, name: file.name }]);
    } catch (err) { alert('上传失败: ' + err.message); }
    setUploading(false);
  }, []);

  const runReview = useCallback(async () => {
    if (!files.length) return;
    setLoading(true); setResults([]);
    try {
      const allResults = [];
      for (const f of files) {
        const res = await api.review(f.path, null, deepReview);
        allResults.push({ file: f, review: res.data });
      }
      setResults(allResults);
    } catch (err) { alert('审查失败: ' + err.message); }
    setLoading(false);
  }, [files, deepReview]);

  const runBatchStream = useCallback(async () => {
    if (!files.length) return;
    setStreaming(true); setResults([]);
    try {
      const paths = files.map(f => f.path);
      const res = await api.batchStream(paths);
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n\n');
        buffer = lines.pop() || '';
        for (const line of lines) {
          if (!line.startsWith('data: ')) continue;
          const data = JSON.parse(line.slice(6));
          if (data.type === 'result') {
            setResults(prev => [...prev, { file: { name: data.paper_title }, review: data }]);
          }
        }
      }
    } catch (err) { alert('流式审查失败: ' + err.message); }
    setStreaming(false);
  }, [files]);

  const severityColor = (s) => s === 'critical' ? 'text-red-600 bg-red-50' : s === 'major' ? 'text-amber-600 bg-amber-50' : 'text-blue-600 bg-blue-50';
  const severityIcon = (s) => s === 'critical' ? <FileWarning className="w-4 h-4" /> : s === 'major' ? <AlertTriangle className="w-4 h-4" /> : <CheckCircle className="w-4 h-4" />;

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div>
        <h1 className="text-xl font-semibold">论文审查</h1>
        <p className="text-sm text-gray-400 mt-1">格式检查 + 内容分析 + 文献验证</p>
      </div>

      {/* Upload */}
      <div className="card p-6">
        <div className="flex items-center gap-4 flex-wrap">
          <button onClick={() => inputRef.current?.click()} disabled={uploading}
            className="btn-primary flex items-center gap-2">
            <Upload className="w-4 h-4" /> {uploading ? '上传中...' : '上传论文'}
          </button>
          <input ref={inputRef} type="file" accept=".tex,.docx,.pdf,.doc,.ltx" className="hidden" onChange={handleUpload} />
          <label className="flex items-center gap-2 text-sm text-gray-500 cursor-pointer">
            <input type="checkbox" checked={deepReview} onChange={e => setDeepReview(e.target.checked)} className="rounded" />
            深度审查（DeepSeek 内容分析）
          </label>
        </div>
        {/* File list */}
        {files.length > 0 && (
          <div className="mt-4 space-y-2">
            {files.map((f, i) => (
              <div key={i} className="flex items-center justify-between px-3 py-2 bg-gray-50 rounded-lg text-sm">
                <span className="flex items-center gap-2"><FileText className="w-4 h-4 text-gray-400" /> {f.name}</span>
                <span className="text-xs text-gray-400">{(f.size / 1024).toFixed(0)} KB</span>
              </div>
            ))}
            <div className="flex gap-3 mt-4">
              <button onClick={runReview} disabled={loading} className="btn-primary flex items-center gap-2">
                {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
                开始审查
              </button>
              <button onClick={runBatchStream} disabled={streaming} className="btn-outline flex items-center gap-2">
                {streaming ? <Loader2 className="w-4 h-4 animate-spin" /> : <ExternalLink className="w-4 h-4" />}
                流式批处理
              </button>
            </div>
          </div>
        )}
        {files.length === 0 && <p className="text-xs text-gray-400 mt-2">支持 .tex .docx .pdf 格式</p>}
      </div>

      {/* Results */}
      {results.map(({ file, review }, fi) => (
        <div key={fi} className="card p-6 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="font-medium">{file.name}</h2>
            <span className="text-xs text-gray-400">{review.file_type}</span>
          </div>

          {/* Score */}
          {review.score !== undefined && (
            <div className="flex items-center gap-4">
              <div className={`text-2xl font-bold ${review.score >= 0.8 ? 'text-green-600' : review.score >= 0.6 ? 'text-amber-600' : 'text-red-600'}`}>
                {(review.score * 100).toFixed(0)}
              </div>
              <div className="text-xs text-gray-400">综合评分</div>
            </div>
          )}

          {/* Format issues */}
          {review.format_issues?.length > 0 && (
            <div>
              <h3 className="text-sm font-medium text-gray-700 mb-2">格式问题 ({review.format_issues.length})</h3>
              <div className="space-y-1 max-h-48 overflow-y-auto">
                {review.format_issues.map((issue, i) => (
                  <div key={i} className={`flex items-start gap-2 p-2 rounded text-xs ${severityColor(issue.severity || 'info')}`}>
                    {severityIcon(issue.severity || 'info')}
                    <span>{issue.description}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* References */}
          {review.references && (
            <div className="grid grid-cols-4 gap-3">
              <div className="stat-card p-3 text-center"><div className="stat-value text-lg">{review.references.total_refs}</div><div className="stat-label text-xs">文献</div></div>
              <div className="stat-card p-3 text-center"><div className="stat-value text-lg">{review.references.matched}</div><div className="stat-label text-xs">匹配</div></div>
              <div className="stat-card p-3 text-center"><div className="stat-value text-lg">{review.references.score.toFixed(2)}</div><div className="stat-label text-xs">一致性</div></div>
              <div className="stat-card p-3 text-center"><div className="stat-value text-lg">{review.references.doi_missing}</div><div className="stat-label text-xs">缺DOI</div></div>
            </div>
          )}

          {/* Sections */}
          {review.sections?.length > 0 && (
            <div className="flex flex-wrap gap-2">
              {review.sections.map((s, i) => <span key={i} className="badge-blue">{s}</span>)}
            </div>
          )}
        </div>
      ))}

      {loading && <div className="text-center py-12 text-gray-400"><Loader2 className="w-6 h-6 animate-spin mx-auto mb-2" />审查中...</div>}
    </div>
  );
}
