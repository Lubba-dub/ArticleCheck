import React, { useState } from 'react';
import { BookOpen, Loader2, FileText, TrendingUp, Lightbulb } from 'lucide-react';
import { api } from '../api/client';

export default function SurveyPage() {
  const [query, setQuery] = useState('');
  const [survey, setSurvey] = useState(null);
  const [markdown, setMarkdown] = useState('');
  const [loading, setLoading] = useState(false);

  const generate = async () => {
    if (!query.trim()) return;
    setLoading(true);
    try {
      const res = await api.survey(query, []);
      setSurvey(res.data);
      const md = await api.surveyMarkdown(query);
      setMarkdown(md);
    } catch (err) { alert('生成失败: ' + err.message); }
    setLoading(false);
  };

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div>
        <h1 className="text-xl font-semibold">文献综述</h1>
        <p className="text-sm text-gray-400 mt-1">多源搜索 → 论文聚类 → 趋势分析 → 可视化图谱</p>
      </div>

      <div className="card p-6">
        <div className="flex gap-2">
          <input value={query} onChange={e => setQuery(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && generate()}
            placeholder="输入研究主题 ..." className="input flex-1" />
          <button onClick={generate} disabled={loading} className="btn-primary flex items-center gap-2">
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <BookOpen className="w-4 h-4" />}
            生成综述
          </button>
        </div>
      </div>

      {survey && (
        <div className="space-y-6">
          {/* Trends */}
          {survey.trends?.length > 0 && (
            <div className="card p-5">
              <h2 className="text-sm font-semibold flex items-center gap-2 mb-3"><TrendingUp className="w-4 h-4 text-primary-600" />趋势分析</h2>
              {survey.trends.map((t, i) => (
                <p key={i} className="text-sm text-gray-700">{t}</p>
              ))}
            </div>
          )}

          {/* Sections */}
          <div className="grid gap-4">
            {survey.sections.map((sec, i) => (
              <div key={i} className="card p-5">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="font-medium text-sm">{sec.title}</h3>
                  <span className="badge-blue">{sec.paper_count} 篇</span>
                </div>
                <div className="space-y-2">
                  {sec.papers?.slice(0, 5).map((p, j) => (
                    <div key={j} className="flex items-start gap-2 text-xs text-gray-600">
                      <FileText className="w-3.5 h-3.5 mt-0.5 text-gray-300 shrink-0" />
                      <span>{p.authors?.join(', ')} — {p.title}<span className="text-gray-400"> ({p.year})</span></span>
                    </div>
                  ))}
                  {sec.papers?.length > 5 && <div className="text-xs text-gray-400">...还有 {sec.papers.length - 5} 篇</div>}
                </div>
              </div>
            ))}
          </div>

          {/* Missing refs */}
          {survey.missing_refs?.length > 0 && (
            <div className="card p-5 border-l-4 border-l-amber-400">
              <h3 className="text-sm font-semibold flex items-center gap-2 mb-2"><Lightbulb className="w-4 h-4 text-amber-500" />建议补充文献</h3>
              {survey.missing_refs.map((p, i) => (
                <p key={i} className="text-xs text-gray-600 py-0.5">• {p.title} ({p.year})</p>
              ))}
            </div>
          )}

          {/* Markdown */}
          {markdown && (
            <details className="card p-5">
              <summary className="text-sm font-medium cursor-pointer text-gray-600 hover:text-gray-900">查看 Markdown 原文</summary>
              <pre className="mt-3 text-xs text-gray-500 whitespace-pre-wrap max-h-96 overflow-y-auto">{markdown}</pre>
            </details>
          )}
        </div>
      )}

      {loading && <div className="text-center py-12 text-gray-400"><Loader2 className="w-6 h-6 animate-spin mx-auto mb-2" />生成综述中...</div>}
    </div>
  );
}
