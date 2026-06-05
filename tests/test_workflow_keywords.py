import sys
import tomllib
from pathlib import Path

from yambo_tester.cli import load_workflow_keywords, main


def collect_workflow_keywords(tests_root):
    executables = set()
    runlevels = set()

    for tests_file in tests_root.rglob("tests.toml"):
        with tests_file.open("rb") as f:
            tests = tomllib.load(f)

        for name, spec in tests.items():
            if name == "sha256":
                continue
            if not isinstance(spec, dict):
                continue

            exe = spec.get("exe")
            if exe:
                executables.add(exe)

            runlevel = spec.get("runlevel")
            if runlevel:
                runlevels.add(runlevel)

    return {
        "executables": sorted(executables),
        "runlevels": sorted(runlevels),
    }


def test_packaged_workflow_keywords_match_imported_tests():
    tests_root = Path(__file__).resolve().parents[1] / "src" / "yambo_tester" / "tests"
    expected = collect_workflow_keywords(tests_root)

    assert load_workflow_keywords() == expected


def test_list_executables_flag_prints_keywords_and_exits(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["yambo-tester", "--list-executables"])
    monkeypatch.setattr("yambo_tester.cli.setup_logging", lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("setup_logging should not run")))

    main()

    captured = capsys.readouterr()
    assert captured.out.splitlines() == ["a2y", "elph", "elph_pp", "p2y", "yambo"]
    assert captured.err == ""


def test_list_runlevels_flag_prints_keywords_and_exits(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["yambo-tester", "--list-runlevels"])
    monkeypatch.setattr("yambo_tester.cli.setup_logging", lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("setup_logging should not run")))

    main()

    captured = capsys.readouterr()
    assert captured.out.splitlines() == ["bse", "dft", "gf", "init", "lifetimes", "optics", "pp", "qp", "rim_cut"]
    assert captured.err == ""
