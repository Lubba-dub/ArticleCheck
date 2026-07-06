import React, { useState, useEffect } from 'react';
import { Routes, Route, Link, useLocation } from 'react-router-dom';
import {
  FileText, Search, BookOpen, CheckSquare, BarChart3,
  Upload, Settings, Github, Menu, X, FileCheck,
  CitationIcon, Globe, PenTool
} from 'lucide-react';
import Dashboard from './pages/Dashboard';
import ReviewPage from './pages/ReviewPage';
import LiteraturePage from './pages/LiteraturePage';
import SubmissionPage from './pages/SubmissionPage';
import SurveyPage from './pages/SurveyPage';
import { api } from './api/client';

const NAV = [
  { path: '/', label: '控制台', icon: BarChart3 },
  { path: '/review', label: '论文审查', icon: FileText },
  { path: '/literature', label: '文献检索', icon: Search },
  { path: '/survey', label: '文献综述', icon: BookOpen },
  { path: '/submission', label: '投稿检查', icon: CheckSquare },
];

export default function App() {
  const [sidebar, setSidebar] = useState(false);
  const [status, setStatus] = useState(null);
  const location = useLocation();

  useEffect(() => {
    api.status().then(r => setStatus(r.data)).catch(() => setStatus(null));
  }, []);

  return (
    <div className="min-h-screen flex">
      {/* Sidebar */}
      <aside className={`fixed inset-y-0 left-0 z-50 w-64 bg-white border-r border-gray-100 transform transition-transform duration-200 lg:translate-x-0 lg:static lg:inset-auto ${sidebar ? 'translate-x-0' : '-translate-x-full'}`}>
        <div className="flex items-center justify-between h-16 px-6 border-b border-gray-100">
          <Link to="/" className="flex items-center gap-2 font-semibold text-lg">
            <FileCheck className="w-6 h-6 text-primary-600" />
            <span>Article<span className="text-primary-600">Check</span></span>
          </Link>
          <button onClick={() => setSidebar(false)} className="lg:hidden"><X className="w-5 h-5" /></button>
        </div>
        <nav className="p-4 space-y-1">
          {NAV.map(({ path, label, icon: Icon }) => (
            <Link key={path} to={path}
              className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                location.pathname === path ? 'bg-primary-50 text-primary-700' : 'text-gray-600 hover:bg-gray-50'
              }`}
              onClick={() => setSidebar(false)}
            >
              <Icon className="w-4 h-4" /> {label}
            </Link>
          ))}
          <div className="pt-4 mt-4 border-t border-gray-100">
            <div className="flex items-center gap-3 px-3 py-2 text-xs text-gray-400">
              <span className={`w-2 h-2 rounded-full ${status ? 'bg-green-500' : 'bg-red-400'}`} />
              {status ? `API ${status.version}` : 'API 离线'}
            </div>
            <div className="px-3 py-1 text-xs text-gray-400">
              {status?.templates && `${status.templates} 个模板 · ${status.lit_sources?.length || 0} 个数据源`}
            </div>
          </div>
        </nav>
      </aside>

      {/* Overlay */}
      {sidebar && <div className="fixed inset-0 bg-black/20 z-40 lg:hidden" onClick={() => setSidebar(false)} />}

      {/* Main */}
      <div className="flex-1 min-w-0">
        <header className="sticky top-0 z-30 bg-white/80 backdrop-blur-sm border-b border-gray-100">
          <div className="flex items-center justify-between h-16 px-4 lg:px-8">
            <button onClick={() => setSidebar(true)} className="lg:hidden"><Menu className="w-5 h-5" /></button>
            <div className="flex items-center gap-3">
              <span className="text-sm text-gray-400 hidden sm:inline">学术论文审查与文献调研系统</span>
            </div>
            <div className="flex items-center gap-2">
              <a href="https://github.com/Lubba-dub/ArticleCheck" target="_blank" rel="noreferrer"
                className="p-2 text-gray-400 hover:text-gray-600 transition-colors">
                <Github className="w-5 h-5" />
              </a>
            </div>
          </div>
        </header>
        <main className="p-4 lg:p-8">
          <Routes>
            <Route path="/" element={<Dashboard status={status} />} />
            <Route path="/review" element={<ReviewPage />} />
            <Route path="/literature" element={<LiteraturePage />} />
            <Route path="/survey" element={<SurveyPage />} />
            <Route path="/submission" element={<SubmissionPage />} />
          </Routes>
        </main>
      </div>
    </div>
  );
}
