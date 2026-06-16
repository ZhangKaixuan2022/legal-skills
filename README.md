# Legal Skills

<p align="center">
  <strong>面向中国法律工作的 AI Skill 系统</strong><br>
  从法律咨询、民事诉讼、刑事辩护、劳动争议、破产程序，到合同、产品法务、广告合规、监管监测和文书导出。
</p>

<p align="center">
  <em>法律工作不是一个提示词，而是一套可复查、可路由、可交付的流程。</em><br>
  <strong>这个项目把个人法律工作台沉淀为可复用的 Agent Skill。</strong><br>
  <em>现在开源。</em>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/China_Law_Skills-red?style=flat" alt="China Law Skills">
  <img src="https://img.shields.io/badge/Codex-412991?style=flat&logo=openai&logoColor=white" alt="Codex">
  <img src="https://img.shields.io/badge/Claude_Code-000?style=flat&logo=anthropic&logoColor=white" alt="Claude Code">
  <img src="https://img.shields.io/badge/Markdown-000000?style=flat&logo=markdown&logoColor=white" alt="Markdown">
  <img src="https://img.shields.io/badge/License-MIT-blue.svg" alt="MIT">
</p>

---

## 这是什么

Legal Skills 是一套中文法律工作 Agent Skill。它以 `法律工作总控` 为统一入口，通过语义路由调用各个子 skill，并把法律任务拆成可检查的步骤：事项隔离、材料读取复查、法规校验、来源边界、文书出稿前审查和最终导出。

它适合本地 AI Coding Agent 使用，例如 Codex、Claude Code、Gemini CLI、OpenCode 等。你可以把它安装到自己的 skills 目录，然后直接对 Agent 说：

```text
法律工作总控 帮我判断这个客户咨询应该怎么回复。
```

```text
民事一审诉讼 读取这个案件材料，先做材料复查摘要，不要直接出法律意见。
```

```text
合同审查 审核这份服务合同，按风险等级输出修改建议。
```

## 功能

| 模块 | 说明 |
|---|---|
| **法律工作总控** | 统一入口、语义路由、事项隔离、来源披露、文件读取复查、法规/Wiki 校验 |
| **民事诉讼** | 初步法律分析、法规案例检索、调查取证、诉讼文书、立案、庭前准备、庭审与结案 |
| **刑事辩护** | 案件承接、侦查、审查起诉、一审、二审、简易速裁、未成年人、死刑、特殊程序 |
| **劳动争议** | 劳动争议诉讼、仲裁程序、证据体系、劳动关系认定与经济补偿计算 |
| **破产程序** | 破产申请、管理人工作、财产调查、债权申报、债权人会议、重整、和解、清算 |
| **合同与合规** | 合同起草、合同审查、用人单位劳动合规、产品法务、广告合规、食品标签合规 |
| **文书生产** | 法律文书出稿前审查、法律文书模板与导出、审理报告、民事判决书、破产文书 |
| **工具型 skill** | 法条转 Markdown、微信文章格式化、法律文章去 AI 味、诉讼可视化、诉讼分析 |

## 快速开始

### 方式一：作为普通 skills 目录安装

```bash
git clone https://github.com/pa1nrui1/legal-skills.git
mkdir -p ~/.codex/skills
rsync -a legal-skills/skills/legal/ ~/.codex/skills/legal/
```

安装后，在 Codex 中可以直接调用：

```text
法律工作总控
法律咨询助手
合同审查
民事一审诉讼
刑事辩护总调度
```

### 方式二：作为 Codex plugin 安装

```bash
codex plugin marketplace add pa1nrui1/legal-skills --sparse .codex-plugin --sparse skills
```

## 使用前必须修改的本地配置

本仓库保留了作者工作流中的默认执业身份和本地工作台约定。Fork 后用于你自己的执业场景时，建议先修改：

- `skills/legal/法律工作总控/references/practice-profile.md`
- 文书模板中出现的律师姓名、律所名称、地址、电话、邮箱
- `<LEGAL_WORKSPACE>`、`<LEGAL_CLIENT_LEDGER>` 等本地路径占位符
- `~/.config/legal-regulatory/pkulaw.env` 等外部检索或法规库凭证配置

不要把真实客户材料、案卷、OCR 中间结果、私有台账、API key 或商业数据库凭证提交到仓库。

## 目录结构

```text
skills/legal/
  法律工作总控/
  法律咨询助手/
  民事一审诉讼/
  刑事辩护总调度/
  合同审查/
  法律文书模板与导出/
  ...
```

每个子目录通常包含：

- `SKILL.md`：skill 的入口说明和触发条件
- `references/`：流程、规则、检查表和方法论
- `templates/`：法律文书或交付物模板
- `scripts/`：少量本地自动化脚本

## 开源范围

本仓库发布的是 skill 规则、流程、模板和脚本，不包含作者本地的客户材料、业务台账、系统记录、飞书文档、私有数据库凭证或迁移备份。

为了便于公开使用，开源整理时做了这些处理：

- 排除原始目录中的 `_backups/`
- 将 `/Users/panrui/.codex/skills/legal` 改为仓库内 `skills/legal`
- 将作者本机业务工作目录改为 `<LEGAL_WORKSPACE>`
- 将作者本机客户台账路径改为 `<LEGAL_CLIENT_LEDGER>`
- 保留需要用户自行配置的外部服务环境变量说明

## 重要声明

本项目是 AI Agent 工作流与文档模板集合，不构成法律意见，也不能替代律师基于完整事实、现行法律和有效委托所作的专业判断。使用者应自行核验法律法规、案例时效、材料真实性、授权范围和最终交付内容。

## License

MIT
