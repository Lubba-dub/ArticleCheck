import * as fs from "fs";
import * as os from "os";
import * as path from "path";
import { execFile } from "child_process";
import * as vscode from "vscode";

type ReviewPayload = {
  report_format?: string;
  meta?: {
    paper_title?: string;
    task_id?: string;
    overall_score?: number;
    duration?: number;
    source_paper_path?: string | null;
  };
  summary?: {
    finding_count?: number;
    error_count?: number;
    report_markdown_path?: string | null;
    report_json_path?: string | null;
    suggestion_report_path?: string | null;
    formal_report_markdown_path?: string | null;
    formal_report_html_path?: string | null;
  };
  advice_report?: {
    priorities?: Array<{
      priority?: string;
      title?: string;
      actions?: string[];
    }>;
    report_path?: string | null;
  };
  formal_report?: {
    markdown_path?: string | null;
    html_path?: string | null;
    json_path?: string | null;
  };
  workflow?: {
    graph?: Record<string, {
      stage?: string;
      status?: string;
      critical?: boolean;
      dependencies?: string[];
      worker_binding?: string | null;
    }>;
    events?: Array<{
      event_type?: string;
      stage?: string;
      timestamp?: number;
    }>;
  };
  evidence_records?: Array<{
    evidence_id?: string;
    stage?: string;
    severity?: string;
    claim?: string;
    suggestion?: string | null;
    location?: Record<string, unknown>;
  }>;
  findings?: Array<{
    category?: string;
    severity?: string;
    type?: string;
    description?: string;
    suggestion?: string | null;
    location?: Record<string, unknown>;
  }>;
  errors?: string[];
};

type BatchPayload = {
  report_format?: string;
  summary?: {
    paper_count?: number;
    average_score?: number;
    total_findings?: number;
  };
  items?: ReviewPayload[];
};

class ArticleCheckState {
  lastReportPayload: ReviewPayload | null = null;
  lastReportJsonPath: string | null = null;
  lastBatchPayload: BatchPayload | null = null;
  lastBatchJsonPath: string | null = null;
  lastReviewedFilePath: string | null = null;
}

class WorkflowTreeProvider implements vscode.TreeDataProvider<vscode.TreeItem> {
  private readonly _onDidChangeTreeData = new vscode.EventEmitter<vscode.TreeItem | undefined | null | void>();
  readonly onDidChangeTreeData = this._onDidChangeTreeData.event;

  constructor(private readonly state: ArticleCheckState) {}

  refresh(): void {
    this._onDidChangeTreeData.fire();
  }

  getTreeItem(element: vscode.TreeItem): vscode.TreeItem {
    return element;
  }

  getChildren(): vscode.TreeItem[] {
    const graph = this.state.lastReportPayload?.workflow?.graph ?? {};
    return Object.entries(graph).map(([nodeId, node]) => {
      const item = new vscode.TreeItem(`${nodeId}: ${node.stage ?? "-"}`, vscode.TreeItemCollapsibleState.None);
      item.description = node.status ?? "pending";
      item.tooltip = [
        `阶段: ${node.stage ?? "-"}`,
        `状态: ${node.status ?? "-"}`,
        `Worker: ${node.worker_binding ?? "-"}`,
        `关键节点: ${node.critical ? "是" : "否"}`,
        `依赖: ${(node.dependencies ?? []).join(", ") || "-"}`,
      ].join("\n");
      item.iconPath = new vscode.ThemeIcon(
        node.status === "completed" ? "pass-filled" :
        node.status === "running" ? "loading~spin" :
        node.status === "skipped" ? "debug-pause" : "circle-large-outline"
      );
      item.command = {
        command: "articleCheck.openWorkflowNodeDetail",
        title: "打开节点详情",
        arguments: [nodeId]
      };
      return item;
    });
  }
}

class EvidenceTreeProvider implements vscode.TreeDataProvider<vscode.TreeItem> {
  private readonly _onDidChangeTreeData = new vscode.EventEmitter<vscode.TreeItem | undefined | null | void>();
  readonly onDidChangeTreeData = this._onDidChangeTreeData.event;

  constructor(private readonly state: ArticleCheckState) {}

  refresh(): void {
    this._onDidChangeTreeData.fire();
  }

  getTreeItem(element: vscode.TreeItem): vscode.TreeItem {
    return element;
  }

  getChildren(): vscode.TreeItem[] {
    const evidence = this.state.lastReportPayload?.evidence_records ?? [];
    return evidence.map((record) => {
      const item = new vscode.TreeItem(
        `${record.stage ?? "-"}: ${record.claim ?? "-"}`,
        vscode.TreeItemCollapsibleState.None
      );
      item.description = record.severity ?? "info";
      item.tooltip = [
        `证据ID: ${record.evidence_id ?? "-"}`,
        `阶段: ${record.stage ?? "-"}`,
        `严重度: ${record.severity ?? "-"}`,
        `建议: ${record.suggestion ?? "-"}`,
        `位置: ${JSON.stringify(record.location ?? {})}`,
      ].join("\n");
      item.iconPath = new vscode.ThemeIcon(
        record.severity === "critical" ? "error" :
        record.severity === "major" ? "warning" : "info"
      );
      item.command = {
        command: "articleCheck.openEvidenceDetail",
        title: "打开证据详情",
        arguments: [record.evidence_id ?? ""]
      };
      return item;
    });
  }
}

class ArticleCheckWorkbenchProvider implements vscode.WebviewViewProvider {
  public static readonly viewType = "articleCheck.workbench";
  private view?: vscode.WebviewView;

  constructor(
    private readonly context: vscode.ExtensionContext,
    private readonly state: ArticleCheckState,
    private readonly output: vscode.OutputChannel,
    private readonly workflowTreeProvider: WorkflowTreeProvider,
    private readonly evidenceTreeProvider: EvidenceTreeProvider,
    private readonly diagnosticCollection: vscode.DiagnosticCollection
  ) {}

  resolveWebviewView(webviewView: vscode.WebviewView): void | Thenable<void> {
    this.view = webviewView;
    webviewView.webview.options = { enableScripts: true };
    webviewView.webview.html = renderWorkbenchHtml(this.state);
    webviewView.webview.onDidReceiveMessage(async (message) => {
      if (message.type === "reviewCurrent") {
        await reviewCurrentFile(
          this.context,
          this.state,
          this.output,
          this,
          this.workflowTreeProvider,
          this.evidenceTreeProvider,
          this.diagnosticCollection
        );
      }
      if (message.type === "reviewWorkspace") {
        await reviewWorkspacePapers(
          this.context,
          this.state,
          this.output,
          this,
          this.workflowTreeProvider,
          this.evidenceTreeProvider,
          this.diagnosticCollection
        );
      }
      if (message.type === "openReport") {
        if (this.state.lastReportPayload) {
          openReportPanel(this.context, this.state.lastReportPayload, this.state.lastReportJsonPath);
        }
      }
      if (message.type === "exportFormalReport") {
        await openFormalReport(this.state);
      }
      if (message.type === "openEvidenceDetail") {
        await openEvidenceDetail(this.context, this.state, String(message.evidenceId ?? ""));
      }
      if (message.type === "jumpToEvidence") {
        focusReportFragment(this.context, this.state, "evidence", String(message.evidenceId ?? ""));
      }
      if (message.type === "askWorkbenchQuestion") {
        const question = String(message.question ?? "").trim();
        if (!question) {
          this.postAnswer("请输入问题。");
          return;
        }
        if (!this.state.lastReportJsonPath) {
          this.postAnswer("当前没有结构化报告，无法回答。");
          return;
        }
        try {
          const answer = await askQuestionWithReport(this.state.lastReportJsonPath, question);
          this.postAnswer(answer);
        } catch (error) {
          this.postAnswer(`回答失败: ${String(error)}`);
        }
      }
    });
  }

  refresh(): void {
    if (this.view) {
      this.view.webview.html = renderWorkbenchHtml(this.state);
    }
  }

  postAnswer(answer: string): void {
    if (this.view) {
      this.view.webview.postMessage({ type: "answer", answer });
    }
  }
}

let lastPanel: vscode.WebviewPanel | null = null;
let lastDetailPanel: vscode.WebviewPanel | null = null;

export function activate(context: vscode.ExtensionContext): void {
  const output = vscode.window.createOutputChannel("Article Check");
  const state = new ArticleCheckState();
  const diagnosticCollection = vscode.languages.createDiagnosticCollection("articleCheck");
  const workflowTreeProvider = new WorkflowTreeProvider(state);
  const evidenceTreeProvider = new EvidenceTreeProvider(state);
  const provider = new ArticleCheckWorkbenchProvider(
    context,
    state,
    output,
    workflowTreeProvider,
    evidenceTreeProvider,
    diagnosticCollection
  );

  context.subscriptions.push(
    output,
    diagnosticCollection,
    vscode.window.registerWebviewViewProvider(ArticleCheckWorkbenchProvider.viewType, provider),
    vscode.window.registerTreeDataProvider("articleCheck.workflowTree", workflowTreeProvider),
    vscode.window.registerTreeDataProvider("articleCheck.evidenceTree", evidenceTreeProvider),
    vscode.commands.registerCommand("articleCheck.reviewCurrentFile", async () => {
      await reviewCurrentFile(
        context,
        state,
        output,
        provider,
        workflowTreeProvider,
        evidenceTreeProvider,
        diagnosticCollection
      );
    }),
    vscode.commands.registerCommand("articleCheck.reviewWorkspace", async () => {
      await reviewWorkspacePapers(
        context,
        state,
        output,
        provider,
        workflowTreeProvider,
        evidenceTreeProvider,
        diagnosticCollection
      );
    }),
    vscode.commands.registerCommand("articleCheck.openLastReport", () => {
      if (!state.lastReportPayload) {
        void vscode.window.showWarningMessage("当前没有可打开的最近报告。");
        return;
      }
      openReportPanel(context, state.lastReportPayload, state.lastReportJsonPath);
    }),
    vscode.commands.registerCommand("articleCheck.exportFormalReport", async () => {
      await openFormalReport(state);
    }),
    vscode.commands.registerCommand("articleCheck.openWorkflowNodeDetail", async (nodeId: string) => {
      await openWorkflowNodeDetail(context, state, nodeId);
    }),
    vscode.commands.registerCommand("articleCheck.openEvidenceDetail", async (evidenceId: string) => {
      await openEvidenceDetail(context, state, evidenceId);
    })
  );
}

export function deactivate(): void {
  // no-op
}

async function reviewCurrentFile(
  context: vscode.ExtensionContext,
  state: ArticleCheckState,
  output: vscode.OutputChannel,
  provider: ArticleCheckWorkbenchProvider,
  workflowTreeProvider: WorkflowTreeProvider,
  evidenceTreeProvider: EvidenceTreeProvider,
  diagnosticCollection: vscode.DiagnosticCollection
): Promise<void> {
  const editor = vscode.window.activeTextEditor;
  if (!editor) {
    void vscode.window.showWarningMessage("请先打开一篇论文文件。");
    return;
  }

  const filePath = editor.document.uri.fsPath;
  const ext = path.extname(filePath).toLowerCase();
  if (![".tex", ".ltx", ".docx", ".doc", ".pdf"].includes(ext)) {
    void vscode.window.showWarningMessage("当前文件不是受支持的论文格式。");
    return;
  }

  const tempJsonPath = await runSingleReview(filePath, output);
  if (!tempJsonPath) {
    return;
  }
  const payload = JSON.parse(fs.readFileSync(tempJsonPath, "utf8")) as ReviewPayload;
  state.lastReportPayload = payload;
  state.lastReportJsonPath = tempJsonPath;
  state.lastReviewedFilePath = filePath;
  provider.refresh();
  workflowTreeProvider.refresh();
  evidenceTreeProvider.refresh();
  applyDiagnostics(state, diagnosticCollection);
  openReportPanel(context, payload, tempJsonPath);
  void vscode.window.showInformationMessage("Article Check 审查完成。");
}

async function reviewWorkspacePapers(
  context: vscode.ExtensionContext,
  state: ArticleCheckState,
  output: vscode.OutputChannel,
  provider: ArticleCheckWorkbenchProvider,
  workflowTreeProvider: WorkflowTreeProvider,
  evidenceTreeProvider: EvidenceTreeProvider,
  diagnosticCollection: vscode.DiagnosticCollection
): Promise<void> {
  const workspaceFolder = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
  if (!workspaceFolder) {
    void vscode.window.showWarningMessage("当前没有打开工作区。");
    return;
  }

  const config = vscode.workspace.getConfiguration("articleCheck");
  const pythonPath = config.get<string>("pythonPath", "python");
  const tempJsonPath = path.join(os.tmpdir(), `article-check-batch-${Date.now()}.json`);
  output.appendLine(`[Article Check] 工作区批量审查开始: ${workspaceFolder}`);

  await vscode.window.withProgress(
    {
      location: vscode.ProgressLocation.Notification,
      title: "Article Check 正在批量审查工作区论文",
      cancellable: false
    },
    async () => {
      await execFileAsync(
        pythonPath,
        [
          "-m",
          "article_check",
          "batch",
          workspaceFolder,
          "--json-output",
          tempJsonPath
        ],
        {
          cwd: workspaceFolder,
          maxBuffer: 32 * 1024 * 1024
        }
      ).then(({ stdout, stderr }) => {
        if (stdout.trim()) {
          output.appendLine(stdout.trim());
        }
        if (stderr.trim()) {
          output.appendLine(stderr.trim());
        }
      });
    }
  );

  if (!fs.existsSync(tempJsonPath)) {
    void vscode.window.showErrorMessage("批量审查完成，但未生成汇总报告。");
    return;
  }
  state.lastBatchJsonPath = tempJsonPath;
  state.lastBatchPayload = JSON.parse(fs.readFileSync(tempJsonPath, "utf8")) as BatchPayload;

  const firstItem = state.lastBatchPayload.items?.[0];
  if (firstItem) {
    state.lastReportPayload = firstItem;
    state.lastReportJsonPath = (firstItem.summary?.report_json_path as string | null) ?? null;
    state.lastReviewedFilePath = null;
  }
  provider.refresh();
  workflowTreeProvider.refresh();
  evidenceTreeProvider.refresh();
  diagnosticCollection.clear();
  if (firstItem) {
    openReportPanel(context, firstItem, state.lastReportJsonPath);
  }
  void vscode.window.showInformationMessage("工作区批量审查完成。");
}

async function runSingleReview(filePath: string, output: vscode.OutputChannel): Promise<string | null> {
  const ext = path.extname(filePath).toLowerCase();
  const config = vscode.workspace.getConfiguration("articleCheck");
  const pythonPath = config.get<string>("pythonPath", "python");
  const reviewDepth = config.get<string>("reviewDepth", "auto");
  const workspaceFolder =
    vscode.workspace.getWorkspaceFolder(vscode.Uri.file(filePath))?.uri.fsPath ??
    path.dirname(filePath);
  const tempJsonPath = path.join(
    os.tmpdir(),
    `article-check-${Date.now()}-${path.basename(filePath, ext)}.json`
  );

  output.clear();
  output.appendLine(`[Article Check] 审查开始: ${filePath}`);
  await vscode.window.withProgress(
    {
      location: vscode.ProgressLocation.Notification,
      title: "Article Check 正在生成 AI 审查报告",
      cancellable: false
    },
    async () => {
      const args = [
        "-m",
        "article_check",
        "review",
        filePath,
        "--depth",
        reviewDepth,
        "--json-output",
        tempJsonPath
      ];
      const { stdout, stderr } = await execFileAsync(pythonPath, args, {
        cwd: workspaceFolder,
        maxBuffer: 32 * 1024 * 1024
      });
      if (stdout.trim()) {
        output.appendLine(stdout.trim());
      }
      if (stderr.trim()) {
        output.appendLine(stderr.trim());
      }
    }
  );

  if (!fs.existsSync(tempJsonPath)) {
    void vscode.window.showErrorMessage("审查完成，但未生成结构化报告。");
    output.show(true);
    return null;
  }
  return tempJsonPath;
}

async function askQuestionWithReport(reportJsonPath: string, question: string): Promise<string> {
  const config = vscode.workspace.getConfiguration("articleCheck");
  const pythonPath = config.get<string>("pythonPath", "python");
  const workspaceFolder =
    vscode.workspace.workspaceFolders?.[0]?.uri.fsPath ??
    path.dirname(reportJsonPath);
  const result = await execFileAsync(
    pythonPath,
    [
      "-m",
      "article_check",
      "assist-report",
      reportJsonPath,
      "--question",
      question,
      "--json-output"
    ],
    {
      cwd: workspaceFolder,
      maxBuffer: 16 * 1024 * 1024
    }
  );
  const answerPayload = JSON.parse(result.stdout || "{}") as { answer?: string };
  return answerPayload.answer ?? "未获得有效回答。";
}

async function openFormalReport(state: ArticleCheckState): Promise<void> {
  const payload = state.lastReportPayload;
  const htmlPath = payload?.formal_report?.html_path ?? payload?.summary?.formal_report_html_path;
  const mdPath = payload?.formal_report?.markdown_path ?? payload?.summary?.formal_report_markdown_path;
  const target = htmlPath || mdPath;
  if (!target) {
    void vscode.window.showWarningMessage("当前没有可导出的正式审改报告。");
    return;
  }
  await vscode.env.openExternal(vscode.Uri.file(target));
}

async function openWorkflowNodeDetail(
  context: vscode.ExtensionContext,
  state: ArticleCheckState,
  nodeId: string
): Promise<void> {
  const payload = state.lastReportPayload;
  const node = payload?.workflow?.graph?.[nodeId];
  if (!payload || !node) {
    void vscode.window.showWarningMessage("当前没有可查看的节点详情。");
    return;
  }

  const events = (payload.workflow?.events ?? []).filter((event) => {
    const stage = String(event.stage ?? "");
    return stage.includes(node.stage ?? "") || stage.includes(nodeId);
  });

  const detailHtml = renderDetailHtml({
    title: `节点详情: ${nodeId}`,
    subtitle: `${payload.meta?.paper_title ?? "-"} | 综合评分 ${formatScore(payload.meta?.overall_score)}`,
    summaryCards: [
      { label: "阶段", value: node.stage ?? "-" },
      { label: "状态", value: node.status ?? "-" },
      { label: "Worker", value: node.worker_binding ?? "-" },
      { label: "关键节点", value: node.critical ? "是" : "否" },
      { label: "依赖", value: (node.dependencies ?? []).join(", ") || "-" }
    ],
    sections: [
      {
        title: "关联事件",
        items: events.length
          ? events.map((event) => `${event.event_type ?? "-"} | ${event.stage ?? "-"} | ${formatTimestamp(event.timestamp)}`)
          : ["当前没有记录到该节点的事件明细"]
      }
    ],
    actions: []
  });

  openDetailPanel(context, `节点详情: ${nodeId}`, detailHtml);
}

async function openEvidenceDetail(
  context: vscode.ExtensionContext,
  state: ArticleCheckState,
  evidenceId: string
): Promise<void> {
  const payload = state.lastReportPayload;
  const record = (payload?.evidence_records ?? []).find((item) => item.evidence_id === evidenceId);
  if (!payload || !record) {
    void vscode.window.showWarningMessage("当前没有可查看的 evidence 详情。");
    return;
  }

  const relatedFindings = (payload.findings ?? []).filter((finding) => {
    return (finding.description ?? "") === (record.claim ?? "") || (finding.category ?? "") === (record.stage ?? "");
  });

  const detailHtml = renderDetailHtml({
    title: `Evidence 详情: ${record.evidence_id ?? "-"}`,
    subtitle: `${payload.meta?.paper_title ?? "-"} | ${record.stage ?? "-"} | ${record.severity ?? "-"}`,
    summaryCards: [
      { label: "阶段", value: record.stage ?? "-" },
      { label: "严重度", value: record.severity ?? "-" },
      { label: "证据描述", value: record.claim ?? "-" },
      { label: "修正建议", value: record.suggestion ?? "-" },
      { label: "位置", value: JSON.stringify(record.location ?? {}) }
    ],
    sections: [
      {
        title: "关联 Findings",
        items: relatedFindings.length
          ? relatedFindings.map((finding) => `[${finding.severity ?? "-"}] ${finding.description ?? "-"}；建议：${finding.suggestion ?? "-"}`)
          : ["当前没有匹配到更多关联 findings"]
      },
      {
        title: "报告导出",
        items: [
          `正式报告 HTML: ${payload.formal_report?.html_path ?? payload.summary?.formal_report_html_path ?? "-"}`,
          `建议报告: ${payload.advice_report?.report_path ?? payload.summary?.suggestion_report_path ?? "-"}`
        ]
      }
    ],
    actions: [
      {
        label: "跳转到报告片段",
        command: "jumpToEvidence",
        payload: { evidenceId: record.evidence_id ?? "" }
      }
    ]
  });

  openDetailPanel(context, `Evidence 详情: ${record.evidence_id ?? "-"}`, detailHtml, (message) => {
    if (message.type === "jumpToEvidence") {
      focusReportFragment(context, state, "evidence", String(message.evidenceId ?? ""));
    }
  });
}

function execFileAsync(
  command: string,
  args: string[],
  options: { cwd: string; maxBuffer: number }
): Promise<{ stdout: string; stderr: string }> {
  return new Promise((resolve, reject) => {
    execFile(command, args, options, (error, stdout, stderr) => {
      if (error) {
        reject(new Error(`${error.message}\n${stderr || stdout}`));
        return;
      }
      resolve({ stdout, stderr });
    });
  });
}

function openReportPanel(
  context: vscode.ExtensionContext,
  payload: ReviewPayload,
  reportJsonPath: string | null,
  initialFocusTargetId?: string | null
): void {
  const panel = vscode.window.createWebviewPanel(
    "articleCheckReport",
    `Article Check: ${payload.meta?.paper_title ?? "审查报告"}`,
    vscode.ViewColumn.Beside,
    {
      enableScripts: true,
      retainContextWhenHidden: true
    }
  );
  lastPanel = panel;
  panel.webview.html = renderReportHtml(payload, initialFocusTargetId ?? null);
  panel.onDidDispose(() => {
    if (lastPanel === panel) {
      lastPanel = null;
    }
  });
  panel.webview.onDidReceiveMessage(async (message) => {
    if (message.type === "askQuestion") {
      const question = String(message.question ?? "").trim();
      if (!question) {
        void vscode.window.showWarningMessage("请输入问题。");
        return;
      }
      if (!reportJsonPath) {
        panel.webview.postMessage({
          type: "answer",
          answer: "当前没有可用的结构化报告路径。"
        });
        return;
      }

      try {
        const editor = vscode.window.activeTextEditor;
        const config = vscode.workspace.getConfiguration("articleCheck");
        const pythonPath = config.get<string>("pythonPath", "python");
        const workspaceFolder =
          (editor && vscode.workspace.getWorkspaceFolder(editor.document.uri)?.uri.fsPath) ??
          vscode.workspace.workspaceFolders?.[0]?.uri.fsPath ??
          path.dirname(reportJsonPath);

        const answer = await askQuestionWithReport(reportJsonPath, question);
        panel.webview.postMessage({
          type: "answer",
          answer
        });
      } catch (error) {
        panel.webview.postMessage({
          type: "answer",
          answer: `回答失败: ${String(error)}`
        });
      }
    }
    if (message.type === "openEvidenceDetail") {
      await openEvidenceDetail(context, { ...new ArticleCheckState(), lastReportPayload: payload, lastReportJsonPath: reportJsonPath }, String(message.evidenceId ?? ""));
    }
  });
}

function renderWorkbenchHtml(state: ArticleCheckState): string {
  const payload = state.lastReportPayload;
  const batch = state.lastBatchPayload;
  const graphEntries = Object.entries(payload?.workflow?.graph ?? {});
  const evidenceRows = (payload?.evidence_records ?? [])
    .slice(0, 8)
    .map(
      (item) => `
        <tr>
          <td>${escapeHtml(item.stage ?? "-")}</td>
          <td>${escapeHtml(item.severity ?? "-")}</td>
          <td>${escapeHtml(item.claim ?? "-")}</td>
          <td>
            <button class="mini-button" data-evidence-detail="${escapeHtml(item.evidence_id ?? "")}">详情</button>
            <button class="mini-button secondary" data-evidence-jump="${escapeHtml(item.evidence_id ?? "")}">跳到报告</button>
          </td>
        </tr>`
    )
    .join("");
  const nodeRows = graphEntries.length
    ? graphEntries
        .map(
          ([nodeId, node]) => `
          <tr>
            <td>${escapeHtml(nodeId)}</td>
            <td>${escapeHtml(node.stage ?? "-")}</td>
            <td>${escapeHtml(node.status ?? "-")}</td>
            <td>${escapeHtml(node.worker_binding ?? "-")}</td>
          </tr>`
        )
        .join("")
    : `<tr><td colspan="4">暂无节点状态</td></tr>`;
  const batchRows = (batch?.items ?? [])
    .slice(0, 10)
    .map(
      (item) => `
        <tr>
          <td>${escapeHtml(item.meta?.paper_title ?? "-")}</td>
          <td>${formatScore(item.meta?.overall_score)}</td>
          <td>${item.summary?.finding_count ?? 0}</td>
        </tr>`
    )
    .join("");

  return `<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <style>
    body { font-family: var(--vscode-font-family); color: var(--vscode-editor-foreground); background: var(--vscode-sideBar-background); padding: 12px; }
    h2 { margin-top: 18px; font-size: 14px; }
    .actions { display: grid; gap: 8px; }
    button { border: 0; border-radius: 6px; padding: 8px 10px; cursor: pointer; color: white; background: var(--vscode-button-background); }
    .card { border: 1px solid var(--vscode-panel-border); border-radius: 8px; padding: 10px; margin-top: 8px; background: var(--vscode-editor-background); }
    .metrics { display: grid; grid-template-columns: repeat(2, minmax(100px, 1fr)); gap: 8px; }
    .metric { border: 1px solid var(--vscode-panel-border); border-radius: 6px; padding: 8px; }
    .label { font-size: 11px; opacity: 0.8; }
    .value { font-size: 18px; font-weight: 600; }
    table { width: 100%; border-collapse: collapse; margin-top: 8px; }
    th, td { border: 1px solid var(--vscode-panel-border); padding: 6px; text-align: left; vertical-align: top; font-size: 12px; }
    textarea { width: 100%; min-height: 64px; margin-top: 8px; background: var(--vscode-input-background); color: var(--vscode-input-foreground); border: 1px solid var(--vscode-input-border); border-radius: 6px; padding: 8px; }
    .answer { white-space: pre-wrap; margin-top: 8px; padding: 8px; border-radius: 6px; background: var(--vscode-editor-background); }
    .mini-button { margin-right: 6px; margin-bottom: 4px; padding: 4px 8px; font-size: 11px; border-radius: 6px; }
    .secondary { background: var(--vscode-button-secondaryBackground); color: var(--vscode-button-secondaryForeground); }
  </style>
</head>
<body>
  <div class="actions">
    <button id="reviewCurrent">审查当前论文</button>
    <button id="reviewWorkspace">批量审查工作区</button>
    <button id="openReport">打开最近报告</button>
    <button id="exportFormalReport">打开正式审改报告</button>
  </div>

  <h2>当前摘要</h2>
  <div class="metrics">
    <div class="metric"><div class="label">最近论文</div><div class="value">${escapeHtml(payload?.meta?.paper_title ?? "-")}</div></div>
    <div class="metric"><div class="label">综合评分</div><div class="value">${formatScore(payload?.meta?.overall_score)}</div></div>
    <div class="metric"><div class="label">问题数</div><div class="value">${payload?.summary?.finding_count ?? 0}</div></div>
    <div class="metric"><div class="label">工作区批量数</div><div class="value">${batch?.summary?.paper_count ?? 0}</div></div>
  </div>

  <div class="card">
    <h2>节点状态</h2>
    <table>
      <thead><tr><th>节点</th><th>阶段</th><th>状态</th><th>Worker</th></tr></thead>
      <tbody>${nodeRows}</tbody>
    </table>
  </div>

  <div class="card">
    <h2>Evidence 面板</h2>
    <table>
      <thead><tr><th>阶段</th><th>严重度</th><th>证据</th><th>操作</th></tr></thead>
      <tbody>${evidenceRows || "<tr><td colspan='4'>暂无 evidence</td></tr>"}</tbody>
    </table>
  </div>

  <div class="card">
    <h2>工作区批量汇总</h2>
    <div>平均分：${formatScore(batch?.summary?.average_score)} / 总问题数：${batch?.summary?.total_findings ?? 0}</div>
    <table>
      <thead><tr><th>论文</th><th>评分</th><th>问题数</th></tr></thead>
      <tbody>${batchRows || "<tr><td colspan='3'>暂无批量结果</td></tr>"}</tbody>
    </table>
  </div>

  <div class="card">
    <h2>工作台问答</h2>
    <textarea id="questionInput" placeholder="例如：最先改哪些问题？哪几个 evidence 最关键？"></textarea>
    <button id="askWorkbenchQuestion">提问</button>
    <div id="answerBox" class="answer">等待提问...</div>
  </div>

  <script>
    const vscode = acquireVsCodeApi();
    document.getElementById('reviewCurrent').addEventListener('click', () => vscode.postMessage({ type: 'reviewCurrent' }));
    document.getElementById('reviewWorkspace').addEventListener('click', () => vscode.postMessage({ type: 'reviewWorkspace' }));
    document.getElementById('openReport').addEventListener('click', () => vscode.postMessage({ type: 'openReport' }));
    document.getElementById('exportFormalReport').addEventListener('click', () => vscode.postMessage({ type: 'exportFormalReport' }));
    document.getElementById('askWorkbenchQuestion').addEventListener('click', () => {
      const question = document.getElementById('questionInput').value.trim();
      document.getElementById('answerBox').textContent = '正在生成回答...';
      vscode.postMessage({ type: 'askWorkbenchQuestion', question });
    });
    document.querySelectorAll('[data-evidence-detail]').forEach((element) => {
      element.addEventListener('click', () => {
        vscode.postMessage({ type: 'openEvidenceDetail', evidenceId: element.getAttribute('data-evidence-detail') });
      });
    });
    document.querySelectorAll('[data-evidence-jump]').forEach((element) => {
      element.addEventListener('click', () => {
        vscode.postMessage({ type: 'jumpToEvidence', evidenceId: element.getAttribute('data-evidence-jump') });
      });
    });
    window.addEventListener('message', (event) => {
      if (event.data.type === 'answer') {
        document.getElementById('answerBox').textContent = event.data.answer || '未获得回答。';
      }
    });
  </script>
</body>
</html>`;
}

function renderReportHtml(payload: ReviewPayload, initialFocusTargetId: string | null = null): string {
  const findings = payload.findings ?? [];
  const evidence = payload.evidence_records ?? [];
  const priorities = payload.advice_report?.priorities ?? [];
  const findingRows = findings.length
    ? findings
        .map((finding, index) => {
          const location = escapeHtml(JSON.stringify(finding.location ?? {}));
          return `
            <tr>
              <td>${index + 1}</td>
              <td>${escapeHtml(finding.category ?? "-")}</td>
              <td>${escapeHtml(finding.severity ?? "-")}</td>
              <td>${escapeHtml(finding.description ?? "-")}</td>
              <td>${escapeHtml(finding.suggestion ?? "-")}</td>
              <td><code>${location}</code></td>
            </tr>`;
        })
        .join("")
    : `<tr><td colspan="6">未发现问题</td></tr>`;

  const errors = (payload.errors ?? [])
    .map((error) => `<li>${escapeHtml(error)}</li>`)
    .join("");
  const priorityBlocks = priorities.length
    ? priorities
        .map((block) => {
          const items = (block.actions ?? [])
            .map((item) => `<li>${escapeHtml(item)}</li>`)
            .join("");
          return `
            <div class="card">
              <div class="label">${escapeHtml(block.priority ?? "-")}</div>
              <div class="value small">${escapeHtml(block.title ?? "-")}</div>
              <ul>${items}</ul>
            </div>`;
        })
        .join("")
    : `<div class="card"><div class="value small">当前未生成审改建议</div></div>`;
  const evidenceRows = evidence.length
    ? evidence
        .map((record, index) => `
          <tr id="${escapeHtml(buildReportTargetId("evidence", record.evidence_id ?? `row-${index}`))}">
            <td>${index + 1}</td>
            <td>${escapeHtml(record.stage ?? "-")}</td>
            <td>${escapeHtml(record.severity ?? "-")}</td>
            <td>${escapeHtml(record.claim ?? "-")}</td>
            <td>${escapeHtml(record.suggestion ?? "-")}</td>
            <td><code>${escapeHtml(JSON.stringify(record.location ?? {}))}</code></td>
            <td><button class="chat-button" data-evidence-id="${escapeHtml(record.evidence_id ?? "")}">查看详情</button></td>
          </tr>
        `)
        .join("")
    : `<tr><td colspan="7">暂无 evidence 记录</td></tr>`;

  return `<!DOCTYPE html>
<html lang="zh-CN">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Article Check Report</title>
    <style>
      body {
        font-family: var(--vscode-font-family);
        color: var(--vscode-editor-foreground);
        background: var(--vscode-editor-background);
        margin: 0;
        padding: 24px;
        line-height: 1.6;
      }
      h1, h2 { margin-top: 0; }
      .meta, .summary {
        display: grid;
        grid-template-columns: repeat(2, minmax(220px, 1fr));
        gap: 12px;
        margin-bottom: 24px;
      }
      .card {
        border: 1px solid var(--vscode-panel-border);
        border-radius: 8px;
        padding: 12px 16px;
        background: color-mix(in srgb, var(--vscode-editor-background) 92%, white 8%);
      }
      .label {
        font-size: 12px;
        opacity: 0.8;
      }
      .value {
        font-size: 20px;
        font-weight: 600;
      }
      .value.small {
        font-size: 16px;
      }
      table {
        width: 100%;
        border-collapse: collapse;
      }
      th, td {
        border: 1px solid var(--vscode-panel-border);
        padding: 8px 10px;
        text-align: left;
        vertical-align: top;
      }
      th {
        background: var(--vscode-sideBar-background);
      }
      code {
        white-space: pre-wrap;
        word-break: break-word;
      }
      .errors {
        color: var(--vscode-errorForeground);
      }
      .chat-box {
        border: 1px solid var(--vscode-panel-border);
        border-radius: 8px;
        padding: 12px;
        margin-top: 24px;
      }
      .chat-input {
        width: 100%;
        min-height: 72px;
        margin-top: 8px;
        margin-bottom: 8px;
        background: var(--vscode-input-background);
        color: var(--vscode-input-foreground);
        border: 1px solid var(--vscode-input-border);
        border-radius: 6px;
        padding: 8px;
      }
      .chat-button {
        border: 0;
        border-radius: 6px;
        padding: 8px 12px;
        cursor: pointer;
        color: white;
        background: var(--vscode-button-background);
      }
      .chat-answer {
        margin-top: 12px;
        padding: 12px;
        border-radius: 8px;
        background: var(--vscode-sideBar-background);
        white-space: pre-wrap;
      }
      .section-anchor {
        scroll-margin-top: 20px;
      }
    </style>
  </head>
  <body>
    <h1>AI 审查报告</h1>
    <div class="meta">
      <div class="card">
        <div class="label">论文标题</div>
        <div class="value">${escapeHtml(payload.meta?.paper_title ?? "-")}</div>
      </div>
      <div class="card">
        <div class="label">综合评分</div>
        <div class="value">${formatScore(payload.meta?.overall_score)}</div>
      </div>
      <div class="card">
        <div class="label">耗时</div>
        <div class="value">${formatDuration(payload.meta?.duration)}</div>
      </div>
      <div class="card">
        <div class="label">报告格式</div>
        <div class="value">${escapeHtml(payload.report_format ?? "-")}</div>
      </div>
    </div>

    <h2>审查摘要</h2>
    <div class="summary">
      <div class="card">
        <div class="label">发现问题数</div>
        <div class="value">${payload.summary?.finding_count ?? 0}</div>
      </div>
      <div class="card">
        <div class="label">运行错误数</div>
        <div class="value">${payload.summary?.error_count ?? 0}</div>
      </div>
      <div class="card">
        <div class="label">Markdown 报告</div>
        <div>${escapeHtml(payload.summary?.report_markdown_path ?? "-")}</div>
      </div>
      <div class="card">
        <div class="label">JSON 报告</div>
        <div>${escapeHtml(payload.summary?.report_json_path ?? "-")}</div>
      </div>
      <div class="card">
        <div class="label">建议报告</div>
        <div>${escapeHtml(payload.summary?.suggestion_report_path ?? "-")}</div>
      </div>
    </div>

    <h2>审改建议</h2>
    <div class="summary">${priorityBlocks}</div>

    <h2>问题明细</h2>
    <table>
      <thead>
        <tr>
          <th>#</th>
          <th>类别</th>
          <th>严重度</th>
          <th>问题描述</th>
          <th>修正建议</th>
          <th>定位</th>
        </tr>
      </thead>
      <tbody>${findingRows}</tbody>
    </table>

    <h2>Evidence 记录</h2>
    <table>
      <thead>
        <tr>
          <th>#</th>
          <th>阶段</th>
          <th>严重度</th>
          <th>证据描述</th>
          <th>修正建议</th>
          <th>定位</th>
          <th>详情</th>
        </tr>
      </thead>
      <tbody>${evidenceRows}</tbody>
    </table>

    <h2>运行错误</h2>
    <ul class="errors">
      ${errors || "<li>无</li>"}
    </ul>

    <div class="chat-box">
      <h2>交互式问答</h2>
      <div>可以直接追问，例如“我应该先改哪些问题？”、“参考文献哪里最危险？”</div>
      <textarea id="questionInput" class="chat-input" placeholder="输入关于当前审查报告的问题"></textarea>
      <button id="askButton" class="chat-button">提问</button>
      <div id="answerBox" class="chat-answer">等待提问...</div>
    </div>

    <script>
      const vscode = acquireVsCodeApi();
      const askButton = document.getElementById('askButton');
      const questionInput = document.getElementById('questionInput');
      const answerBox = document.getElementById('answerBox');
      const initialFocusTargetId = ${JSON.stringify(initialFocusTargetId)};

      function focusFragment(targetId) {
        if (!targetId) return;
        const element = document.getElementById(targetId);
        if (element) {
          element.scrollIntoView({ behavior: 'smooth', block: 'center' });
          element.style.outline = '2px solid var(--vscode-focusBorder)';
          setTimeout(() => { element.style.outline = ''; }, 1800);
        }
      }

      askButton.addEventListener('click', () => {
        const question = questionInput.value.trim();
        if (!question) {
          answerBox.textContent = '请输入问题。';
          return;
        }
        answerBox.textContent = '正在生成回答...';
        vscode.postMessage({ type: 'askQuestion', question });
      });
      document.querySelectorAll('[data-evidence-id]').forEach((element) => {
        element.addEventListener('click', () => {
          vscode.postMessage({ type: 'openEvidenceDetail', evidenceId: element.getAttribute('data-evidence-id') });
        });
      });
      focusFragment(initialFocusTargetId);

      window.addEventListener('message', (event) => {
        const message = event.data;
        if (message.type === 'answer') {
          answerBox.textContent = message.answer || '未获得回答。';
        }
        if (message.type === 'focusFragment') {
          focusFragment(message.targetId);
        }
      });
    </script>
  </body>
</html>`;
}

function focusReportFragment(
  context: vscode.ExtensionContext,
  state: ArticleCheckState,
  targetType: "evidence",
  targetId: string
): void {
  if (!state.lastReportPayload) {
    void vscode.window.showWarningMessage("当前没有可跳转的报告。");
    return;
  }
  const reportTargetId = buildReportTargetId(targetType, targetId);
  if (lastPanel) {
    try {
      lastPanel.reveal(vscode.ViewColumn.Beside, true);
      lastPanel.webview.postMessage({ type: "focusFragment", targetId: reportTargetId });
      return;
    } catch {
      lastPanel = null;
    }
  }
  openReportPanel(context, state.lastReportPayload, state.lastReportJsonPath, reportTargetId);
}

function openDetailPanel(
  context: vscode.ExtensionContext,
  title: string,
  html: string,
  onMessage?: (message: any) => void
): void {
  const panel = vscode.window.createWebviewPanel(
    "articleCheckDetail",
    title,
    vscode.ViewColumn.Beside,
    {
      enableScripts: true,
      retainContextWhenHidden: true
    }
  );
  lastDetailPanel = panel;
  panel.webview.html = html;
  panel.onDidDispose(() => {
    if (lastDetailPanel === panel) {
      lastDetailPanel = null;
    }
  });
  if (onMessage) {
    panel.webview.onDidReceiveMessage(onMessage);
  }
}

function renderDetailHtml(options: {
  title: string;
  subtitle?: string;
  summaryCards: Array<{ label: string; value: string }>;
  sections: Array<{ title: string; items: string[] }>;
  actions: Array<{ label: string; command: string; payload?: Record<string, unknown> }>;
}): string {
  const cards = options.summaryCards
    .map((card) => `
      <div class="card">
        <div class="label">${escapeHtml(card.label)}</div>
        <div class="value">${escapeHtml(card.value)}</div>
      </div>
    `)
    .join("");
  const sections = options.sections
    .map((section) => `
      <div class="section">
        <h2>${escapeHtml(section.title)}</h2>
        <ul>${section.items.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>
      </div>
    `)
    .join("");
  const actions = options.actions.length
    ? `<div class="actions">${options.actions
        .map((action) => `<button data-command="${escapeHtml(action.command)}" data-payload='${escapeHtml(JSON.stringify(action.payload ?? {}))}'>${escapeHtml(action.label)}</button>`)
        .join("")}</div>`
    : "";
  return `<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <style>
    body { font-family: var(--vscode-font-family); color: var(--vscode-editor-foreground); background: var(--vscode-editor-background); padding: 20px; }
    h1 { margin-bottom: 6px; }
    .subtitle { opacity: 0.8; margin-bottom: 16px; }
    .grid { display: grid; grid-template-columns: repeat(2, minmax(180px, 1fr)); gap: 12px; }
    .card, .section { border: 1px solid var(--vscode-panel-border); border-radius: 8px; padding: 12px; background: var(--vscode-sideBar-background); margin-bottom: 12px; }
    .label { font-size: 12px; opacity: 0.8; }
    .value { margin-top: 6px; font-size: 14px; font-weight: 600; white-space: pre-wrap; word-break: break-word; }
    .actions { display: flex; gap: 8px; margin: 16px 0; }
    button { border: 0; border-radius: 6px; padding: 8px 12px; cursor: pointer; color: white; background: var(--vscode-button-background); }
    ul { margin: 0; padding-left: 18px; }
    li { margin-bottom: 6px; }
  </style>
</head>
<body>
  <h1>${escapeHtml(options.title)}</h1>
  <div class="subtitle">${escapeHtml(options.subtitle ?? "")}</div>
  <div class="grid">${cards}</div>
  ${actions}
  ${sections}
  <script>
    const vscode = acquireVsCodeApi();
    document.querySelectorAll('[data-command]').forEach((element) => {
      element.addEventListener('click', () => {
        const command = element.getAttribute('data-command');
        const payload = JSON.parse(element.getAttribute('data-payload') || '{}');
        vscode.postMessage({ type: command, ...payload });
      });
    });
  </script>
</body>
</html>`;
}

function applyDiagnostics(
  state: ArticleCheckState,
  diagnosticCollection: vscode.DiagnosticCollection
): void {
  diagnosticCollection.clear();
  if (!state.lastReviewedFilePath || !state.lastReportPayload) {
    return;
  }
  const uri = vscode.Uri.file(state.lastReviewedFilePath);
  const diagnostics: vscode.Diagnostic[] = [];
  const findings = state.lastReportPayload.findings ?? [];
  const evidence = state.lastReportPayload.evidence_records ?? [];

  findings.forEach((finding, index) => {
    diagnostics.push(
      new vscode.Diagnostic(
        buildRangeFromLocation(finding.location),
        buildDiagnosticMessage(
          finding.description ?? "发现问题",
          finding.suggestion ?? null,
          finding.category ?? null
        ),
        mapSeverity(finding.severity)
      )
    );
    diagnostics[diagnostics.length - 1].source = "Article Check";
    diagnostics[diagnostics.length - 1].code = finding.type ?? `finding-${index + 1}`;
  });

  evidence.forEach((record, index) => {
    diagnostics.push(
      new vscode.Diagnostic(
        buildRangeFromLocation(record.location),
        buildDiagnosticMessage(
          record.claim ?? "发现证据项",
          record.suggestion ?? null,
          record.stage ?? null
        ),
        mapSeverity(record.severity)
      )
    );
    diagnostics[diagnostics.length - 1].source = "Article Check";
    diagnostics[diagnostics.length - 1].code = record.evidence_id ?? `evidence-${index + 1}`;
  });

  diagnosticCollection.set(uri, diagnostics);
}

function buildRangeFromLocation(location?: Record<string, unknown>): vscode.Range {
  const line = parseLineNumber(location);
  const zeroBasedLine = Math.max(0, (line ?? 1) - 1);
  return new vscode.Range(zeroBasedLine, 0, zeroBasedLine, 120);
}

function parseLineNumber(location?: Record<string, unknown>): number | null {
  if (!location) {
    return null;
  }
  const line = location["line"];
  if (typeof line === "number" && Number.isFinite(line)) {
    return line;
  }
  if (typeof line === "string") {
    const match = line.match(/\d+/);
    if (match) {
      return Number(match[0]);
    }
  }
  const locationText = JSON.stringify(location);
  const lineMatch = locationText.match(/line\s*(\d+)/i);
  if (lineMatch) {
    return Number(lineMatch[1]);
  }
  return null;
}

function mapSeverity(severity?: string): vscode.DiagnosticSeverity {
  switch ((severity ?? "").toLowerCase()) {
    case "critical":
      return vscode.DiagnosticSeverity.Error;
    case "major":
      return vscode.DiagnosticSeverity.Warning;
    case "minor":
      return vscode.DiagnosticSeverity.Information;
    default:
      return vscode.DiagnosticSeverity.Hint;
  }
}

function buildDiagnosticMessage(description: string, suggestion?: string | null, category?: string | null): string {
  const parts = [description];
  if (suggestion) {
    parts.push(`建议: ${suggestion}`);
  }
  if (category) {
    parts.push(`类别: ${category}`);
  }
  return parts.join(" | ");
}

function buildReportTargetId(targetType: "evidence", targetId: string): string {
  return `${targetType}-${slugify(targetId || "unknown")}`;
}

function slugify(value: string): string {
  return value.replace(/[^a-zA-Z0-9_-]/g, "-");
}

function formatScore(score?: number): string {
  if (typeof score !== "number") {
    return "-";
  }
  return score.toFixed(2);
}

function formatDuration(duration?: number): string {
  if (typeof duration !== "number") {
    return "-";
  }
  return `${duration.toFixed(1)}s`;
}

function formatTimestamp(timestamp?: number): string {
  if (typeof timestamp !== "number") {
    return "-";
  }
  return new Date(timestamp * 1000).toLocaleString("zh-CN");
}

function escapeHtml(value: string): string {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}
