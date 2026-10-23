"""Tests for govcheck. Run: python -m unittest discover -s tools"""
from __future__ import annotations

import contextlib
import io
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import govcheck  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
WF = "workflows/template-creation.yaml"


class GovTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.gov = self.tmp / "governance"
        shutil.copytree(REPO / "governance", self.gov)

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp)

    def run_cli(self, *argv: str) -> tuple[int, str]:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            code = govcheck.main(["--gov", str(self.gov), *argv])
        return code, buf.getvalue()

    def edit(self, rel: str, old: str, new: str) -> None:
        path = self.gov / rel
        text = path.read_text(encoding="utf-8")
        self.assertIn(old, text)
        path.write_text(text.replace(old, new, 1), encoding="utf-8")


class TestValidate(GovTestCase):
    def test_repository_records_validate(self) -> None:
        code, out = self.run_cli("validate")
        self.assertEqual(code, 0, out)

    def test_unrecorded_step_change_blocks(self) -> None:
        self.edit(WF, "check: Every part has a placement", "check: Every part has a placement and a reason")
        self.run_cli("render")
        code, out = self.run_cli("validate")
        self.assertEqual(code, 1)
        self.assertIn("the steps changed since the last change record", out)

    def test_record_change_clears_the_block_and_bumps_version(self) -> None:
        _, wf = govcheck.Registry.read(self.gov).workflows["WF-template-creation"]
        expected = govcheck.bump(govcheck.current_version(wf), "minor")
        self.edit(WF, "check: Every part has a placement", "check: Every part has a placement and a reason")
        code, out = self.run_cli(
            "record-change", "--summary", "Set placement check asks for a reason",
            "--ruled-by", "Ingrid", "--date", "2026-10-24", "--steps", "set-placement",
        )
        self.assertEqual(code, 0, out)
        self.assertIn(f"version {expected}", out)
        code, out = self.run_cli("validate")
        self.assertEqual(code, 0, out)
        page = (self.gov / "workflows/template-creation.md").read_text(encoding="utf-8")
        self.assertIn("Set placement check asks for a reason", page)

    def test_record_change_refuses_when_nothing_changed(self) -> None:
        code, _ = self.run_cli("record-change", "--summary", "Nothing")
        self.assertEqual(code, 1)

    def test_tag_step_must_be_last(self) -> None:
        reg = govcheck.Registry.read(self.gov)
        path, wf = reg.workflows["WF-template-creation"]
        wf["steps"].insert(0, wf["steps"].pop())  # move tag-stage-and-kind to the front
        f = govcheck.Findings()
        govcheck.validate_workflow(f, reg, path, wf)
        self.assertTrue(any("must be the last step" in m for _, _, m in f.items))

    def test_unknown_ruling_blocks(self) -> None:
        self.edit(WF, "rulings: [placement-default-pinned", "rulings: [no-such-ruling, placement-default-pinned")
        code, out = self.run_cli("validate")
        self.assertEqual(code, 1)
        self.assertIn("no-such-ruling", out)

    def test_value_outside_vocabulary_blocks(self) -> None:
        self.edit(WF, "level: report\n    standing: ruled", "level: report\n    standing: approved")
        code, out = self.run_cli("validate")
        self.assertEqual(code, 1)
        self.assertIn("'approved' is not in vocabulary standing", out)

    def test_stale_page_blocks(self) -> None:
        (self.gov / "workflows/template-creation.md").write_text("edited by hand\n", encoding="utf-8")
        code, out = self.run_cli("validate")
        self.assertEqual(code, 1)
        self.assertIn("page is out of date", out)


class TestNames(GovTestCase):
    def test_good_names(self) -> None:
        code, out = self.run_cli("names", "IB-FIRST.slots.md", "EH-STD-MODS Mods Register.docx",
                                 "ICH-M11Template-11.7-DataGovernance-2025-11.pdf")
        self.assertEqual(code, 0, out)

    def test_positional_and_slash_names_block(self) -> None:
        code, out = self.run_cli("names", "1-csr-methods-and-results-TEMPLATE.docx", "Type A/B meeting")
        self.assertEqual(code, 1)
        self.assertIn("no-positional-prefix", out)
        self.assertIn("no-slash", out)

    def test_required_pattern(self) -> None:
        code, out = self.run_cli("names", "--as", "mod-id", "MOD_Metatag")
        self.assertEqual(code, 1)
        self.assertIn("does not match mod-id", out)


class TestBlock(GovTestCase):
    def write(self, name: str, text: str) -> Path:
        path = self.tmp / name
        path.write_text(text, encoding="utf-8")
        return path

    def test_conforming_block(self) -> None:
        path = self.write("IB-FIRST.alteration.md", (
            "# IB-FIRST alteration of parts\n\nWorkflow step: **Set alteration** (report level).\n\n"
            "## Check, run 22 October 2026\n\nThe check passes.\n"
        ))
        code, out = self.run_cli("block", str(path))
        self.assertEqual(code, 0, out)

    def test_unknown_step_blocks(self) -> None:
        path = self.write("IB-FIRST.alteration.md", "Workflow step: **Lock the parts**\n")
        code, out = self.run_cli("block", str(path))
        self.assertEqual(code, 1)
        self.assertIn("record the change first", out)

    def test_wrong_file_for_step_blocks(self) -> None:
        path = self.write("IB-FIRST.locks.md", "Workflow step: **Set alteration**\n\nCheck passes.\n")
        code, out = self.run_cli("block", str(path))
        self.assertEqual(code, 1)
        self.assertIn("writes <LABEL>.alteration.md", out)

    def test_step_named_in_running_text(self) -> None:
        # IB-FIRST.base.md: "Assembled ... at the workflow step **Assemble the base**."
        path = self.write("IB-FIRST.base.md", (
            "Assembled 22 October 2026 at the workflow step **Assemble the base**.\n\n## Check\n\nCounts match.\n"
        ))
        code, out = self.run_cli("block", str(path))
        self.assertEqual(code, 0, out)
        self.assertNotIn("Rule and publish", out)

    def test_suffix_fallback_takes_first_step(self) -> None:
        # Two steps write <LABEL>.base.md; with no step line the earlier one applies.
        path = self.write("IB-FIRST.base.md", "Nothing here names a step.\n")
        code, out = self.run_cli("block", str(path))
        self.assertIn("expected **Assemble the base**", out)

    def test_result_line_counts_as_check_result(self) -> None:
        path = self.write("IB-FIRST.components.md", (
            "Workflow step: **Map sections to components**\n\nResult: a component exists for every section.\n"
        ))
        code, out = self.run_cli("block", str(path))
        self.assertEqual(code, 0, out)
        self.assertNotIn("records no check result", out)

    def test_lock_values_in_tables(self) -> None:
        good = self.write("IB-FIRST.alteration.md", (
            "Workflow step: **Set alteration**\n\n| Part | Lock | What may be altered |\n|---|---|---|\n"
            "| Title Page | Hard: edition number | Nothing |\n| Summary | Soft, from approval | Composed text |\n"
            "| Introduction | Set at component level | — |\n\n## Check, run 22 October 2026\n\nThe check passes.\n"
        ))
        code, out = self.run_cli("block", str(good))
        self.assertEqual(code, 0, out)
        bad = self.write("IB-FIRST.alteration.md", (
            "Workflow step: **Set alteration**\n\n| Part | Lock |\n|---|---|\n| Title Page | Frozen |\n"
            "| Summary | Set aside |\n\nThe check passes.\n"
        ))
        code, out = self.run_cli("block", str(bad))
        self.assertEqual(code, 1)
        self.assertIn("'Frozen'", out)
        self.assertIn("'Set aside'", out)

    def test_vocabulary_in_block(self) -> None:
        path = self.write("IB-FIRST.placement.md", (
            "Workflow step: **Set placement**\n\n- Placement: floating. Lock: hard\n\nThe check passes.\n"
        ))
        code, out = self.run_cli("block", str(path))
        self.assertEqual(code, 1)
        self.assertIn("'floating'", out)


if __name__ == "__main__":
    unittest.main()
