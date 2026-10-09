from mcd_team_meal_director.cli import main


def test_dry_run_cli_prints_three_plans(capsys: object) -> None:
    exit_code = main(
        [
            "--people",
            "6",
            "--budget",
            "180",
            "--calorie-conscious",
            "2",
            "--dietary-goal",
            "丰富一点",
        ]
    )

    output = capsys.readouterr().out  # type: ignore[attr-defined]
    assert exit_code == 0
    assert "DRY-RUN" in output
    assert "最省钱方案" in output
    assert "营养相对均衡方案" in output
    assert "品类最丰富方案" in output
    assert output.count("预估合计") == 3
