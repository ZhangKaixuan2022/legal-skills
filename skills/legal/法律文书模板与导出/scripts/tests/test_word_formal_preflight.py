#!/usr/bin/env python3
"""Regression tests for formal Word preflight gates."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


LEGAL_DIR = Path(__file__).resolve().parents[3]
PREFLIGHT = LEGAL_DIR / "法律文书出稿前审查" / "scripts" / "preflight_check.py"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class ClonePreflightTests(unittest.TestCase):
    def write_clone_case(self, root: Path, *, omit_table_index: bool = False) -> dict[str, Path]:
        workspace = root / "workspace"
        matter_path = workspace / "示例事项"
        system_record_path = workspace / "_系统记录" / "示例事项"
        current_matter = workspace / "_系统记录" / "当前事项.md"
        matter_path.mkdir(parents=True, exist_ok=True)
        system_record_path.mkdir(parents=True, exist_ok=True)
        current_matter.write_text(
            f"# 当前事项\n业务文件路径：{matter_path}\n系统记录路径：{system_record_path}\n",
            encoding="utf-8",
        )
        template_docx = root / "template.docx"
        template_docx.write_bytes(b"synthetic docx placeholder for preflight hash check")
        clone_manifest = root / "template-clone-manifest.json"
        clone_manifest.write_text(
            json.dumps(
                {
                    "version": "test",
                    "templates": [
                        {
                            "template_id": "civil_complaint_private_lending_v1",
                            "doc_type": "民事起诉状",
                            "case_cause": "民间借贷纠纷",
                            "source_docx": str(template_docx),
                            "sha256": sha256(template_docx),
                            "expected_tables": 1,
                            "expected_grid_span": 0,
                            "expected_vmerge": 0,
                            "expected_row_heights": 0,
                        }
                    ],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        for name, text in {
            "reading_review.md": "# 读取复查摘要\n文件名：合成测试\n存疑项：无\n",
            "source_boundary.md": "# 来源边界记录\n已核验：合成测试\n未核验：无\n",
            "legal_verification.md": "# 法规校验摘要\n已核验：不引用实体法条\n现行有效：不适用\n",
            "user_confirmation.md": "# 用户确认记录\n已确认：合成测试字段\n",
        }.items():
            (root / name).write_text(text, encoding="utf-8")

        complaint_data = {
            "template_id": "civil_complaint_private_lending_v1",
            "fields": {"plaintiff.natural.name": "张三"},
            "source_map": {"plaintiff.natural.name": "fixture"},
            "known_gaps": [],
        }
        target = {
            "table_index": 1,
            "row_index": 3,
            "cell_index": 2,
            "anchor_text": "姓名：",
        }
        if omit_table_index:
            target.pop("table_index")
        fill_plan = {
            "template_id": "civil_complaint_private_lending_v1",
            "fields": [
                {
                    "field_id": "plaintiff.natural.name",
                    "value": "张三",
                    "target": target,
                    "mode": "append_after_anchor",
                }
            ],
        }
        qc_meta = {
            "template_id": "civil_complaint_private_lending_v1",
            "source_skill": "诉讼文书起草",
            "doc_type": "民事起诉状",
            "case_cause": "民间借贷纠纷",
            "matter_path": str(matter_path),
            "system_record_path": str(system_record_path),
            "legal_verification_required": True,
            "evidence": {
                "reading_review_path": str(root / "reading_review.md"),
                "source_boundary_path": str(root / "source_boundary.md"),
                "legal_verification_path": str(root / "legal_verification.md"),
                "user_confirmation_source": str(root / "user_confirmation.md"),
            },
        }
        paths = {
            "complaint_data": root / "complaint-data.json",
            "fill_plan": root / "fill-plan.json",
            "qc_meta": root / "qc-meta.json",
            "report": root / "report.md",
            "workspace": workspace,
            "clone_manifest": clone_manifest,
        }
        paths["complaint_data"].write_text(json.dumps(complaint_data, ensure_ascii=False), encoding="utf-8")
        paths["fill_plan"].write_text(json.dumps(fill_plan, ensure_ascii=False), encoding="utf-8")
        paths["qc_meta"].write_text(json.dumps(qc_meta, ensure_ascii=False), encoding="utf-8")
        return paths

    def run_preflight(self, paths: dict[str, Path]) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env["LEGAL_WORKSPACE"] = str(paths["workspace"])
        env["LEGAL_TEMPLATE_CLONE_MANIFEST"] = str(paths["clone_manifest"])
        return subprocess.run(
            [
                sys.executable,
                str(PREFLIGHT),
                "--complaint-data",
                str(paths["complaint_data"]),
                "--fill-plan",
                str(paths["fill_plan"]),
                "--qc-meta",
                str(paths["qc_meta"]),
                "--report",
                str(paths["report"]),
            ],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            env=env,
            check=False,
        )

    def test_clone_preflight_accepts_complete_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = self.write_clone_case(Path(tmp))
            proc = self.run_preflight(paths)
            self.assertEqual(proc.returncode, 0, proc.stdout)
            self.assertIn("review_status: PASS", proc.stdout)

    def test_clone_preflight_blocks_missing_table_coordinate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = self.write_clone_case(Path(tmp), omit_table_index=True)
            proc = self.run_preflight(paths)
            self.assertNotEqual(proc.returncode, 0, proc.stdout)
            report = paths["report"].read_text(encoding="utf-8")
            self.assertIn("NEEDS_BUSINESS_REVISION", report)
            self.assertIn("缺少表格坐标：table_index", report)


if __name__ == "__main__":
    unittest.main()
