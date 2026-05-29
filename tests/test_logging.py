import logging

from yambo_tester import cli
from yambo_tester.log import setup_logging, setup_test_logger


def test_main_and_local_loggers_stay_isolated(tmp_path):
    main_log = tmp_path / "main.log"
    run_a = tmp_path / "run-a"
    run_b = tmp_path / "run-b"

    main_logger = setup_logging(main_log, console=False, name="yambo_tester.tests.main")
    local_a = setup_test_logger(run_a)
    local_b = setup_test_logger(run_b)

    main_logger.info("setup phase")
    main_logger.info("[A/step] Starting test")
    local_a.info("A details")
    local_b.info("B details")
    main_logger.info("[A/step] Finished test")

    main_text = main_log.read_text()
    assert "setup phase" in main_text
    assert "[A/step] Starting test" in main_text
    assert "[A/step] Finished test" in main_text
    assert "A details" not in main_text
    assert "B details" not in main_text

    local_a_text = (run_a / "tester.log").read_text()
    local_b_text = (run_b / "tester.log").read_text()
    assert "A details" in local_a_text
    assert "B details" not in local_a_text
    assert "A details" not in local_b_text
    assert "B details" in local_b_text
    assert "setup phase" not in local_a_text
    assert "setup phase" not in local_b_text

    assert main_logger.propagate is False
    assert local_a.propagate is False
    assert local_b.propagate is False
    assert len(main_logger.handlers) == 1
    assert len(local_a.handlers) == 1
    assert len(local_b.handlers) == 1


def test_reconfiguring_same_test_logger_does_not_duplicate_lines(tmp_path):
    run_dir = tmp_path / "run"

    logger = setup_test_logger(run_dir)
    logger.info("first run")
    logger = setup_test_logger(run_dir)
    logger.info("second run")

    text = (run_dir / "tester.log").read_text()
    assert text.count("second run") == 1
    assert "first run" not in text
    assert logger.propagate is False
    assert len(logger.handlers) == 1


def test_cli_logs_setup_and_test_lifecycle(monkeypatch, tmp_path):
    main_log = tmp_path / "main.log"
    run_dir = tmp_path / "scratch" / "TestA" / "Case1"
    test_dir = run_dir.parent
    captured = {}

    config = {
        "config": tmp_path / "config.toml",
        "parameters": {
            "logger": str(main_log),
            "init": False,
            "verbose": False,
            "donly": False,
            "nochecksum": False,
            "label": "",
        },
        "tests": {"TestA": ["Case1"]},
    }

    def fake_load_config():
        return config

    def fake_set_cl_args(config):
        return config

    def fake_check_parameters(parameters, logger):
        logger.info("setup complete")
        return parameters

    def fake_setup_rundir(test, parameters, logger):
        run_dir.mkdir(parents=True, exist_ok=True)
        (run_dir / "tests.toml").write_text(
            'sha256 = "dummy"\n\n[step]\ninput = "input.in"\nexe = "yambo"\noutput = "output"\n',
            encoding="utf-8",
        )
        return test_dir, run_dir

    def fake_run_test(test, parameters, logger, verbose=False):
        local_logger = setup_test_logger(run_dir)
        captured["local_logger"] = local_logger
        local_logger.info("local execution details")
        return local_logger

    def fake_run_pytest(test, local_logger, verbose=False):
        local_logger.info("local validation details")
        return 0

    monkeypatch.setattr(cli, "load_config", fake_load_config)
    monkeypatch.setattr(cli, "set_cl_args", fake_set_cl_args)
    monkeypatch.setattr(cli, "check_parameters", fake_check_parameters)
    monkeypatch.setattr(cli, "setup_rundir", fake_setup_rundir)
    monkeypatch.setattr(cli, "run_test", fake_run_test)
    monkeypatch.setattr(cli, "run_pytest", fake_run_pytest)

    cli.main()

    main_logger = logging.getLogger("yambo_tester")
    for handler in main_logger.handlers:
        handler.flush()
    for handler in captured["local_logger"].handlers:
        handler.flush()

    main_text = main_log.read_text()
    local_text = (run_dir / "tester.log").read_text()

    assert "setup complete" in main_text
    assert "[TestA/Case1] Starting test" in main_text
    assert "[TestA/Case1] Finished test" in main_text
    assert "local execution details" not in main_text
    assert "local validation details" not in main_text

    assert "local execution details" in local_text
    assert "local validation details" in local_text
    assert "setup complete" not in local_text
    assert "[TestA/Case1] Starting test" not in local_text
    assert "[TestA/Case1] Finished test" not in local_text
