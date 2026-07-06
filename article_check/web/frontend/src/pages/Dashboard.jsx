import React from 'react';
import { Link } from 'react-router-dom';
import { FileText, Search, BookOpen, CheckSquare, BarChart3, TrendingUp, FileCheck, Activity } from 'lucide-react';

export default function Dashboard({ status }) {
  const cards = [
    { label: '论文审查', value: '格式+内容+文献', icon: FileText, color: 'text-blue-600', bg: 'bg-blue-50', to: '/review' },
    { label: '文献检索', value: '5 源并行搜索', icon: Search, color: 'text-emerald-600', bg: 'bg-emerald-50', to: '/literature' },
    { label: '自动综述', value: '聚类+趋势+图谱', icon: BookOpen, color: 'text-violet-600', bg: 'bg-violet-50', to: '/survey' },
    { label: '投稿检查', value: 'PASS/FAIL 清单', icon: CheckSquare, color: 'text-amber-600', bg: 'bg-amber-50', to: '/submission' },
  ];
  const features = [
    { icon: FileText, title: '格式审查', desc: 'LaTeX/Word 规则引擎 + 4 模板 + 18 条规则，零 token 消耗', color: 'text-blue-500' },
    { icon: Search, title: '文献检索', desc: '5 学术数据源并发搜索，自动去重排序', color: 'text-emerald-500' },
    { icon: TrendingUp, title: '引文分析', desc: '前向/后向引文网络，共引矩阵，遗漏文献发现', color: 'text-violet-500' },
    { icon: FileCheck, title: '投稿就绪', desc: '期刊指南 + 阶段规则 + PASS/FAIL 报告', color: 'text-amber-500' },
    { icon: Activity, title: '弹性并行', desc: '自适应并发控制 + 流式批处理 + CPM 调度', color: 'text-rose-500' },
    { icon: CheckSquare, title: '自动修正', desc: '一键修复字体/边距/页码/标题样式', color: 'text-cyan-500' },
  ];
  return (
    <div className="max-w-6xl mx-auto space-y-8">
      {/* Hero */}
      <div className="text-center py-8">
        <h1 className="text-3xl font-bold text-gray-900">学术论文审查与文献调研系统</h1>
        <p className="mt-2 text-gray-500 max-w-2xl mx-auto">
          格式审查 · 文献检索 · 引文分析 · 自动综述 · 投稿检查 · 批量并行
        </p>
        <div className="flex items-center justify-center gap-4 mt-4 text-xs text-gray-400">
          <span className="flex items-center gap-1"><span className={`w-2 h-2 rounded-full ${status ? 'bg-green-500' : 'bg-red-400'}`} />API {status ? '在线' : '离线'}</span>
          <span>DeepSeek {status?.deepseek_api ? '已配置' : '未配置'}</span>
          <span>{status?.templates || 0} 个模板</span>
          <span>v0.3.0</span>
        </div>
      </div>

      {/* Quick cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {cards.map(({ label, value, icon: Icon, color, bg, to }) => (
          <Link key={to} to={to} className="card p-5 hover:shadow-lg transition-all">
            <div className={`w-10 h-10 rounded-lg ${bg} flex items-center justify-center mb-3`}>
              <Icon className={`w-5 h-5 ${color}`} />
            </div>
            <div className="text-sm font-medium text-gray-900">{label}</div>
            <div className="text-xs text-gray-400 mt-0.5">{value}</div>
          </Link>
        ))}
      </div>

      {/* Feature grid */}
      <div>
        <h2 className="text-lg font-semibold text-gray-900 mb-4">核心能力</h2>
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {features.map(({ icon: Icon, title, desc, color }) => (
            <div key={title} className="card p-5">
              <Icon className={`w-5 h-5 ${color} mb-2`} />
              <h3 className="font-medium text-sm text-gray-900">{title}</h3>
              <p className="text-xs text-gray-400 mt-1">{desc}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
