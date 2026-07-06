"""
全局配置管理 — 支持环境变量覆盖、JSON/YAML 配置、模板匹配
"""
import os
import json
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class DeepSeekConfig:
    """DeepSeek API 配置"""
    api_key: str = field(default_factory=lambda: os.getenv("DEEPSEEK_API_KEY", ""))
    base_url: str = "https://api.deepseek.com/v1"
    chat_model: str = "deepseek-chat"
    reasoner_model: str = "deepseek-reasoner"
    max_tokens: int = 8192
    temperature: float = 0.1
    top_p: float = 0.9
    timeout: int = 120


@dataclass
class CacheConfig:
    """缓存策略配置（Token 优化核心）"""
    enabled: bool = True
    # 系统提示词固定在前缀，利用 provider 缓存
    cache_prefix_system: bool = True
    # 语义缓存（embedding-based）
    semantic_cache_enabled: bool = True
    semantic_cache_threshold: float = 0.92
    # 缓存 TTL
    system_cache_ttl: int = 3600
    semantic_cache_ttl: int = 1800


@dataclass
class PipelineConfig:
    """流水线配置"""
    max_concurrent: int = 4  # 并行 worker 数
    max_retries: int = 3
    retry_delay: float = 2.0
    timeout_per_worker: int = 300
    # 工作树隔离
    worktree_enabled: bool = True
    worktree_base_dir: str = ".worktrees"
    # 自适应审查
    adaptive_depth: bool = True
    triage_first: bool = True  # 先快速扫描再决定深度


@dataclass
class FormatConfig:
    """格式检查规则配置"""
    # LaTeX
    latex_rules_enabled: bool = True
    chktex_config: str = ".chktexrc"
    # Word
    docx_rules_enabled: bool = True
    docx_template: Optional[str] = None
    # 自定义规则
    custom_rules_dir: str = "rules"


@dataclass
class ReferenceConfig:
    """文献审查配置"""
    semantic_scholar_api: str = "https://api.semanticscholar.org/graph/v1"
    crossref_api: str = "https://api.crossref.org"
    openalex_api: str = "https://api.openalex.org"
    verify_doi: bool = True
    check_citation_accuracy: bool = True
    max_refs_per_paper: int = 100


@dataclass
class ReportConfig:
    """报告输出配置"""
    output_format: str = "markdown"  # markdown / html / pdf
    output_dir: str = "reports"
    include_suggestions: bool = True
    include_score: bool = True
    template_dir: str = "report/templates"


@dataclass
class AppConfig:
    """主配置"""
    project_root: str = field(
        default_factory=lambda: os.getcwd()
    )
    deepseek: DeepSeekConfig = field(default_factory=DeepSeekConfig)
    cache: CacheConfig = field(default_factory=CacheConfig)
    pipeline: PipelineConfig = field(default_factory=PipelineConfig)
    format: FormatConfig = field(default_factory=FormatConfig)
    reference: ReferenceConfig = field(default_factory=ReferenceConfig)
    report: ReportConfig = field(default_factory=ReportConfig)

    def __post_init__(self):
        self.project_root = os.getenv(
            "ARTICLE_CHECK_ROOT",
            str(Path(self.project_root).resolve())
        )

    @classmethod
    def from_json(cls, path: str) -> "AppConfig":
        with open(path, "r") as f:
            data = json.load(f)
        return cls(**data)

    def to_dict(self) -> dict:
        return asdict(self)


# 全局单例
config = AppConfig()
