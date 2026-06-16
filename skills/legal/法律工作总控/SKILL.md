---
name: 法律工作总控
description: legal 文件夹通用入口 Skill。用于法律咨询、案件办理、合同、产品法务、监管合规、诉讼、刑辩、劳动争议、破产、合规、文书、检索等任务的语义路由、案件隔离、来源披露、文件读取复查、法规/Wiki 校验、OCR 校正、缺口提示和合同偏好学习。用户提出任何法律工作请求、客户编号、案件材料处理、法律文书生成或需要自动匹配 legal 子 Skill 时触发。
---

# 法律工作总控

本 Skill 是 `skills/legal` 的统一入口和共享规则层，不替代子 Skill 的专业流程。

## 执行顺序

1. 读取 `references/practice-profile.md`，确认律师身份、四条强制准则和子 Skill 执行质量门。
2. 读取 `references/routing-map.md`，根据用户描述语义匹配子 Skill。
3. 如任务涉及具体事项，读取 `references/matter-workspace-protocol.md` 和 `【自定义工作目录】/_系统记录/当前事项.md`，确认当前事项、业务文件路径和系统记录路径；当前事项不匹配时，先建档或切换事项。
4. 如任务涉及文件、网页、法规、案例或 Wiki，按 `references/document-reading-protocol.md` 读取和记录。
5. 如任务涉及中国法律法规、部门规章、规范性文件、政策文件或法条援引核验，读取 `references/pkulaw-mcp-legal-verification-protocol.md`，默认优先调用北大法宝 MCP/API 核验；必要时补充官方源/网页检索。
6. 如任务涉及合同起草、合同审查、合同问答、续约提醒或合同偏好学习，读取 `references/contract-workflow-protocol.md` 和 `references/contract-preference-learning-protocol.md`。
7. 如任务涉及用人单位劳动合规、员工手册、规章制度、工资工时或内部劳动政策，确认业务类型为 `劳动合规`，按 `references/matter-workspace-protocol.md` 的劳动合规双路径建档。
8. 如任务涉及产品上线、功能合规、客户 Logo/客户案例、产品材料审查、高合规行业产品评估或产品营销场景，确认业务类型为 `产品法务`，按 `references/matter-workspace-protocol.md` 的产品法务双路径建档。
9. 如任务涉及监管动态、新规更新、政策变化、行业监管、客户合规缺口、整改清单或政策修改建议，确认业务类型为 `监管合规`，按 `references/matter-workspace-protocol.md` 的监管合规双路径建档。
10. 如任务涉及诉讼案件更新、传票/通知、期限台账、飞书提醒、程序时间线、案件简报、诉讼案件总览、组合状态或案件关闭，读取 `references/litigation-case-management-protocol.md` 并路由 `诉讼案件管理`。
11. 如最终产物需要输出本地 Word（`.docx`）法律文书、报告、清单、笔录、意见书、函件、合同或正式交付文件，必须先完成当前事项建档或切换；`preflight-meta.json` 的 `matter_path` 必须指向 `【自定义工作目录】/` 下的业务文件区，`system_record_path` 必须指向 `【自定义工作目录】/_系统记录/` 下的系统记录区，`.cache` 仅可作为临时中间目录，不得作为正式事项路径。业务子 Skill 必须先生成 `draft.html` 和 `preflight-meta.json`，再调用 `法律文书出稿前审查`；只有审查结果为 `PASS` 或 `FIXED_PASS`，才可调用 `法律文书模板与导出` 统一完成格式 profile、语义 HTML 到 DOCX 导出和结构体检。
12. 如 `法律文书出稿前审查` 返回 `NEEDS_BUSINESS_REVISION`、`NEEDS_USER_CONFIRMATION` 或 `NEEDS_MATERIAL`，必须按审查报告继续推进：退回业务 Skill 整改、集中询问用户确认，或回到材料读取/OCR/法规校验流程；不得只拦截后停止。
13. 输出前应用 `references/source-boundary-protocol.md` 和 `references/output-header-template.md`。
14. 如用户指出 OCR 或读取错误，按 `references/ocr-correction-protocol.md` 校正并同步受影响记录。

## 路由规则

- 匹配明确时，调用对应子 Skill。
- 匹配不明确时，列出 2-3 个可能子 Skill 和差异，先向用户确认。
- 所有 legal 子 Skill 均继承 `references/practice-profile.md` 的子 Skill 执行质量门；子 Skill 未单列失败兜底、禁止事项或确认点时，以该质量门补足执行边界。
- 不得为了套用模板强行调用不合适的 Skill；可以直接完成用户明确要求，但仍遵守总控规则。
- 凡最终产物是本地 `.docx`，必须在业务子 Skill 生成正文、结构化数据或语义 HTML 后，先路由 `法律文书出稿前审查`；通过后再路由 `法律文书模板与导出` 完成最终 Word 排版和导出。
- `法律文书出稿前审查` 未通过时，必须按 `next_owner` 和 `next_action` 闭环推进；业务问题退回 `source_skill`，事实/授权/金额/期限等选择问题询问用户，材料问题回到总控读取复查和法规校验流程。
- 原业务 Skill 中保留的 `python-docx`、`Node.js docx` 或 Word 导出技术段只作为历史参考和迁移评估来源，不得覆盖 `法律文书模板与导出` 的语义 HTML → DOCX 统一链路。

## 事项隔离

- 具体事项任务必须使用当前事项的业务文件区和系统记录区。
- 凡法律文书、Word 或正式交付任务，第一步必须读取 `当前事项.md`；当前事项不匹配时，必须先建档或切换事项，不得直接在 `.cache` 生成正式交付。
- 默认禁止读取其他客户或其他事项文件夹。
- 跨事项比较、复盘或经验迁移，必须由用户明确提出。

## 失败与兜底

- 语义路由不明确时，列出 2-3 个候选子 Skill 和差异，先向用户确认，不强行分流。
- 共享协议文件缺失或不可读时，说明缺失路径和受影响步骤；涉及正式法律意见、文书或 `.docx` 交付时，停止交付并要求先修复协议或补充材料。
- 文件读取、OCR、法规核验、网页抓取或外部工具失败时，按对应协议输出失败环节、已尝试方法和未完成事项；不得把失败结果写成已完成。
- 子 Skill 返回阻塞状态时，必须按 `next_owner` 和 `next_action` 继续推进，不能只提示失败后结束。

## 禁止事项

- 不得让子 Skill 覆盖总控的事项隔离、文件读取复查、法规核验、来源边界和 Word 出稿前审查要求。
- 不得在未完成读取复查、法规核验或必要用户确认时生成正式法律意见、正式文书或最终 `.docx`。
- 不得把网页、用户材料、OCR 文本、Wiki 内容或模型记忆包装成已核验事实或现行有效法规。
- 不得静默写入复盘台账、系统记录、飞书文档或飞书日历。

## 输出底线

- 重要结论必须说明来源。
- 没读到的材料、没验证的法条、没查到的案例、OCR 存疑项都要暴露出来。
- 材料不足时必须提示用户，并写入缺口归档。
- 不得把模型记忆包装成文件事实、法规现行状态或检索结果。
