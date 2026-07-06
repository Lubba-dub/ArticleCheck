import React, { useState } from 'react';
import { Search, Loader2, ExternalLink, Bookmark, Globe } from 'lucide-react';
import { api } from '../api/client';

const SOURCES = [
  { id: 'semantic_scholar', label: 'Semantic Scholar', color: 'text-yellow-600 bg-yellow-50' },
  { id: 'openalex', label: 'OpenAlex', color: 'text-blue-600 bg-blue-50' },
  { id: 'crossref', label: 'CrossRef', color: 'text-green-600 bg-green-50' },
  { id: 'arxiv', label: 'arXiv', color: 'text-red-600 bg-red-50' },
];

export default function LiteraturePage() {
  const [query, setQuery] = useState('');
  const [papers, setPapers] = useState([]);
  const [loading, setLoading] = useState(false);
  const [total, setTotal] = useState(0);
  const [selectedSources, setSelectedSources] = useState(SOURCES.map(s => s.id));

  const search = async () => {
    if (!query.trim()) return;
    setLoading(true);
    try {
      const res = await api.search(query, selectedSources, 10);
      setPapers(res.data.papers);
      setTotal(res.data.count);
    } catch (err) { alert('搜索失败: ' + err.message); }
    setLoading(false);
  };

  const toggleSource = (id) => {
    setSelectedSources(prev => prev.includes(id) ? prev.filter(s => s !== id) : [...prev, id]);
  };

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div>
        <h1 className="text-xl font-semibold">文献检索</h1>
        <p className="text-sm text-gray-400 mt-1">5 个学术数据源并发搜索，自动去重排序</p>
      </div>

      {/* Search bar */}
      <div className="card p-6 space-y-4">
        <div className="flex gap-2">
          <input value={query} onChange={e => setQuery(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && search()}
            placeholder="输入研究主题或关键词 ..."
            className="input flex-1" />
          <button onClick={search} disabled={loading} className="btn-primary flex items-center gap-2">
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
            搜索
          </button>
        </div>
        <div className="flex flex-wrap gap-2">
          {SOURCES.map(s => (
            <button key={s.id} onClick={() => toggleSource(s.id)}
              className={`text-xs px-3 py-1.5 rounded-full border transition-colors ${
                selectedSources.includes(s.id) ? `${s.color} border-transparent` : 'text-gray-400 border-gray-200'
              }`}>
              <Globe className="w-3 h-3 inline mr-1" />{s.label}
            </button>
          ))}
        </div>
      </div>

      {/* Results */}
      {papers.length > 0 && (
        <div className="space-y-3">
          <p className="text-sm text-gray-400">共 {total} 篇（去重后 {papers.length} 篇）</p>
          {papers.map((p, i) => (
            <div key={i} className="card p-5 hover:shadow-lg transition-shadow">
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1 min-w-0">
                  <h3 className="font-medium text-sm text-gray-900 leading-relaxed">{p.title}</h3>
                  <p className="text-xs text-gray-400 mt-1">
                    {p.authors?.join(', ') || '?'} · {p.year || '?'}
                  </p>
                  <p className="text-xs text-gray-400">{p.venue || ''}</p>
                  <div className="flex items-center gap-3 mt-2">
                    {p.doi && <span className="text-xs text-gray-400">DOI: {p.doi}</span>}
                    {p.citation_count !== null && (
                      <span className="badge-blue">被引 {p.citation_count}</span>
                    )}
                    <span className={`text-xs px-2 py-0.5 rounded-full ${SOURCES.find(s => s.id === p.source)?.color || 'text-gray-500 bg-gray-100'}`}>
                      {p.source}
                    </span>
                  </div>
                </div>
                {p.doi && (
                  <a href={`https://doi.org/${p.doi}`} target="_blank" rel="noreferrer"
                    className="p-2 text-gray-300 hover:text-primary-600 transition-colors">
                    <ExternalLink className="w-4 h-4" />
                  </a>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {loading && <div className="text-center py-12 text-gray-400"><Loader2 className="w-6 h-6 animate-spin mx-auto mb-2" />搜索中...</div>}
      {!loading && papers.length === 0 && query && <div className="text-center py-12 text-gray-400">未找到结果</div>}
    </div>
  );
}
