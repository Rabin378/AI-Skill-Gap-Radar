from skill_gap_radar.cli import main


def test_analyze_prints_the_headline_and_learn_next(capsys):
    assert main(["analyze", "--top", "3"]) == 0

    output = capsys.readouterr().out
    assert "SKILL RADAR" in output
    assert "Learn next" in output
    assert "Skill gap:" in output


def test_report_command_writes_the_file(tmp_path, capsys):
    target = tmp_path / "out.html"

    assert main(["report", "--output", str(target)]) == 0

    assert target.exists()
    assert "Wrote report:" in capsys.readouterr().out


def test_bad_input_returns_an_error_code_instead_of_a_traceback(tmp_path, capsys):
    missing = tmp_path / "missing.csv"

    code = main(["analyze", "--user", str(missing)])

    assert code == 1
    assert "Error:" in capsys.readouterr().err


def test_no_subcommand_defaults_to_analyze(capsys):
    assert main([]) == 0
    assert "SKILL RADAR" in capsys.readouterr().out
