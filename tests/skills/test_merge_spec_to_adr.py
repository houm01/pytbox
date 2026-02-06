from __future__ import annotations

import importlib.util
import sys
from datetime import date
from pathlib import Path
from types import ModuleType


REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


def _load_module() -> ModuleType:
    script_path = REPO_ROOT / "skills" / "spec-adr-rollup" / "scripts" / "merge_spec_to_adr.py"
    module_spec = importlib.util.spec_from_file_location("merge_spec_to_adr", script_path)
    if module_spec is None or module_spec.loader is None:
        raise RuntimeError("failed to load merge_spec_to_adr module")
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    return module


MODULE = _load_module()


def test_merge_spec_to_adr_success(tmp_path: Path) -> None:
    spec_dir = tmp_path / "docs" / "specs" / "2026-02-feishu"
    spec_dir.mkdir(parents=True)

    (spec_dir / "spec.md").write_text(
        "# Entry\n\n1) 01-first.md\n2) 02-second.md\n- 必须遵守 AGENTS.md\n", encoding="utf-8"
    )
    (spec_dir / "01-first.md").write_text("# first\ncontent A\n", encoding="utf-8")
    (spec_dir / "02-second.md").write_text("# second\ncontent B\n", encoding="utf-8")

    adr_root = tmp_path / "docs" / "adr"
    response = MODULE.merge_spec_to_adr(spec_dir=spec_dir, adr_root=adr_root, run_date=date(2026, 2, 7))

    assert response.code == 0
    output_path = adr_root / "2026-02-feishu.md"
    assert output_path.exists()

    content = output_path.read_text(encoding="utf-8")
    assert "| spec.md | Done | 2026-02-07 | Merged |" in content
    assert "| 01-first.md | Done | 2026-02-07 | Merged |" in content
    assert "| 02-second.md | Done | 2026-02-07 | Merged |" in content
    assert "AGENTS.md" not in content
    assert content.index("### spec.md") < content.index("### 01-first.md") < content.index("### 02-second.md")


def test_merge_spec_to_adr_marks_missing_file_as_abandoned(tmp_path: Path) -> None:
    spec_dir = tmp_path / "docs" / "specs" / "feature-x"
    spec_dir.mkdir(parents=True)

    (spec_dir / "spec.md").write_text(
        "# Entry\n\n1) 01-keep.md\n2) 99-missing.md\n", encoding="utf-8"
    )
    (spec_dir / "01-keep.md").write_text("# keep\n", encoding="utf-8")

    response = MODULE.merge_spec_to_adr(
        spec_dir=spec_dir,
        adr_root=tmp_path / "docs" / "adr",
        run_date=date(2026, 2, 7),
    )

    assert response.code == 0
    content = (tmp_path / "docs" / "adr" / "feature-x.md").read_text(encoding="utf-8")
    assert "| 99-missing.md | 放弃 | 2026-02-07 | File not found |" in content


def test_merge_spec_to_adr_is_idempotent_overwrite(tmp_path: Path) -> None:
    spec_dir = tmp_path / "docs" / "specs" / "idempotent"
    spec_dir.mkdir(parents=True)

    sub_file = spec_dir / "01-item.md"
    sub_file.write_text("# version1\n", encoding="utf-8")

    adr_root = tmp_path / "docs" / "adr"
    first_resp = MODULE.merge_spec_to_adr(
        spec_dir=spec_dir,
        adr_root=adr_root,
        run_date=date(2026, 2, 7),
    )
    assert first_resp.code == 0

    sub_file.write_text("# version2\n", encoding="utf-8")
    second_resp = MODULE.merge_spec_to_adr(
        spec_dir=spec_dir,
        adr_root=adr_root,
        run_date=date(2026, 2, 7),
    )

    assert second_resp.code == 0
    content = (adr_root / "idempotent.md").read_text(encoding="utf-8")
    assert "# version2" in content
    assert "# version1" not in content
