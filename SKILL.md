---
name: china-legal-skills
description: Chinese legal workflow skills for lawyers, legal counsel, enterprise legal operations, litigation, criminal defense, labor disputes, bankruptcy, contract review, compliance, legal research, and legal document drafting.
---

# China Legal Skills

Use this skill when the user needs Chinese legal work support, including legal consultation, enterprise internal legal operations, litigation analysis, criminal defense, labor disputes, bankruptcy, contract review, compliance review, legal research, evidence review, or legal document drafting.

## Workflow

1. For enterprise internal legal operations, read `skills/enterprise-legal-ops/SKILL.md`.
2. For lawyer/legal-service workflows, read `skills/legal/法律工作总控/SKILL.md` first. Treat it as the main router and shared quality gate for the legal workflow.
3. Let the main router choose the relevant Chinese sub-skill under `skills/legal/`.
4. When a referenced file path is relative, resolve it from this repository root.

Do not replace attorney review, client authorization, source verification, or jurisdiction-specific legal judgment. Outputs are working drafts unless a qualified professional reviews them.
