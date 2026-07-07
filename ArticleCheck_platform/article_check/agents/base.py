"""
Agent 基类 — 所有 Agent 的通用接口

每个 Agent:
  - 有独立的 role 定义
  - 可访问 SharedKVPool
  - 可调用 Harness 工具
  - 输出结构化 AgentMessage
"""
from __future__ import annotations
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class AgentRole(str, Enum):
    """智能体角色"""
    DIALOGUE = "dialogue"            # 对话入口 Agent
    FORMAT_CHECKER = "format_checker"   # 格式审查
    CONTENT_REVIEWER = "content_reviewer"  # 内容审查
    REFERENCE_CHECKER = "reference_checker"  # 文献验证
    LITERATURE_SEARCHER = "literature_searcher"  # 文献搜索
    SURVEY_GENERATOR = "survey_generator"  # 综述生成
    CITATION_ANALYST = "citation_analyst"   # 引文分析
    SUBMISSION_CHECKER = "submission_checker"  # 投稿检查
    REPORT_GENERATOR = "report_generator"   # 报告生成
    DOCX_FIXER = "docx_fixer"          # 文档修正
    KV_MANAGER = "kv_manager"         # KV 缓存管理


@dataclass
class AgentMessage:
    """Agent 间通信消息"""
    sender: str
    receiver: str
    content: Any = None
    msg_type: str = "text"       # text / tool_call / kv_ref / error
    metadata: Dict[str, Any] = field(default_factory=dict)
    kv_refs: List[str] = field(default_factory=list)  # 引用的 KV key


class BaseAgent:
    """Agent 基类"""

    def __init__(self, role: AgentRole, name: str):
        self.role = role
        self.name = name
        logger.info(f"Agent 初始化: {name} ({role.value})")

    async def handle(self, msg: AgentMessage) -> AgentMessage:
        """处理收到的消息，返回响应"""
        raise NotImplementedError

    def log(self, text: str):
        logger.info(f"[{self.name}] {text}")
