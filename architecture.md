.
├── article_check/        # 主源码
│   ├── core/             # 核心抽象
│   │   ├── harness/      # 6层Harness
│   │   ├── agent/        # Agent基类
│   │   └── worktree/     # 工作树隔离
│   ├── pipeline/         # 审查流水线
│   ├── rules/            # 格式规则
│   ├── llm/              # LLM交互
│   ├── mcp/              # MCP工具
│   └── config/           # 配置
├── repos/                # 参考项目
│   ├── coarse
│   ├── loupe
│   ├── reviewer2
│   ├── OpenJudge
│   ├── athena-loops
│   ├── awesome-llm-paper-wiki
│   └── validocx
├── tests/                # 测试
├── scripts/              # 工具脚本
├── docs/                 # 文档
└── pyproject.toml
