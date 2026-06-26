#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Preflight review for legal DOCX deliverables before HTML-to-DOCX export."""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import re
import sys
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path
from typing import Any


LEGAL_DIR = Path(__file__).resolve().parents[2]
EXPORT_SKILL_DIR = LEGAL_DIR / "法律文书模板与导出"
PROFILES_DIR = EXPORT_SKILL_DIR / "assets" / "profiles"
MATTER_ROOT = Path(os.environ.get("LEGAL_WORKSPACE", ".")).expanduser()
SYSTEM_RECORD_ROOT = MATTER_ROOT / "_系统记录"
CURRENT_MATTER_PATH = SYSTEM_RECORD_ROOT / "当前事项.md"
CLONE_MANIFEST_PATH = Path(
    os.environ.get("LEGAL_TEMPLATE_CLONE_MANIFEST", str(EXPORT_SKILL_DIR / "assets" / "template-clone-manifest.json"))
).expanduser()
FIXED_IDENTITY = {
    "律所": os.environ.get("LEGAL_FIRM_NAME", "【律师事务所名称】"),
    "律师": os.environ.get("LEGAL_LAWYER_NAME", "【律师姓名】"),
    "地址": os.environ.get("LEGAL_FIRM_ADDRESS", "【律所地址】"),
    "电话": os.environ.get("LEGAL_LAWYER_PHONE", "【联系电话】"),
    "邮箱": os.environ.get("LEGAL_LAWYER_EMAIL", "【电子邮箱】"),
}
OLD_CONTACT_PATTERNS = [
    re.compile(r"1[3-9]\d{9}"),
    re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
]
LEGAL_CITATION_RE = re.compile(
    r"《[^》]{2,40}(法|条例|规定|解释|规则|办法|典|决定|纪要)》|"
    r"第[一二三四五六七八九十百千万零\d]+条|"
    r"指导性案例|入库案例|公报案例|司法解释|法释〔|法发〔"
)
BODY_RE = re.compile(r"<body\b[^>]*>(.*?)</body>", re.I | re.S)


@dataclass
class HtmlFacts:
    title: str = ""
    text: str = ""
    tags: set[str] = field(default_factory=set)
    has_table: bool = False
    has_signature: bool = False


class FactParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.facts = HtmlFacts()
        self.stack: list[tuple[str, dict[str, str]]] = []
        self._h1_parts: list[str] = []
        self._text_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_dict = {k: (v or "") for k, v in attrs}
        tag = tag.lower()
        self.facts.tags.add(tag)
        self.stack.append((tag, attr_dict))
        if tag == "table":
            self.facts.has_table = True
        if "signature" in attr_dict.get("class", "").split():
            self.facts.has_signature = True

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        for idx in range(len(self.stack) - 1, -1, -1):
            if self.stack[idx][0] == tag:
                del self.stack[idx:]
                break

    def handle_data(self, data: str) -> None:
        text = data.strip()
        if not text:
            return
        self._text_parts.append(text)
        if any(tag == "h1" for tag, _ in self.stack):
            self._h1_parts.append(text)

    def close(self) -> None:
        super().close()
        self.facts.title = " ".join("".join(self._h1_parts).split())
        self.facts.text = "\n".join(self._text_parts)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError("meta root must be a JSON object")
    return data


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_clone_template(template_id: str) -> dict[str, Any] | None:
    if not CLONE_MANIFEST_PATH.exists():
        return None
    data = load_json(CLONE_MANIFEST_PATH)
    for item in data.get("templates", []):
        if isinstance(item, dict) and item.get("template_id") == template_id:
            return item
    return None


def parse_html(text: str) -> HtmlFacts:
    parser = FactParser()
    parser.feed(text)
    parser.close()
    return parser.facts


def normalize_path(value: Any) -> Path | None:
    if not isinstance(value, str) or not value.strip():
        return None
    return Path(os.path.expandvars(value)).expanduser()


def existing_text(path: Path | None) -> str:
    if not path or not path.exists() or not path.is_file():
        return ""
    try:
        return read_text(path)
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8", errors="ignore")


def markdown_tables_to_html(text: str) -> tuple[str, bool]:
    lines = text.splitlines()
    out: list[str] = []
    changed = False
    i = 0
    sep_re = re.compile(r"^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?\s*$")
    while i < len(lines):
        if i + 1 < len(lines) and "|" in lines[i] and sep_re.match(lines[i + 1]):
            header = split_md_row(lines[i])
            rows: list[list[str]] = []
            i += 2
            while i < len(lines) and "|" in lines[i] and lines[i].strip():
                rows.append(split_md_row(lines[i]))
                i += 1
            out.append("<table>")
            out.append("<tr>" + "".join(f"<th>{html.escape(cell)}</th>" for cell in header) + "</tr>")
            for row in rows:
                out.append("<tr>" + "".join(f"<td>{html.escape(cell)}</td>" for cell in row) + "</tr>")
            out.append("</table>")
            changed = True
            continue
        out.append(lines[i])
        i += 1
    return "\n".join(out), changed


def split_md_row(line: str) -> list[str]:
    stripped = line.strip().strip("|")
    return [cell.strip() for cell in stripped.split("|")]


def ensure_signature(html_text: str, facts: HtmlFacts) -> tuple[str, bool]:
    if facts.has_signature:
        return html_text, False
    firm = FIXED_IDENTITY["律所"]
    lawyer = FIXED_IDENTITY["律师"]
    if firm not in facts.text and lawyer not in facts.text:
        return html_text, False
    body_match = BODY_RE.search(html_text)
    signature = (
        f"\n<p class=\"signature\">{firm}</p>"
        f"\n<p class=\"signature\">律师：{lawyer}</p>"
    )
    if body_match:
        insert_at = body_match.end(1)
        return html_text[:insert_at] + signature + html_text[insert_at:], True
    return html_text + signature, True


def fix_identity(html_text: str) -> tuple[str, list[str]]:
    changes: list[str] = []
    fixed = html_text
    firm = FIXED_IDENTITY["律所"]
    lawyer = FIXED_IDENTITY["律师"]
    lawyer_line = f"律师：{lawyer}"
    if firm not in fixed and lawyer_line in fixed:
        fixed = fixed.replace(lawyer_line, f"{firm}\n{lawyer_line}")
        changes.append("补入律所名称")
    if lawyer not in fixed:
        fixed = fixed.replace("</body>", f"<p class=\"signature\">{lawyer_line}</p>\n</body>")
        changes.append("补入律师姓名")
    fixed_lines: list[str] = []
    identity_markers = [lawyer, "律师", "律所", firm, "电话", "邮箱"]
    for line in fixed.splitlines():
        new_line = line
        if any(marker in line for marker in identity_markers):
            for pattern in OLD_CONTACT_PATTERNS:
                for match in list(pattern.finditer(new_line)):
                    value = match.group(0)
                    replacement = FIXED_IDENTITY["电话"] if "@" not in value else FIXED_IDENTITY["邮箱"]
                    if value != replacement:
                        new_line = new_line.replace(value, replacement)
                        changes.append(f"替换固定联系方式：{value} -> {replacement}")
        fixed_lines.append(new_line)
    fixed = "\n".join(fixed_lines)
    return fixed, changes


def write_checked_html(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def append_issue(bucket: dict[str, list[str]], key: str, message: str) -> None:
    bucket.setdefault(key, []).append(message)


def is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def validate_matter_paths(meta: dict[str, Any], issues: dict[str, list[str]]) -> None:
    matter_path = normalize_path(meta.get("matter_path"))
    system_record_path = normalize_path(meta.get("system_record_path"))

    if matter_path:
        if ".cache" in matter_path.parts or not is_relative_to(matter_path, MATTER_ROOT):
            append_issue(
                issues,
                "business",
                f"matter_path 必须位于正式业务文件区 {MATTER_ROOT}，不得使用 .cache 或临时目录：{matter_path}",
            )
        if is_relative_to(matter_path, SYSTEM_RECORD_ROOT):
            append_issue(issues, "business", f"matter_path 不得指向系统记录区：{matter_path}")
        if not matter_path.exists():
            append_issue(issues, "material", f"matter_path 不存在：{matter_path}")

    if system_record_path:
        if ".cache" in system_record_path.parts or not is_relative_to(system_record_path, SYSTEM_RECORD_ROOT):
            append_issue(
                issues,
                "business",
                f"system_record_path 必须位于正式系统记录区 {SYSTEM_RECORD_ROOT}，不得使用 .cache 或临时目录：{system_record_path}",
            )
        if not system_record_path.exists():
            append_issue(issues, "material", f"system_record_path 不存在：{system_record_path}")

    if not CURRENT_MATTER_PATH.exists():
        append_issue(issues, "material", f"当前事项.md 不存在：{CURRENT_MATTER_PATH}")
        return

    current_text = existing_text(CURRENT_MATTER_PATH)
    if not current_text.strip():
        append_issue(issues, "material", f"当前事项.md 为空或不可读：{CURRENT_MATTER_PATH}")
        return

    if matter_path and str(matter_path) not in current_text:
        append_issue(issues, "business", f"当前事项.md 未匹配 matter_path：{matter_path}")
    if system_record_path and str(system_record_path) not in current_text:
        append_issue(issues, "business", f"当前事项.md 未匹配 system_record_path：{system_record_path}")


def validate_doc_template_requirements(meta: dict[str, Any], facts: HtmlFacts, issues: dict[str, list[str]]) -> None:
    """Block known template-shape mistakes before formal Word export."""
    doc_type = str(meta.get("doc_type") or "")
    if "证据目录" not in doc_type:
        return

    if facts.has_table:
        append_issue(
            issues,
            "business",
            "证据目录必须按 templates/证据目录格式.md 的分组文本段落形式生成；未获用户明确覆盖时不得使用 table 表格。",
        )

    required_marks = ["第一组证据", "证明目的"]
    missing = [mark for mark in required_marks if mark not in facts.text]
    if missing:
        append_issue(
            issues,
            "business",
            "证据目录缺少模板要求的分组段落结构：" + "、".join(missing),
        )


def choose_status(
    issues: dict[str, list[str]],
    auto_fixes: list[str],
) -> tuple[str, str, str, bool]:
    if issues.get("hard"):
        return "HARD_BLOCK", "master_control", "停止导出，先处理根本阻断事项。", True
    if issues.get("material"):
        return "NEEDS_MATERIAL", "master_control", "回到材料读取、OCR、读取复查或法规校验流程，补齐证据后复审。", True
    if issues.get("confirmation"):
        return "NEEDS_USER_CONFIRMATION", "user", "向用户集中确认列明事项，写入确认记录后复审。", True
    if issues.get("business"):
        return "NEEDS_BUSINESS_REVISION", "business_skill", "退回业务 Skill 整改正文、HTML 或 preflight-meta.json 后复审。", True
    if auto_fixes:
        return "FIXED_PASS", "export_skill", "使用 draft_checked.html 进入法律文书模板与导出。", False
    return "PASS", "export_skill", "使用 draft_checked.html 进入法律文书模板与导出。", False


def make_report(
    report_path: Path,
    status: str,
    next_owner: str,
    next_action: str,
    source_skill: str,
    issues: dict[str, list[str]],
    confirmations: list[str],
    evidence_required: list[str],
    auto_fixes: list[str],
    rerun_required: bool,
) -> None:
    revision_items = issues.get("business", [])
    if issues.get("hard"):
        revision_items.extend(issues["hard"])
    lines = [
        "# 出稿前审查报告",
        "",
        f"review_status: {status}",
        f"next_owner: {next_owner}",
        f"next_action: {next_action}",
        f"return_to_skill: {source_skill if next_owner == 'business_skill' else ''}",
        "revision_items:",
    ]
    lines.extend(f"- {item}" for item in (revision_items or ["无"]))
    lines.append("confirmation_questions:")
    lines.extend(f"- {item}" for item in (confirmations or ["无"]))
    lines.append("evidence_required:")
    lines.extend(f"- {item}" for item in (evidence_required or ["无"]))
    lines.append(f"rerun_required: {'true' if rerun_required else 'false'}")
    lines.append("")
    lines.append("auto_fixes:")
    lines.extend(f"- {item}" for item in (auto_fixes or ["无"]))
    lines.append("")
    lines.append("issue_detail:")
    for key in ["material", "confirmation", "business", "hard"]:
        for item in issues.get(key, []):
            lines.append(f"- [{key}] {item}")
    if not any(issues.values()):
        lines.append("- 无")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def check(args: argparse.Namespace) -> int:
    issues: dict[str, list[str]] = {}
    confirmations: list[str] = []
    evidence_required: list[str] = []
    auto_fixes: list[str] = []

    html_path = args.html
    meta_path = args.meta
    meta_loaded = False
    if not html_path.exists():
        append_issue(issues, "business", f"draft.html 不存在：{html_path}")
        source_skill = ""
        original_html = ""
        meta: dict[str, Any] = {}
    else:
        original_html = read_text(html_path)
    if not meta_path.exists():
        append_issue(issues, "business", f"preflight-meta.json 不存在：{meta_path}")
        meta = {}
    else:
        try:
            meta = load_json(meta_path)
            meta_loaded = True
        except Exception as exc:
            append_issue(issues, "business", f"preflight-meta.json 无法解析：{exc}")
            meta = {}

    source_skill = str(meta.get("source_skill") or "")
    for key in ["source_skill", "doc_type", "output_purpose", "profile", "matter_path", "system_record_path", "evidence"]:
        if key not in meta or meta.get(key) in ("", None, {}):
            append_issue(issues, "business", f"preflight-meta.json 缺少必要字段：{key}")
    if meta_loaded:
        validate_matter_paths(meta, issues)

    html_text = original_html
    html_text, table_fixed = markdown_tables_to_html(html_text)
    if table_fixed:
        auto_fixes.append("Markdown 表格已转换为 HTML table")
    html_text, identity_fixes = fix_identity(html_text)
    auto_fixes.extend(identity_fixes)
    facts = parse_html(html_text)
    html_text, signature_fixed = ensure_signature(html_text, facts)
    if signature_fixed:
        auto_fixes.append("补入 signature 类落款段")
        facts = parse_html(html_text)

    if not facts.title:
        append_issue(issues, "business", "draft.html 缺少 h1 标题")
    if len(facts.text.strip()) < 30:
        append_issue(issues, "business", "draft.html 正文内容过短或无法识别")
    if "p" not in facts.tags:
        append_issue(issues, "business", "draft.html 缺少 p 正文段落")
    validate_doc_template_requirements(meta, facts, issues)

    profile = str(meta.get("profile") or "fallback_desktop_word")
    if not (PROFILES_DIR / f"{profile}.json").exists():
        auto_fixes.append(f"profile 未命中，导出时应使用 fallback_desktop_word：{profile}")

    evidence = meta.get("evidence") if isinstance(meta.get("evidence"), dict) else {}
    required_evidence = {
        "reading_review_path": "读取复查摘要",
        "source_boundary_path": "来源边界记录",
    }
    if LEGAL_CITATION_RE.search(facts.text):
        required_evidence["legal_verification_path"] = "法规校验摘要"
    required_confirmations = meta.get("required_confirmations") or []
    if required_confirmations:
        required_evidence["user_confirmation_source"] = "用户确认记录"

    evidence_texts: dict[str, str] = {}
    if meta_loaded and isinstance(meta.get("evidence"), dict):
        for key, label in required_evidence.items():
            path = normalize_path(evidence.get(key))
            text = existing_text(path)
            evidence_texts[key] = text
            if not path:
                append_issue(issues, "material", f"缺少{label}路径：evidence.{key}")
                evidence_required.append(label)
            elif not path.exists():
                append_issue(issues, "material", f"{label}文件不存在：{path}")
                evidence_required.append(str(path))
            elif not text.strip():
                append_issue(issues, "material", f"{label}文件为空或不可读：{path}")
                evidence_required.append(str(path))

    reading_text = evidence_texts.get("reading_review_path", "")
    if reading_text and "读取复查摘要" not in reading_text:
        append_issue(issues, "material", "读取复查摘要文件未包含【读取复查摘要】标记")
    boundary_text = evidence_texts.get("source_boundary_path", "")
    if boundary_text and not any(mark in boundary_text for mark in ["来源", "边界", "未核验", "已核验"]):
        append_issue(issues, "business", "来源边界记录内容未体现来源边界或核验状态")
    legal_text = evidence_texts.get("legal_verification_path", "")
    if legal_text and not any(mark in legal_text for mark in ["法规校验摘要", "现行有效", "已核验", "法宝", "官方"]):
        append_issue(issues, "business", "法规校验摘要内容未体现法规核验状态")

    confirmation_text = evidence_texts.get("user_confirmation_source", "")
    if not isinstance(required_confirmations, list):
        append_issue(issues, "business", "required_confirmations 必须是数组")
        required_confirmations = []
    for item in required_confirmations:
        item_text = str(item)
        if item_text and item_text not in confirmation_text:
            append_issue(issues, "confirmation", f"缺少用户确认：{item_text}")
            confirmations.append(item_text)

    known_gaps = meta.get("known_gaps") or []
    if isinstance(known_gaps, list) and known_gaps:
        append_issue(issues, "confirmation", "存在 known_gaps，需用户确认是否继续出稿：" + "；".join(map(str, known_gaps)))
        confirmations.extend(map(str, known_gaps))
    elif not isinstance(known_gaps, list):
        append_issue(issues, "business", "known_gaps 必须是数组")

    status, next_owner, next_action, rerun_required = choose_status(issues, auto_fixes)
    write_checked_html(args.output_html, html_text)
    make_report(
        args.report,
        status,
        next_owner,
        next_action,
        source_skill,
        issues,
        confirmations,
        evidence_required,
        auto_fixes,
        rerun_required,
    )
    print(f"review_status: {status}")
    print(f"next_owner: {next_owner}")
    print(f"report: {args.report}")
    print(f"output_html: {args.output_html}")
    return 0 if status in {"PASS", "FIXED_PASS"} else 2


def validate_clone_evidence(qc_meta: dict[str, Any], issues: dict[str, list[str]], evidence_required: list[str]) -> None:
    evidence = qc_meta.get("evidence") if isinstance(qc_meta.get("evidence"), dict) else {}
    required_evidence = {
        "reading_review_path": "读取复查摘要",
        "source_boundary_path": "来源边界记录",
        "user_confirmation_source": "用户确认记录",
    }
    if qc_meta.get("legal_verification_required", True):
        required_evidence["legal_verification_path"] = "法规校验摘要"

    for key, label in required_evidence.items():
        path = normalize_path(evidence.get(key))
        text = existing_text(path)
        if not path:
            append_issue(issues, "material", f"缺少{label}路径：evidence.{key}")
            evidence_required.append(label)
        elif not path.exists():
            append_issue(issues, "material", f"{label}文件不存在：{path}")
            evidence_required.append(str(path))
        elif not text.strip():
            append_issue(issues, "material", f"{label}文件为空或不可读：{path}")
            evidence_required.append(str(path))
        elif key == "reading_review_path" and "读取复查摘要" not in text:
            append_issue(issues, "material", "读取复查摘要文件未包含【读取复查摘要】标记")
        elif key == "source_boundary_path" and not any(mark in text for mark in ["来源", "边界", "未核验", "已核验"]):
            append_issue(issues, "business", "来源边界记录内容未体现来源边界或核验状态")
        elif key == "legal_verification_path" and not any(mark in text for mark in ["法规校验摘要", "现行有效", "已核验", "法宝", "官方"]):
            append_issue(issues, "business", "法规校验摘要内容未体现法规核验状态")


def validate_clone_field_sources(
    complaint_data: dict[str, Any],
    fill_plan: dict[str, Any],
    issues: dict[str, list[str]],
    confirmations: list[str],
) -> None:
    fields = complaint_data.get("fields")
    source_map = complaint_data.get("source_map")
    known_gaps = complaint_data.get("known_gaps", [])
    plan_fields = fill_plan.get("fields")

    if not isinstance(fields, dict) or not fields:
        append_issue(issues, "business", "complaint-data.json 必须包含非空 fields 对象")
        fields = {}
    if not isinstance(source_map, dict):
        append_issue(issues, "business", "complaint-data.json 必须包含 source_map 对象")
        source_map = {}
    if not isinstance(known_gaps, list):
        append_issue(issues, "business", "complaint-data.json known_gaps 必须是数组")
        known_gaps = []
    if known_gaps:
        append_issue(issues, "confirmation", "complaint-data.json 存在字段缺口，需用户确认后才能正式填充：" + "；".join(map(str, known_gaps)))
        confirmations.extend(map(str, known_gaps))

    gap_ids = {str(item.get("field_id") if isinstance(item, dict) else item) for item in known_gaps}
    for field_id in fields:
        if field_id not in source_map and field_id not in gap_ids:
            append_issue(issues, "business", f"字段缺少来源或缺口说明：{field_id}")

    if not isinstance(plan_fields, list) or not plan_fields:
        append_issue(issues, "business", "fill-plan.json 必须包含非空 fields 数组")
        return

    seen_targets: set[tuple[int, int, int, str]] = set()
    for idx, field in enumerate(plan_fields, 1):
        if not isinstance(field, dict):
            append_issue(issues, "business", f"fill-plan 字段 #{idx} 不是对象")
            continue
        field_id = str(field.get("field_id") or "")
        if not field_id:
            append_issue(issues, "business", f"fill-plan 字段 #{idx} 缺少 field_id")
        elif field_id not in fields:
            append_issue(issues, "business", f"fill-plan 字段不在 complaint-data.fields 中：{field_id}")
        target = field.get("target")
        if not isinstance(target, dict):
            append_issue(issues, "business", f"fill-plan 字段 {field_id or idx} 缺少 target")
            continue
        missing_coords = [key for key in ["table_index", "row_index", "cell_index"] if key not in target]
        if missing_coords:
            append_issue(issues, "business", f"fill-plan 字段 {field_id or idx} 缺少表格坐标：" + "、".join(missing_coords))
        else:
            try:
                target_key = (
                    int(target["table_index"]),
                    int(target["row_index"]),
                    int(target["cell_index"]),
                    str(target.get("anchor_text") or ""),
                )
                if target_key in seen_targets:
                    append_issue(issues, "business", f"fill-plan 重复命中同一坐标和锚点：{field_id or idx}")
                seen_targets.add(target_key)
            except Exception:
                append_issue(issues, "business", f"fill-plan 字段 {field_id or idx} 表格坐标必须为数字")
        mode = str(field.get("mode") or "")
        if mode not in {"append_after_anchor", "replace_anchor", "replace_cell"}:
            append_issue(issues, "business", f"fill-plan 字段 {field_id or idx} mode 非法：{mode}")
        if mode in {"append_after_anchor", "replace_anchor"} and not str(target.get("anchor_text") or ""):
            append_issue(issues, "business", f"fill-plan 字段 {field_id or idx} 使用锚点模式但缺少 anchor_text")


def check_clone(args: argparse.Namespace) -> int:
    issues: dict[str, list[str]] = {}
    confirmations: list[str] = []
    evidence_required: list[str] = []
    auto_fixes: list[str] = []

    complaint_data: dict[str, Any] = {}
    fill_plan: dict[str, Any] = {}
    qc_meta: dict[str, Any] = {}
    for path, label, target in [
        (args.complaint_data, "complaint-data.json", "complaint"),
        (args.fill_plan, "fill-plan.json", "fill_plan"),
        (args.qc_meta, "qc-meta.json", "qc_meta"),
    ]:
        if not path or not path.exists():
            append_issue(issues, "business", f"{label} 不存在：{path}")
            continue
        try:
            data = load_json(path)
        except Exception as exc:
            append_issue(issues, "business", f"{label} 无法解析：{exc}")
            continue
        if target == "complaint":
            complaint_data = data
        elif target == "fill_plan":
            fill_plan = data
        else:
            qc_meta = data

    template_id = str(complaint_data.get("template_id") or fill_plan.get("template_id") or qc_meta.get("template_id") or "")
    if not template_id:
        append_issue(issues, "business", "要素式文书缺少 template_id")
    if template_id:
        for label, data in [("complaint-data.json", complaint_data), ("fill-plan.json", fill_plan), ("qc-meta.json", qc_meta)]:
            value = str(data.get("template_id") or "")
            if value and value != template_id:
                append_issue(issues, "business", f"{label} template_id 不一致：{value} != {template_id}")
        try:
            template = load_clone_template(template_id)
        except Exception as exc:
            template = None
            append_issue(issues, "business", f"template-clone-manifest.json 无法解析：{exc}")
        if not template:
            append_issue(issues, "business", f"template_id 未命中 template-clone-manifest.json：{template_id}")
        else:
            source_docx = Path(os.path.expandvars(str(template.get("source_docx") or ""))).expanduser()
            if not source_docx.exists():
                append_issue(issues, "material", f"DOCX 母版不存在：{source_docx}")
            elif template.get("sha256") and sha256(source_docx) != template.get("sha256"):
                append_issue(issues, "business", f"DOCX 母版 sha256 不匹配：{template_id}")
            if template.get("doc_type") != "民事起诉状":
                append_issue(issues, "business", f"要素式模板 doc_type 非民事起诉状：{template.get('doc_type')}")

    for key in ["template_id", "matter_path", "system_record_path", "evidence"]:
        if key not in qc_meta or qc_meta.get(key) in ("", None, {}):
            append_issue(issues, "business", f"qc-meta.json 缺少必要字段：{key}")
    if qc_meta:
        validate_matter_paths(qc_meta, issues)
        validate_clone_evidence(qc_meta, issues, evidence_required)
    if complaint_data or fill_plan:
        validate_clone_field_sources(complaint_data, fill_plan, issues, confirmations)

    status, next_owner, next_action, rerun_required = choose_status(issues, auto_fixes)
    if status in {"PASS", "FIXED_PASS"}:
        next_action = "使用 complaint-data.json、fill-plan.json 进入 DOCX 母版克隆填充和模板克隆质控。"
    elif next_owner == "business_skill":
        next_action = "退回业务 Skill 整改 complaint-data.json、fill-plan.json 或 qc-meta.json 后复审。"
    make_report(
        args.report,
        status,
        next_owner,
        next_action,
        str(qc_meta.get("source_skill") or "诉讼文书起草"),
        issues,
        confirmations,
        evidence_required,
        auto_fixes,
        rerun_required,
    )
    print(f"review_status: {status}")
    print(f"next_owner: {next_owner}")
    print(f"report: {args.report}")
    return 0 if status in {"PASS", "FIXED_PASS"} else 2


def main() -> int:
    parser = argparse.ArgumentParser(description="Review legal deliverables before DOCX export.")
    parser.add_argument("--html", type=Path)
    parser.add_argument("--meta", type=Path)
    parser.add_argument("--output-html", type=Path)
    parser.add_argument("--complaint-data", type=Path)
    parser.add_argument("--fill-plan", type=Path)
    parser.add_argument("--qc-meta", type=Path)
    parser.add_argument("--report", required=True, type=Path)
    args = parser.parse_args()
    if args.complaint_data or args.fill_plan or args.qc_meta:
        if not (args.complaint_data and args.fill_plan and args.qc_meta):
            parser.error("--complaint-data, --fill-plan and --qc-meta must be provided together")
        return check_clone(args)
    if not (args.html and args.meta and args.output_html):
        parser.error("--html, --meta and --output-html are required for HTML preflight")
    return check(args)


if __name__ == "__main__":
    sys.exit(main())
