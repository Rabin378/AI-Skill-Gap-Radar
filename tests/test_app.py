from pathlib import Path

import pytest

streamlit_testing = pytest.importorskip("streamlit.testing.v1")

APP_PATH = Path(__file__).resolve().parents[1] / "src" / "skill_gap_radar" / "app.py"


@pytest.fixture(scope="module")
def dashboard():
    return streamlit_testing.AppTest.from_file(str(APP_PATH), default_timeout=60).run()


def test_dashboard_renders_without_exceptions(dashboard):
    assert not dashboard.exception
    assert dashboard.title[0].value == "Skill Radar"
    assert len(dashboard.metric) == 3


def test_dashboard_coverage_matches_the_cli_for_the_same_profile(dashboard):
    # The CLI and report give 16.6% coverage for the sample profile, which rounds to 17%.
    # Before the fix the dashboard dropped levels for skills outside the top 12 and showed 13%.
    coverage_metric = dashboard.metric[0]
    assert coverage_metric.label == "Market value you cover"
    assert coverage_metric.value == "17%"
