import React, { useMemo } from 'react';
import {
  AlertTriangle,
  ArrowRight,
  BookMarked,
  Bot,
  ChevronRight,
  ExternalLink,
  FileWarning,
  Files,
  Flag,
  Printer,
  Gauge,
  ListChecks,
  LocateFixed,
  ScanLine,
  ScanSearch,
  ShieldAlert,
  Sparkles,
} from 'lucide-react';

const DEMO_REPORT = {
  meta: {
    paper_title: '模板示例：本科毕业论文审查报告',
    task_id: 'template-demo',
    overall_score: 0.71,
    duration: 18.4,
  },
  summary: {
    finding_count: 12,
    error_count: 0,
  },
  sections: {
    format_check: {
      issues: [
        {
          type: 'title_format',
          severity: 'major',
          line: 3,
          column: 1,
          description: '论文封面标题字体与模板要求不一致',
          suggestion: '将封面标题调整为指定字号与加粗样式',
        },
        {
          type: 'missing_section',
          severity: 'minor',
          section: 'related work',
          description: "缺少 'related work' 章节",
          suggestion: '补充相关工作综述并说明与现有研究的差异',
        },
        {
          type: 'caption_alignment',
          severity: 'minor',
          line: 42,
          column: 3,
          description: '图表标题未按学校模板要求居中',
          suggestion: '统一图表标题的居中与编号样式',
        },
      ],
    },
    reference_check: {
      issues: [
        {
          type: 'reference_missing',
          severity: 'critical',
          section: 'references',
          description: '存在正文引用但未形成完整参考文献列表',
          suggestion: '补齐参考文献章节并检查编号顺序',
        },
        {
          type: 'doi_missing',
          severity: 'major',
          section: 'references',
          description: '3 条英文文献缺少 DOI 信息',
          suggestion: '补充 DOI 或稳定访问链接，提升可验证性',
        },
      ],
      total_refs: 15,
      matched: 12,
      doi_missing_count: 3,
      score: 0.76,
    },
  },
  findings: [
    {
      category: 'format',
      severity: 'major',
      type: 'title_format',
      description: '封面标题字体与模板不一致',
      suggestion: '按模板统一封面字体、字号与加粗规则',
      location: { line: 3, column: 1 },
    },
    {
      category: 'reference',
      severity: 'critical',
      type: 'reference_missing',
      description: '正文引用与参考文献列表不完整',
      suggestion: '补齐 reference 章节并逐条核对引用',
      location: { section: 'references' },
    },
  ],
  evidence_records: [
    {
      evidence_id: 'template-ev-1',
      stage: 'format',
      severity: 'major',
      claim: '封面标题字体与模板不一致',
      suggestion: '改为模板指定字体与字号',
      location: { line: 3, column: 1, page: 1 },
    },
    {
      evidence_id: 'template-ev-2',
      stage: 'reference',
      severity: 'critical',
      claim: '正文引用存在，但 reference 章节缺失完整条目',
      suggestion: '补齐参考文献列表，并校对编号映射',
      location: { section: 'references', page: 8 },
    },
    {
      evidence_id: 'template-ev-3',
      stage: 'format',
      severity: 'minor',
      claim: '图 2 标题未居中',
      suggestion: '统一图题对齐与编号',
      location: { line: 42, page: 5 },
    },
  ],
  advice_report: {
    priorities: [
      {
        priority: 'critical',
        title: '先修复影响提交的硬性问题',
        actions: [
          '补齐参考文献章节并逐条核对正文引用映射',
          '确保每条外文文献具备 DOI 或稳定检索路径',
        ],
      },
      {
        priority: 'major',
        title: '再修复模板一致性问题',
        actions: [
          '统一封面、目录、正文标题层级的格式样式',
          '对图表标题、页眉页脚与行距做整体验证',
        ],
      },
    ],
  },
  workflow: {
    graph: {
      ingest: { stage: 'ingest', status: 'completed', critical: true, dependencies: [], worker_binding: 'file_loader' },
      format: { stage: 'format_check', status: 'completed', critical: true, dependencies: ['ingest'], worker_binding: 'format_checker' },
      reference: { stage: 'reference_validate', status: 'completed', critical: true, dependencies: ['format'], worker_binding: 'reference_checker' },
      report: { stage: 'report', status: 'completed', critical: true, dependencies: ['reference'], worker_binding: 'report_builder' },
    },
    events: [
      { event_type: 'started', stage: 'ingest', timestamp: 1710000000 },
      { event_type: 'completed', stage: 'format_check', timestamp: 1710000005 },
      { event_type: 'completed', stage: 'reference_validate', timestamp: 1710000010 },
      { event_type: 'completed', stage: 'report', timestamp: 1710000012 },
    ],
  },
};

export default function ReviewStudio({
  results,
  selectedResultId,
  onSelectResult,
  detailTarget,
  onSelectWorkflow,
  onSelectEvidence,
  onJumpEvidence,
  question,
  onQuestionChange,
  onAskQuestion,
  answer,
  asking,
  sourceSnippet,
  snippetLoading,
  onOpenFormalReport,
  onPrintFormalReport,
  reportFileUrl,
}) {
  const selectedEntry = useMemo(
    () => results.find((item) => item.id === selectedResultId) || null,
    [results, selectedResultId]
  );
  const review = selectedEntry?.review || DEMO_REPORT;
  const usingTemplate = !selectedEntry;

  const formatIssues = useMemo(() => extractFormatIssues(review), [review]);
  const referenceIssues = useMemo(() => extractReferenceIssues(review), [review]);
  const contentHighlights = useMemo(() => extractContentHighlights(review), [review]);
  const evidenceRecords = review.evidence_records || [];
  const priorities = review.advice_report?.priorities || [];
  const summaryCards = buildSummaryCards(review, formatIssues, referenceIssues, evidenceRecords);
  const overview = buildOverview(review, formatIssues, referenceIssues, contentHighlights);
  const navigatorItems = buildNavigatorItems(evidenceRecords, formatIssues, referenceIssues);

  return (
    <div className="space-y-8">
      <section className="report-hero overflow-hidden">
        <div className="grid gap-8 xl:grid-cols-[1.35fr,0.85fr]">
          <div className="space-y-5">
            <div className="flex flex-wrap items-center gap-3">
              <span className="capsule capsule-primary">
                <Files className="h-3.5 w-3.5" />
                {usingTemplate ? '报告模板预览' : '结构化审查报告'}
              </span>
              <span className="capsule capsule-muted">
                <Gauge className="h-3.5 w-3.5" />
                {describeVerdict(review.meta?.overall_score)}
              </span>
              <span className="capsule capsule-muted">
                <ScanSearch className="h-3.5 w-3.5" />
                任务 {review.meta?.task_id || '-'}
              </span>
            </div>

            <div className="space-y-3">
              <div className="report-kicker">审查报告总览</div>
              <h1 className="report-title">
                {review.meta?.paper_title || '论文审查报告'}
              </h1>
              <p className="report-subtitle">
                按“执行摘要 → 风险分层 → 问题定位 → 修订行动”组织，帮助用户快速把握最需要优先修改的内容。
              </p>
            </div>

            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
              {summaryCards.map((card) => (
                <MetricCard key={card.label} {...card} />
              ))}
            </div>

            <div className="flex flex-wrap gap-3">
              <button type="button" className="btn-primary" onClick={onOpenFormalReport} disabled={usingTemplate}>
                <ExternalLink className="h-4 w-4" />
                打开打印版报告
              </button>
              <button type="button" className="btn-outline" onClick={onPrintFormalReport} disabled={usingTemplate}>
                <Printer className="h-4 w-4" />
                直接打印 / 导出 PDF
              </button>
            </div>
          </div>

          <div className="report-brief">
            <div className="report-brief-header">
              <div>
                <div className="report-brief-label">执行结论</div>
                <div className="report-brief-value">{formatScore(review.meta?.overall_score)}</div>
              </div>
              <div className={`risk-orb ${scoreToneClass(review.meta?.overall_score)}`}>
                {Math.round(normalizeScore(review.meta?.overall_score) || 0)}
              </div>
            </div>

            <div className="space-y-4">
              {overview.map((item) => (
                <div key={item.label} className="overview-row">
                  <div className="overview-row-head">
                    <item.icon className="h-4 w-4" />
                    <span>{item.label}</span>
                  </div>
                  <div className="overview-row-meta">
                    <span className={`capsule ${item.capsuleClass}`}>{item.value}</span>
                  </div>
                  <p className="overview-row-text">{item.description}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      <div className="grid gap-6">
        <SurfaceCard
          title="打印版报告预览"
          subtitle="面向打印、归档与 PDF 导出优化的正式审改报告模板"
          icon={Printer}
        >
          {usingTemplate || !reportFileUrl ? (
            <EmptyState text="完成真实审查后，这里会展示正式报告 HTML 的打印预览。" />
          ) : (
            <div className="space-y-4">
              <iframe
                title="formal-report-preview"
                src={reportFileUrl}
                className="print-preview-frame"
              />
            </div>
          )}
        </SurfaceCard>
      </div>

      <section className="space-y-6 min-w-0">
        <div className="grid gap-6 xl:grid-cols-[1.05fr,0.95fr]">
          <SurfaceCard
            title="报告队列"
            subtitle={results.length ? `${results.length} 份已生成报告` : '当前显示模板示例报告'}
            icon={Files}
          >
            <div className="space-y-3">
              {(results.length ? results : [{ id: 'template-demo', review: DEMO_REPORT }]).map((entry) => {
                const active = entry.id === (selectedEntry?.id || 'template-demo');
                const meta = entry.review?.meta || {};
                return (
                  <button
                    key={entry.id}
                    type="button"
                    onClick={() => onSelectResult?.(entry.id)}
                    className={`queue-card ${active ? 'queue-card-active' : ''}`}
                  >
                    <div className="queue-card-top">
                      <span className="queue-title">{meta.paper_title || '模板示例'}</span>
                      <span className={`queue-score ${scoreToneClass(meta.overall_score)}`}>
                        {formatScore(meta.overall_score)}
                      </span>
                    </div>
                    <div className="queue-meta">
                      <span>{meta.task_id || 'template-demo'}</span>
                      <span>{entry.review?.summary?.finding_count ?? 0} 条发现</span>
                    </div>
                  </button>
                );
              })}
            </div>
          </SurfaceCard>

          <SurfaceCard
            title="定位导航"
            subtitle="优先展示高风险证据与可定位片段"
            icon={LocateFixed}
          >
            <div className="space-y-2.5">
              {navigatorItems.length === 0 && (
                <EmptyState text="当前没有可快速定位的证据或问题。" />
              )}
              {navigatorItems.map((item) => (
                <button
                  key={item.key}
                  type="button"
                  onClick={() => onJumpEvidence?.(item.id)}
                  className="navigator-item"
                >
                  <div className={`severity-dot ${severityColor(item.severity)}`} />
                  <div className="flex-1 text-left">
                    <div className="navigator-title">{item.title}</div>
                    <div className="navigator-meta">{item.meta}</div>
                  </div>
                  <ChevronRight className="h-4 w-4 text-slate-400" />
                </button>
              ))}
            </div>
          </SurfaceCard>
        </div>

        <div className="grid gap-6">
          <SurfaceCard
            title="格式预警与定位"
            subtitle="突出格式错误、章节缺失与模板不一致，并提供清晰定位"
            icon={FileWarning}
            actionLabel={formatIssues.length ? `${formatIssues.length} 项` : '无'}
          >
            <IssueTable
              emptyText="当前未检测到格式层面的显著问题。"
              items={formatIssues}
              onLocate={onSelectEvidence}
              onJump={onJumpEvidence}
            />
          </SurfaceCard>

          <SurfaceCard
            title="文献预警与定位"
            subtitle="聚焦引用一致性、参考文献缺失、DOI 缺失与可验证性风险"
            icon={BookMarked}
            actionLabel={referenceIssues.length ? `${referenceIssues.length} 项` : '无'}
          >
            <IssueTable
              emptyText="当前未检测到显著的文献风险。"
              items={referenceIssues}
              onLocate={onSelectEvidence}
              onJump={onJumpEvidence}
            />
          </SurfaceCard>
        </div>

        <div className="grid gap-6 2xl:grid-cols-[1.05fr,0.95fr]">
          <SurfaceCard
            title="报告片段与证据链"
            subtitle="展示关键问题的证据摘要，并支持跳转到对应报告片段"
            icon={ShieldAlert}
          >
            <div className="space-y-4">
              {evidenceRecords.length === 0 && (
                <EmptyState text="当前报告暂无可定位证据。" />
              )}
              {evidenceRecords.map((record) => (
                <div
                  key={record.evidence_id}
                  id={`report-evidence-${slugify(record.evidence_id)}`}
                  className="evidence-card"
                >
                  <div className="evidence-card-head">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className={`severity-pill ${severityPillClass(record.severity)}`}>{record.severity || 'info'}</span>
                      <span className="mini-meta">{record.stage || '-'}</span>
                      <span className="mini-meta">{formatLocation(record.location)}</span>
                    </div>
                  </div>
                  <h4 className="evidence-card-title">{record.claim || '未命名 evidence'}</h4>
                  {record.suggestion && (
                    <p className="evidence-card-text">建议：{record.suggestion}</p>
                  )}
                  <div className="evidence-card-actions">
                    <button type="button" className="btn-primary" onClick={() => onJumpEvidence?.(record.evidence_id)}>
                      跳转到对应片段
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </SurfaceCard>

          <SurfaceCard
            title="原文片段联动预览"
            subtitle="点击任一证据后，在这里查看论文原文中的对应位置"
            icon={ScanLine}
          >
            <SourceSnippetPanel snippetLoading={snippetLoading} sourceSnippet={sourceSnippet} />
          </SurfaceCard>
        </div>

        <div className="grid gap-6 2xl:grid-cols-[1fr,1fr]">
          <SurfaceCard
            title="审改行动清单"
            subtitle="按照风险优先级输出明确修订动作"
            icon={ListChecks}
          >
            <div className="space-y-4">
              {priorities.length === 0 && (
                <EmptyState text="当前没有生成审改行动建议。" />
              )}
              {priorities.map((block) => (
                <div key={block.title} className="priority-card">
                  <div className="priority-head">
                    <span className={`severity-pill ${severityPillClass(block.priority)}`}>{block.priority}</span>
                    <span className="priority-title">{block.title}</span>
                  </div>
                  <div className="space-y-2.5">
                    {(block.actions || []).map((action, index) => (
                      <div key={`${block.title}-${index}`} className="priority-item">
                        <ArrowRight className="h-4 w-4 text-primary-600" />
                        <span>{action}</span>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </SurfaceCard>

          <SurfaceCard
            title="内容审查摘录"
            subtitle="保留最影响论文质量的写作与结构问题"
            icon={Flag}
          >
            <div className="space-y-3">
              {contentHighlights.length === 0 && (
                <EmptyState text="当前没有可展示的内容审查摘录。" />
              )}
              {contentHighlights.map((item, index) => (
                <div key={`content-${index}`} className="content-item">
                  <div className="content-item-head">
                    <span className={`severity-pill ${severityPillClass(item.severity)}`}>{item.severity || 'info'}</span>
                    <span className="mini-meta">{item.location || '全文'}</span>
                  </div>
                  <p className="content-item-text">{item.description}</p>
                </div>
              ))}
            </div>
          </SurfaceCard>
        </div>

        <SurfaceCard
          title="报告问答"
          subtitle="围绕当前结构化报告继续追问最关键的修改建议"
          icon={Bot}
        >
          <div className="space-y-4">
            <div className="rounded-2xl border border-slate-200 bg-white/70 p-4">
              <div className="mb-2 text-xs font-semibold uppercase tracking-[0.24em] text-slate-500">问题输入</div>
              <textarea
                value={question}
                onChange={(event) => onQuestionChange?.(event.target.value)}
                placeholder="例如：请按优先级总结最需要先改的 3 个问题，并说明定位依据。"
                className="min-h-28 w-full resize-y border-0 bg-transparent p-0 text-sm leading-7 text-slate-700 outline-none placeholder:text-slate-400"
              />
            </div>
            <div className="flex flex-wrap gap-3">
              <button
                type="button"
                onClick={onAskQuestion}
                disabled={asking || usingTemplate}
                className="btn-primary inline-flex items-center gap-2 disabled:cursor-not-allowed disabled:opacity-60"
              >
                <Sparkles className="h-4 w-4" />
                {asking ? '思考中...' : '生成报告问答'}
              </button>
              {usingTemplate && (
                <span className="capsule capsule-muted">模板模式下不发起真实问答</span>
              )}
            </div>
            <div className="answer-panel">
              {answer || '这里将显示围绕当前论文审查结果生成的解释、优先级建议与答辩式说明。'}
            </div>
          </div>
        </SurfaceCard>
      </section>
    </div>
  );
}

function SurfaceCard({ title, subtitle, icon: Icon, actionLabel, children }) {
  return (
    <section className="surface-card">
      <div className="surface-card-head">
        <div className="flex items-start gap-3">
          {Icon && (
            <div className="surface-card-icon">
              <Icon className="h-4 w-4" />
            </div>
          )}
          <div>
            <h3 className="surface-card-title">{title}</h3>
            {subtitle && <p className="surface-card-subtitle">{subtitle}</p>}
          </div>
        </div>
        {actionLabel && <span className="capsule capsule-muted">{actionLabel}</span>}
      </div>
      {children}
    </section>
  );
}

function MetricCard({ label, value, detail, toneClass, icon: Icon }) {
  return (
    <div className="metric-card">
      <div className="metric-card-head">
        <span className="metric-label">{label}</span>
        {Icon && <Icon className={`h-4 w-4 ${toneClass}`} />}
      </div>
      <div className={`metric-value ${toneClass}`}>{value}</div>
      <div className="metric-detail">{detail}</div>
    </div>
  );
}

function IssueTable({ items, emptyText, onLocate, onJump }) {
  if (!items.length) {
    return <EmptyState text={emptyText} />;
  }

  return (
    <div className="overflow-hidden rounded-2xl border border-slate-200">
      <div className="min-w-0 overflow-x-auto">
        <table className="w-full min-w-full table-fixed text-left">
          <thead className="bg-slate-50/80 text-xs uppercase tracking-[0.22em] text-slate-500">
            <tr>
              <th className="w-[108px] px-4 py-3 font-medium">严重度</th>
              <th className="w-[31%] px-4 py-3 font-medium">问题</th>
              <th className="w-[19%] px-4 py-3 font-medium">定位</th>
              <th className="w-[30%] px-4 py-3 font-medium">建议</th>
              <th className="w-[132px] px-4 py-3 font-medium text-right">动作</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-200 bg-white/80 text-sm text-slate-700">
            {items.map((item) => (
              <tr key={item.key} className="align-top">
                <td className="px-4 py-4">
                  <span className={`severity-pill ${severityPillClass(item.severity)}`}>{item.severity || 'info'}</span>
                </td>
                <td className="px-4 py-4">
                  <div className="break-words font-medium text-slate-900">{item.title}</div>
                  {item.type && <div className="mt-1 text-xs text-slate-500">{item.type}</div>}
                </td>
                <td className="px-4 py-4 text-slate-600">
                  <div className="break-words">{item.locator}</div>
                </td>
                <td className="px-4 py-4 text-slate-600">
                  <div className="break-words">{item.suggestion || '建议人工复核后修订'}</div>
                </td>
                <td className="px-4 py-4">
                  <div className="flex flex-wrap justify-end gap-2">
                    {item.evidenceId && (
                      <button type="button" className="btn-outline" onClick={() => onLocate?.(item.evidenceId)}>
                        详情
                      </button>
                    )}
                    {item.evidenceId && (
                      <button type="button" className="btn-primary" onClick={() => onJump?.(item.evidenceId)}>
                        跳转
                      </button>
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function EmptyState({ text }) {
  return (
    <div className="rounded-2xl border border-dashed border-slate-300 bg-slate-50/70 px-4 py-8 text-center text-sm text-slate-500">
      <Files className="mx-auto mb-3 h-5 w-5 text-slate-400" />
      <div className="mb-1 text-xs font-semibold uppercase tracking-[0.22em] text-slate-400">暂无内容</div>
      {text}
    </div>
  );
}

function SourceSnippetPanel({ snippetLoading, sourceSnippet }) {
  if (snippetLoading) {
    return <EmptyState text="正在加载与当前证据对应的原文片段。" />;
  }

  if (!sourceSnippet) {
    return <EmptyState text="点击任一证据后，这里会展示源论文中的对应片段。" />;
  }

  const excerpt = sourceSnippet?.snippet?.excerpt || [];
  const focusLine = sourceSnippet?.snippet?.focus_line;
  return (
    <div className="space-y-4">
      <div className="snippet-header">
        <div>
          <div className="snippet-title">{sourceSnippet.source_name || '原文片段'}</div>
          <div className="snippet-meta">{sourceSnippet.claim || '未提供问题摘要'}</div>
        </div>
        <span className="capsule capsule-muted">{sourceSnippet?.snippet?.source_kind || 'unknown'}</span>
      </div>
      <div className="snippet-summary-grid">
        <div className="snippet-summary-card">
          <div className="snippet-summary-label">定位摘要</div>
          <div className="snippet-summary-value">{sourceSnippet?.snippet?.summary || '未提供定位信息'}</div>
        </div>
        <div className="snippet-summary-card">
          <div className="snippet-summary-label">焦点行</div>
          <div className="snippet-summary-value">{focusLine || '章节匹配 / 未知'}</div>
        </div>
      </div>
      <div className="snippet-panel">
        {excerpt.length === 0 && (
          <div className="text-sm text-slate-500">当前没有可展示的原文片段。</div>
        )}
        {excerpt.map((line, index) => (
          <div
            key={`${line.line_number || 'line'}-${index}`}
            className={`snippet-line ${focusLine && line.line_number === focusLine ? 'snippet-line-focused' : ''}`}
          >
            <div className="snippet-line-number">{line.line_number || '·'}</div>
            <pre className="snippet-line-text">{line.text || ''}</pre>
          </div>
        ))}
      </div>
    </div>
  );
}

function buildSummaryCards(review, formatIssues, referenceIssues, evidenceRecords) {
  return [
    {
      label: '综合评分',
      value: formatScore(review.meta?.overall_score),
      detail: describeVerdict(review.meta?.overall_score),
      toneClass: scoreToneClass(review.meta?.overall_score),
      icon: Gauge,
    },
    {
      label: '格式预警',
      value: String(formatIssues.length),
      detail: '模板、结构与版式问题',
      toneClass: 'text-amber-600',
      icon: FileWarning,
    },
    {
      label: '文献预警',
      value: String(referenceIssues.length),
      detail: '引用一致性与 DOI 风险',
      toneClass: 'text-rose-600',
      icon: BookMarked,
    },
    {
      label: '证据记录',
      value: String(evidenceRecords.length),
      detail: '可定位证据记录',
      toneClass: 'text-sky-600',
      icon: ShieldAlert,
    },
  ];
}

function buildOverview(review, formatIssues, referenceIssues, contentHighlights) {
  return [
    {
      label: '格式结构',
      value: `${countBySeverity(formatIssues, 'major') + countBySeverity(formatIssues, 'critical')} 项重点问题`,
      description: formatIssues[0]?.title || '暂无显著格式风险',
      icon: FileWarning,
      capsuleClass: 'capsule-warn',
    },
    {
      label: '参考文献',
      value: `${countBySeverity(referenceIssues, 'major') + countBySeverity(referenceIssues, 'critical')} 项需优先修复`,
      description: referenceIssues[0]?.title || '文献结构基本正常',
      icon: BookMarked,
      capsuleClass: 'capsule-danger',
    },
    {
      label: '内容表达',
      value: `${contentHighlights.length} 条摘录`,
      description: contentHighlights[0]?.description || '暂无内容层摘录',
      icon: AlertTriangle,
      capsuleClass: 'capsule-muted',
    },
  ];
}

function buildNavigatorItems(evidenceRecords, formatIssues, referenceIssues) {
  const evidenceItems = evidenceRecords.slice(0, 4).map((record) => ({
    key: `evidence-${record.evidence_id}`,
    kind: 'evidence',
    id: record.evidence_id,
    title: record.claim || '未命名 evidence',
    meta: `${record.stage || '-'} · ${formatLocation(record.location)}`,
    severity: record.severity || 'info',
  }));

  const issueItems = [...formatIssues, ...referenceIssues].slice(0, 4).map((item) => ({
    key: `issue-${item.key}`,
    kind: 'evidence',
    id: item.evidenceId,
    title: item.title,
    meta: item.locator,
    severity: item.severity || 'info',
  }));

  return [...evidenceItems, ...issueItems].filter((item) => item.id);
}

function extractFormatIssues(review) {
  const issues = review.sections?.format_check?.issues || [];
  return issues
    .filter((issue) => issue && (issue.description || issue.type))
    .map((issue, index) => ({
      key: `format-${index}`,
      title: issue.description || issue.type || '未命名格式问题',
      type: issue.type || 'format',
      severity: issue.severity || 'info',
      locator: formatLocation(issue),
      suggestion: issue.suggestion || '按模板要求修订',
      evidenceId: findEvidenceId(review, issue.description),
    }));
}

function extractReferenceIssues(review) {
  const issues = review.sections?.reference_check?.issues || review.sections?.reference_check?.details?.issues || [];
  return issues
    .filter((issue) => issue && (issue.description || issue.type))
    .map((issue, index) => ({
      key: `reference-${index}`,
      title: issue.description || issue.type || '未命名文献问题',
      type: issue.type || 'reference',
      severity: issue.severity || 'info',
      locator: formatLocation(issue),
      suggestion: issue.suggestion || '补充文献定位与核验信息',
      evidenceId: findEvidenceId(review, issue.description),
    }));
}

function extractContentHighlights(review) {
  const content = review.sections?.content_review || {};
  const blocks = Object.values(content).filter(Boolean);
  const issues = [];

  blocks.forEach((block) => {
    const nestedIssues = Array.isArray(block?.issues) ? block.issues : Array.isArray(block) ? block : [];
    nestedIssues.forEach((item) => {
      if (typeof item === 'string') {
        issues.push({ description: item, severity: 'info', location: '全文' });
        return;
      }
      if (item && typeof item === 'object') {
        issues.push({
          description: item.description || item.issue || '内容层问题',
          severity: item.severity || 'minor',
          location: item.location || item.section || '全文',
        });
      }
    });
  });

  return issues.slice(0, 6);
}

function findEvidenceId(review, description) {
  if (!description) return null;
  const hit = (review.evidence_records || []).find((record) => record.claim === description);
  return hit?.evidence_id || null;
}

function countBySeverity(items, severity) {
  return items.filter((item) => item.severity === severity).length;
}

function normalizeScore(score) {
  if (typeof score !== 'number' || Number.isNaN(score)) return null;
  return score <= 1 ? score * 100 : score;
}

function formatScore(score) {
  const normalized = normalizeScore(score);
  if (normalized === null) return '-';
  return `${Math.round(normalized)}分`;
}

function describeVerdict(score) {
  const normalized = normalizeScore(score);
  if (normalized === null) return '待评估';
  if (normalized >= 85) return '可提交，仅需轻微修订';
  if (normalized >= 70) return '建议修订后提交';
  if (normalized >= 55) return '存在明显问题，需较大修订';
  return '当前不建议直接提交';
}

function scoreToneClass(score) {
  const normalized = normalizeScore(score);
  if (normalized === null) return 'text-slate-500';
  if (normalized >= 85) return 'text-emerald-600';
  if (normalized >= 70) return 'text-blue-600';
  if (normalized >= 55) return 'text-amber-600';
  return 'text-rose-600';
}

function severityPillClass(severity) {
  if (severity === 'critical') return 'pill-critical';
  if (severity === 'major') return 'pill-major';
  if (severity === 'minor') return 'pill-minor';
  return 'pill-info';
}

function severityColor(severity) {
  if (severity === 'critical') return 'bg-rose-500';
  if (severity === 'major') return 'bg-amber-500';
  if (severity === 'minor') return 'bg-sky-500';
  return 'bg-slate-400';
}

function statusPillClass(status) {
  if (status === 'completed') return 'pill-completed';
  if (status === 'running') return 'pill-running';
  if (status === 'skipped') return 'pill-skipped';
  return 'pill-pending';
}

function formatLocation(location) {
  if (!location || typeof location !== 'object') return '未提供定位信息';
  const fields = [];
  if (location.page) fields.push(`第 ${location.page} 页`);
  if (location.line) fields.push(`行 ${location.line}`);
  if (location.column) fields.push(`列 ${location.column}`);
  if (location.section) fields.push(`章节 ${location.section}`);
  if (fields.length) return fields.join(' · ');
  return '未提供定位信息';
}

function simplifyStage(stage) {
  if (!stage) return stage;
  if (stage.includes('format')) return 'format';
  if (stage.includes('reference')) return 'reference';
  if (stage.includes('content')) return 'content';
  return stage;
}

function formatTimestamp(timestamp) {
  if (!timestamp) return '-';
  try {
    return new Date(timestamp * 1000).toLocaleString();
  } catch {
    return String(timestamp);
  }
}

function slugify(value) {
  return String(value || 'fragment')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '');
}
