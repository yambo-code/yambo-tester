import pytest  # test framework

from yambo_tester.variants import load_variant, rewrite_input  # code under test
from yambo_tester.versioning import resolve_workflow_metadata, workflow_steps_for_version  # overlay chain


def write(tmp_path, text):  # scratch input helper
    path = tmp_path / "in"  # input file
    path.write_text(text)  # content
    return path  # path


def test_develop_hf_input(tmp_path):  # SEApprox="HF" -> HF_lXC + dyson, SEApprox dropped
    path = write(tmp_path, 'self_energy   # comment\nHFlXC_CPU= ""\nSEApprox= "HF"   # approx\nEXXRLvcs= 300 RL\n')  # main syntax
    rewrite_input(path, load_variant("develop", "6"))  # apply develop rules
    assert path.read_text() == 'HF_lXC\ndyson\nHFlXC_CPU= ""\nEXXRLvcs= 300 RL\n'  # runlevels replaced, variable removed


def test_develop_ppa_input_lowercase(tmp_path):  # other approximations -> HF_lXC + gw + dyson
    path = write(tmp_path, 'rim_cut\nself_energy\nSEApprox= "ppa"\nppa\n')  # value in lower case
    rewrite_input(path, load_variant("develop", "6"))  # apply develop rules
    assert path.read_text() == 'rim_cut\nHF_lXC\ngw\ndyson\nppa\n'  # default runlevels


def test_input_without_runlevel_untouched(tmp_path):  # inputs without self_energy stay as they are
    text = 'optics\nchi\nSEApprox= "HF"\n'  # no self_energy line
    path = write(tmp_path, text)  # scratch input
    rewrite_input(path, load_variant("develop", "6"))  # apply develop rules
    assert path.read_text() == text  # unchanged


def test_unknown_variant_and_wrong_major():  # fail early with a clear message
    assert load_variant("", "6") == {}  # no variant: no rules
    with pytest.raises(ValueError, match="Unknown Yambo variant"):  # typo in the name
        load_variant("develp", "6")
    with pytest.raises(ValueError, match="is for Yambo 6"):  # develop is a Yambo 6 dialect
        load_variant("develop", "5")


def test_variant_overlay_on_top_of_major():  # versions."6-develop" applies after versions."6"
    workflow = {
        "tarball_url": "base",  # workflow metadata
        "versions": {"6": {"tarball_url": "y6"}, "6-develop": {"tarball_url": "develop"}},  # two overlays
        "02_hf": {
            "input": "INPUTS/Y5/02_hf",  # base
            "versions": {"6": {"input": "INPUTS/Y6/02_hf"}, "6-develop": {"reference": {"REFERENCE/Y6-develop/o": []}}},  # step overlays
        },
    }
    assert resolve_workflow_metadata(workflow, "6")["tarball_url"] == "y6"  # no variant
    assert resolve_workflow_metadata(workflow, "6", "develop")["tarball_url"] == "develop"  # variant wins
    step = workflow_steps_for_version(workflow, "6", "develop")["02_hf"]  # resolved step
    assert step["input"] == "INPUTS/Y6/02_hf"  # from the major overlay
    assert step["reference"] == {"REFERENCE/Y6-develop/o": []}  # from the variant overlay
    assert "reference" not in workflow_steps_for_version(workflow, "6")["02_hf"]  # variant overlay off without --variant


def test_thread_env_always_sets_omp_threads(monkeypatch):  # MPI-only builds must not leave threaded BLAS unbounded
    from yambo_tester.runner import thread_env  # code under test
    monkeypatch.delenv("OMP_NUM_THREADS", raising=False)  # as in a plain shell
    assert thread_env({"omp": False, "thrs": 4})["OMP_NUM_THREADS"] == "1"  # MPI-only yambo: one thread per task
    assert thread_env({"omp": True, "thrs": 4})["OMP_NUM_THREADS"] == "4"  # OpenMP yambo: the requested threads
