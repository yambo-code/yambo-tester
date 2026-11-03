import tarfile  # tarball fixture
from pathlib import Path  # fixture paths

import pytest  # test framework

from yambo_tester import benchmark  # module under test
from yambo_tester.benchmark import eval_formula, parallel_lines, parse_report, patch_input, write_job  # helpers

FIXTURE = Path(__file__).parent / "data" / "r-grco_small_ppa_y5_trimmed"  # trimmed MaX grco-small-ppa report (LUMI-C, 2 nodes)
SXP = "16 if ntasks>320 else 8 if ntasks>160 else 4 if ntasks>80 else 2 if ntasks>40 else 1"  # MaX JUBE rule
BENCH = {  # tests.toml [benchmark] example
    "nodes": [1, 2], "tasks_per_node": 8, "threads": 16,  # scaling points
    "vars": {"sxp": SXP, "half": "sxp * 2 // 2"},  # helper vars, second uses the first
    "parallel": {  # generic block -> role -> formula
        "dip": {"k": "1", "c": "ntasks", "v": "1"},  # dipoles
        "chi": {"q": "1", "g": "1", "k": "1", "c": "ntasks", "v": "1"},  # response
        "fock": {"q": "half", "b": "ntasks // sxp"},  # exchange
        "gw": {"q": "1", "qp": "1", "b": "ntasks"},  # correlation
    },
}


def test_eval_formula_arithmetic_and_ifexp():
    assert eval_formula("ntasks // 4 + 2 * nodes - 1", {"ntasks": 16, "nodes": 2}) == 7  # arithmetic
    assert eval_formula(SXP, {"ntasks": 96}) == 4  # chained if/else
    assert eval_formula("1 < ntasks <= 8", {"ntasks": 8}) is True  # chained comparison
    assert eval_formula(3, {}) == 3  # TOML integer formula


@pytest.mark.parametrize("expr", ["__import__('os')", "ntasks.real", "abs(ntasks)", "ntasks / 2",  # call, attribute, call, true division
                                  "unknown", "'a'", "[1]", "ntasks ** 2", "lambda: 1", "1 +"])  # name, str, list, power, lambda, syntax
def test_eval_formula_rejects_unsafe_or_unknown(expr):
    with pytest.raises(ValueError):  # everything outside the whitelist
        eval_formula(expr, {"ntasks": 8})  # evaluate


def test_parallel_lines_y5_names():
    lines = parallel_lines(BENCH, 16, "5")  # 2 nodes x 8 tasks
    assert lines["X_and_IO_CPU"] == "1 1 1 16 1" and lines["X_and_IO_ROLEs"] == "q g k c v"  # chi -> X_and_IO
    assert lines["SE_CPU"] == "1 1 16" and lines["SE_ROLEs"] == "q qp b"  # gw -> SE
    assert lines["SX_CPU"] == "1 16" and lines["DIP_CPU"] == "1 16 1"  # fock -> SX, dip -> DIP


def test_parallel_lines_y6_names_and_override():
    lines = parallel_lines(BENCH, 64, "6.0.1")  # 8 nodes, full version string
    assert lines["PPA_CPU"] == "1 1 1 64 1" and lines["GW_CPU"] == "1 1 64"  # chi -> PPA, gw -> GW
    assert lines["HFlXC_CPU"] == "2 32" and lines["HFlXC_ROLEs"] == "q b"  # fock -> HFlXC, sxp=2
    bench = dict(BENCH, names={"6": {"chi": "EM1D"}})  # per-version override
    assert "EM1D_CPU" in parallel_lines(bench, 64, "6") and "EM1D_CPU" not in parallel_lines(bench, 64, "5")  # only Y6


def test_parallel_lines_product_must_match_ntasks():
    bad = dict(BENCH, parallel={"gw": {"q": "2", "b": "ntasks"}})  # product 2*ntasks
    with pytest.raises(ValueError, match="multiply"):  # clear error
        parallel_lines(bad, 8, "5")  # evaluate
    with pytest.raises(ValueError, match="Unknown"):  # unknown generic block
        parallel_lines(dict(BENCH, parallel={"bse": {"k": "ntasks"}}), 8, "5")  # evaluate


def test_patch_input_replaces_and_appends(tmp_path):
    inp = tmp_path / "01_gw"  # yambo input
    inp.write_text('gw0\nse_cpu= "1 1 1"   # old\nSE_ROLEs= ""\nBndsRnXp\n  1 | 100 |\n%\n')  # existing lines
    patch_input(inp, {"SE_CPU": "1 1 8", "SE_ROLEs": "q qp b", "DIP_CPU": "1 8 1"})  # patch
    text = inp.read_text().splitlines()  # result
    assert text[1] == 'SE_CPU= "1 1 8"' and text[2] == 'SE_ROLEs= "q qp b"'  # replaced in place
    assert text[3:6] == ["BndsRnXp", "  1 | 100 |", "%"] and text[-1] == 'DIP_CPU= "1 8 1"'  # rest kept, missing appended


def test_parse_report_on_max_fixture():
    rep = parse_report(FIXTURE)  # trimmed Y5.4 report
    assert rep["resources"] == {"tasks": 16, "threads": 16, "nodes": 2}  # header
    s = rep["summary"]  # MaX columns
    assert s["Time-Profile"] == 6060.0 and s["Xo"] == 5100.0 and s["X"] == pytest.approx(4.0023)  # 01h-41m, 01h-25m
    assert s["Self Energy"] == pytest.approx(3.2498 + 926.0) and s["Dipoles"] == pytest.approx(16.926)  # HF + GW(ppa)
    assert s["Other"] == pytest.approx(9.8219)  # matches MaX result.dat (2 nodes row)
    assert rep["timing"]["Xo (REDUX)"] == 1330.0 and rep["timing"]["io_QP_and_GF"] == pytest.approx(0.0195)  # 22m-10s, no [MAX]


def test_collect_writes_result_dat(tmp_path, capsys):
    for n in (1, 2):  # two job dirs, same report
        d = tmp_path / f"nodes_{n:03d}" / "run"  # job layout
        d.mkdir(parents=True)  # create
        d.joinpath(FIXTURE.name).write_text(FIXTURE.read_text())  # copy report
        ref = tmp_path / f"nodes_{n:03d}" / "REFERENCE" / "Y5"  # copied reference tree
        ref.mkdir(parents=True)  # create
        ref.joinpath(FIXTURE.name).write_text(FIXTURE.read_text())  # must be ignored
    benchmark.collect(tmp_path)  # build table
    lines = (tmp_path / "result.dat").read_text().splitlines()  # result.dat
    assert lines[0] == "Nodes;Tasks;Threads/Task;Time-Profile;Dipoles;Xo;X;Self Energy;Other"  # header
    assert lines[2].startswith("2;16;16;6060.00;16.93;5100.00;4.00;929.25;9.82")  # MaX-format row
    assert "0.50" in capsys.readouterr().out  # efficiency of identical times on 2 nodes


def test_write_job_and_dry_run_submit(tmp_path, capsys, monkeypatch):
    cluster = {"partition": "batch", "qos": "normal", "account": "", "time": "02:00:00", "modules": ["yambo/5.3"], "setup": ["source env.sh"]}  # empty account
    job = write_job(tmp_path, cluster, 4, 8, 16, "yambo-tester --nodes 4")  # render
    text = job.read_text()  # script
    for expected in ["#SBATCH --nodes=4", "#SBATCH --ntasks-per-node=8", "#SBATCH --cpus-per-task=16",  # resources
                     "#SBATCH --partition=batch", "#SBATCH --qos=normal", "#SBATCH --time=02:00:00", "module load yambo/5.3", "source env.sh",  # site
                     "export OMP_NUM_THREADS=16", "yambo-tester --nodes 4"]:  # env and command
        assert expected in text  # present
    assert "--account" not in text  # empty option dropped
    monkeypatch.setattr(benchmark.subprocess, "run", lambda *a, **k: pytest.fail("sbatch called"))  # no SLURM
    benchmark.submit([job], dry_run=True)  # print only
    assert str(job) in capsys.readouterr().out  # job path shown


def test_prepare_jobs_writes_job_dirs(tmp_path):
    wf = tmp_path / "tests" / "GrCo" / "GW_bench"  # fake workflow
    wf.mkdir(parents=True)  # create
    wf.joinpath("tests.toml").write_text('[benchmark]\nnodes = [1, 2]\ntasks_per_node = 8\nthreads = 16\n')  # metadata
    config = {"parameters": {"tests_dir": str(tmp_path / "tests"), "scratch_dir": str(tmp_path / "scratch"), "yambo_version": "5"},  # params
              "cluster": {"mpi": "srun"}, "executables": {"yambo": "yambo"}, "tests": {"GrCo": ["GW_bench"]}}  # selection
    jobs = benchmark.prepare_jobs(config)  # write jobs
    assert [j.parent.name for j in jobs] == ["nodes_001", "nodes_002"]  # one per node count
    assert "--nodes 2 --np 16 --thrs 16 --mpi srun" in jobs[1].read_text()  # self-invocation
    assert 'GrCo = [ "GW_bench",]' in jobs[1].parent.joinpath("config.toml").read_text()  # selection restricted


def test_prepare_jobs_cluster_shape_wins_and_is_required(tmp_path):
    wf = tmp_path / "tests" / "GrCo" / "GW_bench"  # fake workflow
    wf.mkdir(parents=True)  # create
    wf.joinpath("tests.toml").write_text('[benchmark]\nnodes = [1, 2]\n')  # no machine shape in the workflow
    par = {"tests_dir": str(tmp_path / "tests"), "scratch_dir": str(tmp_path / "s"), "mpi_launcher": "mpirun"}  # params
    config = {"parameters": par, "cluster": {}, "executables": {}, "tests": {"GrCo": ["GW_bench"]}}  # no shape anywhere
    with pytest.raises(ValueError, match="tasks_per_node, threads"):  # clear message
        benchmark.prepare_jobs(config)  # refused
    config["cluster"] = {"tasks_per_node": 4, "threads": 32, "nodes": [3]}  # site shape and node override
    jobs = benchmark.prepare_jobs(config)  # write jobs
    assert [j.parent.name for j in jobs] == ["nodes_003"]  # cluster nodes win
    assert "--nodes 3 --np 12 --thrs 32 --mpi mpirun" in jobs[0].read_text()  # site shape, mpi_launcher fallback


def test_write_job_uses_site_template(tmp_path):
    tpl = tmp_path / "site.sh"  # site template
    tpl.write_text("#!/bin/bash\n#SITE {nodes}x{ntasks_per_node}\n{cmd}\n")  # minimal template
    job = write_job(tmp_path, {"template": str(tpl)}, 2, 8, 16, "run")  # render
    assert job.read_text() == "#!/bin/bash\n#SITE 2x8\nrun\n"  # site template used


def test_parse_report_on_y6_fixture():
    rep = parse_report(FIXTURE.parent / "r-hbn2d_ppa_y6_trimmed")  # trimmed Y6 report (hBN_2D 04_ppa)
    assert rep["resources"] == {"tasks": 2, "nodes": 1} and rep["missing"] == []  # Y6 header labels, all columns found
    s = rep["summary"]  # MaX columns
    assert s["X"] == pytest.approx(0.0030) and s["Xo"] == pytest.approx(1.7983)  # PPA matrix, Xo
    assert s["Self Energy"] == pytest.approx(0.1595 + 3.0702)  # Fock + Plasmon-Pole


def test_collect_warns_on_unknown_timer(tmp_path, capsys):
    d = tmp_path / "nodes_001"  # job dir
    d.mkdir()  # create
    d.joinpath("r-x").write_text("[Time-Profile]: 10s\n\n Clock: global\n Dipoles : 1.0s P1 [MAX]\n\n")  # no Xo/X/SE timers
    benchmark.collect(tmp_path)  # build table
    out = capsys.readouterr().out  # printed text
    assert "WARNING" in out and "Xo, X, Self Energy" in out  # missing columns named


def test_link_save_extracts_once_and_symlinks(tmp_path):
    src = tmp_path / "src" / "GW_bench"  # tarball content
    (src / "SAVE").mkdir(parents=True)  # SAVE dir
    (src / "SAVE" / "ns.db1").write_text("db")  # database
    (src / "extra.txt").write_text("x")  # non-SAVE file
    tar_file = tmp_path / "GrCo_GW_bench.tar.gz"  # tarball path
    with tarfile.open(tar_file, "w:gz") as tar:  # build tarball
        tar.add(src, arcname="GW_bench")  # Feature/SAVE layout
    for job in ("job1", "job2"):  # two jobs share one extraction
        benchmark.link_save(tar_file, tmp_path / "cache", tmp_path / job)  # link
        assert (tmp_path / job / "GW_bench" / "SAVE").is_symlink()  # SAVE is a symlink
        assert (tmp_path / job / "GW_bench" / "extra.txt").read_text() == "x"  # rest copied
    assert (tmp_path / "job1" / "GW_bench" / "SAVE").resolve() == (tmp_path / "cache" / "extracted" / "GrCo_GW_bench" / "GW_bench" / "SAVE").resolve()  # shared target
    assert len(list((tmp_path / "cache" / "extracted").iterdir())) == 1  # extracted once, no temp left
    shared_save = tmp_path / "cache" / "extracted" / "GrCo_GW_bench" / "GW_bench" / "SAVE"  # shared SAVE
    with pytest.raises(PermissionError):  # read-only guard
        (shared_save / "ndb.gops").write_text("x")  # a stray write into SAVE fails
    for p in [shared_save, *shared_save.iterdir()]:  # restore write bits
        p.chmod(0o755)  # so pytest can clean tmp_path
