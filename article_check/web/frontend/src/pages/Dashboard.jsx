import React from 'react';
import { Link } from 'react-router-dom';
import { Activity, FileCheck, FileText, ShieldAlert, Sparkles, TrendingUp } from 'lucide-react';

export default function Dashboard({ status }) {
  const cards = [
    { label: '论文审查', value: '正式报告模板 + 证据定位', icon: FileText, to: '/review' },
  ];
  const features = [
    { icon: FileText, title: '正式报告模板', desc: '将格式、文献、内容与 evidence 收束为统一审查报告', tone: 'text-primary-700' },
    { icon: ShieldAlert, title: '证据定位', desc: '支持问题定位、证据片段跳转与细节展开', tone: 'text-rose-700' },
    { icon: TrendingUp, title: '文献风险分析', desc: '缺失 DOI、引用不一致、相关工作遗漏统一汇总', tone: 'text-amber-700' },
    { icon: Activity, title: '批量并行审查', desc: '单篇、批量、流式结果进入同一工作台', tone: 'text-sky-700' },
    { icon: Sparkles, title: '报告问答', desc: '围绕结构化报告继续追问修改优先级与依据', tone: 'text-violet-700' },
    { icon: FileCheck, title: '导出与归档', desc: '同时生成建议报告与正式审改报告多种格式', tone: 'text-emerald-700' },
  ];
  return (
    <div className="page-stack">
      <section className="hero-banner">
        <div className="hero-grid">
          <div className="space-y-5">
            <div className="capsule capsule-primary">Academic Review System</div>
            <h1 className="hero-title">把论文审查做成一份真正可交付的正式报告</h1>
            <p className="hero-text">
              面向“本科毕业论文格式核查 + 参考文献有效性验证 + 审改建议输出”的统一工作台。当前版本收束为 WebDemo + FastAPI 网关 + Dify 多应用编排 + 官方认证接入的最小平台交付形态。
            </p>
            <div className="flex flex-wrap gap-3">
              <Link to="/review" className="btn-primary">进入报告工作台</Link>
            </div>
          </div>

          <div className="hero-panel">
            <div className="hero-panel-row">
              <span>系统状态</span>
              <span className={`capsule ${status ? 'capsule-success' : 'capsule-danger'}`}>{status ? '在线' : '离线'}</span>
            </div>
            <div className="hero-panel-row">
              <span>Dify</span>
              <span>{status?.dify_enabled ? '已接入' : '待配置'}</span>
            </div>
            <div className="hero-panel-row">
              <span>模板数量</span>
              <span>{status?.templates || 0}</span>
            </div>
            <div className="hero-panel-row">
              <span>AI Provider</span>
              <span>{status?.ai_provider ? String(status.ai_provider).toUpperCase() : '-'}</span>
            </div>
          </div>
        </div>
      </section>

      <section className="grid gap-4 lg:grid-cols-1">
        {cards.map(({ label, value, icon: Icon, to }) => (
          <Link key={to} to={to} className="nav-card">
            <div className="nav-card-icon">
              <Icon className="h-5 w-5" />
            </div>
            <div className="space-y-1">
              <div className="nav-card-title">{label}</div>
              <div className="nav-card-text">{value}</div>
            </div>
          </Link>
        ))}
      </section>

      <section className="grid gap-6 xl:grid-cols-[1.2fr,0.8fr]">
        <div className="surface-card">
          <div className="surface-card-head">
            <div>
              <h2 className="surface-card-title">设计目标</h2>
              <p className="surface-card-subtitle">从调试视图升级到正式审改报告与证据工作台</p>
            </div>
          </div>
          <div className="grid gap-4 md:grid-cols-2">
            {features.map(({ icon: Icon, title, desc, tone }) => (
              <div key={title} className="feature-card">
                <div className={`feature-icon ${tone}`}>
                  <Icon className="h-5 w-5" />
                </div>
                <div>
                  <h3 className="feature-title">{title}</h3>
                  <p className="feature-text">{desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="surface-card">
          <div className="surface-card-head">
            <div>
              <h2 className="surface-card-title">当前主线</h2>
              <p className="surface-card-subtitle">围绕一份结构化报告串起所有入口</p>
            </div>
          </div>
          <div className="space-y-4">
            {[
              '上传论文或批量目录后，统一生成 article_check.ai_review.v1 结构化报告',
              '格式预警、文献预警、内容摘录和 evidence 记录汇入同一份报告',
              '工作流节点、证据链、报告问答与导出视图共用同一数据模型',
              '正式审改报告与建议报告作为平台 WebDemo 的核心交付物',
            ].map((item) => (
              <div key={item} className="timeline-item">
                <div className="timeline-dot" />
                <div className="timeline-text">{item}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="surface-card">
        <div className="surface-card-head">
          <div>
            <h2 className="surface-card-title">推荐入口</h2>
            <p className="surface-card-subtitle">如果你要看新设计，请直接进入新的报告工作台</p>
          </div>
        </div>
        <Link to="/review" className="inline-flex items-center gap-2 text-sm font-medium text-primary-700">
          打开论文审查报告页面 <FileText className="h-4 w-4" />
        </Link>
      </section>
    </div>
  );
}
