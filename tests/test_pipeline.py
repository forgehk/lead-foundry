"""End-to-end pipeline test against the example CSV."""

from pathlib import Path

from lead_foundry.pipeline import Pipeline

EXAMPLES = Path(__file__).parent.parent / "examples"

def test_pipeline_against_example():
    scored = Pipeline().run(
        EXAMPLES / "raw_leads.csv",
        icp_path=EXAMPLES / "icp.yaml",
    )
    # 6 leads in (one blank row, two dupes on calmwell.io) -> 4 unique after dedupe
    # (plus the blank one if it survives — it has no domain so it does)
    verdicts = [sl.verdict for sl in scored]
    # Maya at CalmWell should be the top scorer.
    assert scored[0].lead.domain == "calmwell.io"
    assert scored[0].verdict in {"hot", "warm"}
    # The industrial-manufacturing director should be cold.
    bigcorp = next(sl for sl in scored if sl.lead.domain == "bigcorp.com")
    assert bigcorp.verdict == "cold"

def test_pipeline_dedupes_calmwell():
    scored = Pipeline().run(
        EXAMPLES / "raw_leads.csv",
        icp_path=EXAMPLES / "icp.yaml",
    )
    calmwell = [sl for sl in scored if sl.lead.domain == "calmwell.io"]
    assert len(calmwell) == 1
