---
name: 法律文书模板与导出
description: 统一处理法律工作中最终需要输出本地 Word（.docx）的文书、报告、清单、笔录、意见书、函件、合同和正式交付文件。由法律工作总控强制路由调用；业务 Skill 负责正文和法律判断，本 Skill 负责选择格式 profile、接收语义 HTML、导出 DOCX、结构体检和兜底模板。
---

# 法律文书模板与导出

本 Skill 只处理最终 Word 的格式与导出，不替代业务 Skill 的事实梳理、法律分析、文书正文生成、材料读取复查、法规核验和出稿前审查。

## 法律工作总控规则（强制）

执行本 Skill 前，必须先遵循：
- skills/legal/法律工作总控/references/practice-profile.md
- skills/legal/法律工作总控/references/source-boundary-protocol.md

本 Skill 继承 `practice-profile.md` 的子 Skill 执行质量门；审查报告、来源边界或验证结果缺失时，不得标记为正式交付。

## 强制路由

- 凡最终产物是本地 `.docx` 的法律文书、报告、清单、笔录、意见书、函件、合同或正式交付文件，必须调用本 Skill。
- `法律工作总控` 负责判断是否进入本 Skill；用户直接点名业务 Skill 生成 Word 时，业务 Skill 也必须先通过 `法律文书出稿前审查`，再调用本 Skill。
- 正式交付只接收 `法律文书出稿前审查` 生成的 `draft_checked.html`，并必须附带审查报告。
- 审查报告不是 `PASS` 或 `FIXED_PASS` 时，禁止生成正式 `.docx`。
- 未命中专用 profile 时，使用 `fallback_desktop_word`。
- 原 Skill 中保留的 `python-docx`、`Node.js docx`、Word 导出示例或旧技术方案只作为迁移评估来源/历史参考；不得作为最终 Word 导出路径执行。
- 最终 `.docx` 一律走本 Skill 的语义 HTML -> `html_to_docx.py` -> DOCX 链路，除非用户明确要求另行实验且不作为正式交付。

## 输入约定

业务 Skill 应先生成语义 HTML，并经 `法律文书出稿前审查` 生成 `draft_checked.html`。使用 XHTML 兼容写法：

- `h1`：文书标题。
- `h2` / `h3`：层级标题。
- `p.meta`：申请人、当事人、案号、法院、基础信息。
- `p.body` 或普通 `p`：正文段落。
- `p.signature`：落款。
- `table`：真实表格。
- `section`：附件、事实、理由、请求、证据目录等区块。

## Profile

内置 profile 位于 `assets/profiles/`：

- `litigation_standard`：诉讼/刑辩通用文书。
- `legal_report`：法律服务建议书、检索报告、案件提纲等。
- `judgment_style`：民事判决书、审理报告等特殊法院文书样式。
- `entrustment_authorization`：委托合同管理-授权委托书。
- `entrustment_contract`：委托合同管理-委托代理合同。
- `entrustment_risk_notice`：委托合同管理-风险义务告知书。
- `entrustment_statement_record`：委托合同管理-委托人陈述笔录/案件沟通记录。
- `entrustment_supervision_card`：委托合同管理-服务质量监督卡。
- `legal_representative_certificate`：委托合同管理-法定代表人身份证明书。
- `litigation_visualization`：诉讼可视化图表嵌入 Word。
- `fallback_desktop_word`：无专用模板时的兜底桌面 Word。

## 导出命令

```bash
python scripts/html_to_docx.py \
  --input draft_checked.html \
  --output output.docx \
  --profile litigation_standard \
  --preflight-report 出稿前审查报告.md
```

如未指定或未找到 profile，脚本使用 `fallback_desktop_word`。

## 失败与兜底

- `draft_checked.html`、审查报告或 profile 缺失时，停止导出并退回 `法律文书出稿前审查` 或业务 Skill 补齐。
- `html_to_docx.py` 执行失败时，报告本次命令、错误摘要和输入文件路径；不得输出未验证的 `.docx`。
- 专用 profile 不存在、JSON 解析失败或 manifest 异常时，使用 `fallback_desktop_word` 重新导出，并在交付说明中标注兜底 profile。
- `health_check.py` 未通过时，不得宣称 Word 已交付；先修复导出问题，修复失败则保留 HTML 和错误摘要。

## 验证命令

```bash
python scripts/health_check.py
python scripts/health_check.py --docx output.docx --expect-title "文书标题"
```

验证至少检查：

- profile JSON 可解析。
- manifest 可解析。
- DOCX 可解包。
- `word/document.xml` 存在。
- 标题文本存在。
- 页边距配置存在。
- 页码字段存在。
- 表格生成真实 `w:tbl`。

## 迁移边界

- 只迁移 Word 排版和导出规则，不迁移正文范式、事实分析框架、法律论证模板、提示词库、质证句式库、信息采集表和案件流程规则。
- 原 Skill 中 `python-docx`、`Node.js docx`、Word 导出方案必须先评估，再标注为 `迁移替换`、`保留引用` 或 `暂不迁移`。
- 本轮不删除现有正文模板文件。
- 标注为 `保留引用` 或 `暂不迁移` 的旧技术段不得继续驱动最终 DOCX 生成；只保留其中的业务结构、特殊字段或风险提示价值。

## 禁止事项

- 禁止绕过 `法律文书出稿前审查` 直接导出正式 Word。
- 禁止修改业务正文、法律判断、事实认定或当事人信息来适配排版。
- 禁止在审查报告为 `NEEDS_BUSINESS_REVISION`、`NEEDS_USER_CONFIRMATION` 或 `NEEDS_MATERIAL` 时生成正式 `.docx`。
- 禁止把验证失败的 `.docx` 标记为最终交付文件。
