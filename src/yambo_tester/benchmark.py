# Copyright (c) 2025 Nicola Spallanzani 
# Riccardo Reho
# Licensed under the MIT License. See LICENSE file for details.
"""Benchmark mode: parallel strategy from tests.toml, SLURM jobs, timing collection."""

import ast  # safe formula parsing
import operator  # arithmetic for the formula evaluator
import re  # input patching and time parsing
import shlex  # quoting of the job command
import shutil  # copy of non-SAVE tarball files
import subprocess  # sbatch calls
import sys  # path of the running yambo-tester
import tarfile  # shared SAVE extraction
import tempfile  # private extraction dir
import tomllib  # packaged data and workflow metadata
import importlib.resources  # packaged data files
from pathlib import Path  # filesystem paths
import toml  # job config.toml writer (existing dependency)
from .versioning import normalize_yambo_version, resolve_workflow_metadata, resolve_yambo_version  # version helpers

_BINOPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.FloorDiv: operator.floordiv}  # allowed arithmetic
_CMPOPS = {ast.Lt: operator.lt, ast.LtE: operator.le, ast.Gt: operator.gt, ast.GtE: operator.ge,
           ast.Eq: operator.eq, ast.NotEq: operator.ne}  # allowed comparisons
_UNITS = {"d": 86400.0, "h": 3600.0, "m": 60.0, "s": 1.0}  # seconds per Yambo time unit
COLUMNS = ["Nodes", "Tasks", "Threads/Task", "Time-Profile", "Dipoles", "Xo", "X", "Self Energy", "Other"]  # result.dat header (MaX style)


def eval_formula(expr, names):
    """Evaluate a benchmark formula with numbers, names, + - * //, comparisons and if/else only."""
    def ev(node):  # recursive whitelist walker
        if isinstance(node, ast.Constant) and type(node.value) in (int, float):  # plain number (no bool/str)
            return node.value  # literal value
        if isinstance(node, ast.Name) and node.id in names:  # known variable
            return names[node.id]  # its value
        if isinstance(node, ast.BinOp) and type(node.op) in _BINOPS:  # + - * //
            return _BINOPS[type(node.op)](ev(node.left), ev(node.right))  # apply operator
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):  # negative number
            return -ev(node.operand)  # negate
        if isinstance(node, ast.Compare) and all(type(o) in _CMPOPS for o in node.ops):  # chained comparison
            values = [ev(node.left)] + [ev(c) for c in node.comparators]  # operands in order
            return all(_CMPOPS[type(o)](a, b) for o, a, b in zip(node.ops, values, values[1:]))  # a<b<c semantics
        if isinstance(node, ast.IfExp):  # x if cond else y
            return ev(node.body) if ev(node.test) else ev(node.orelse)  # lazy branch
        raise ValueError(f"Unsupported element {type(node).__name__} in benchmark formula {expr!r}")  # anything else
    try:  # syntax errors become ValueError too
        tree = ast.parse(str(expr).strip(), mode="eval")  # parse one expression
    except SyntaxError as e:  # malformed formula
        raise ValueError(f"Invalid benchmark formula {expr!r}: {e.msg}") from None  # clear message
    return ev(tree.body)  # evaluate the expression body


def load_parallel_names(major, overrides=None):
    """Return the generic block -> Yambo variable prefix map for a major version."""
    with (importlib.resources.files("yambo_tester.data") / "parallel_names.toml").open("rb") as f:  # packaged map
        names = dict(tomllib.load(f)[normalize_yambo_version(major)])  # table of this version
    names.update((overrides or {}).get(normalize_yambo_version(major), {}))  # [benchmark.names."<major>"] wins
    return names  # e.g. {"chi": "PPA", ...}


def parallel_lines(bench, ntasks, major, nodes=None):
    """Return {"<NAME>_CPU": "1 1 8", "<NAME>_ROLEs": "q g b", ...} for this ntasks and Yambo version."""
    names = load_parallel_names(major, bench.get("names"))  # generic -> versioned names
    nodes = nodes if nodes is not None else ntasks // bench.get("tasks_per_node", ntasks)  # default node count
    scope = {"ntasks": ntasks, "nodes": int(nodes), "threads": bench.get("threads", 1)}  # formula variables
    for var, formula in bench.get("vars", {}).items():  # helper vars, in order
        scope[var] = eval_formula(formula, scope)  # may use earlier vars
    lines = {}  # output variables
    for block, roles in bench.get("parallel", {}).items():  # generic block -> {role: formula}
        if block not in names:  # unknown generic name
            raise ValueError(f"Unknown benchmark parallel block '{block}' (known: {', '.join(names)})")  # clear error
        counts = [eval_formula(f, scope) for f in roles.values()]  # CPUs per role
        if any(not isinstance(c, int) or c < 1 for c in counts):  # must be positive integers
            raise ValueError(f"Benchmark block '{block}' gives non positive-integer CPUs {counts}")  # clear error
        product = 1  # product of counts
        for c in counts:  # multiply
            product *= c  # running product
        if product != ntasks:  # Yambo needs product == MPI tasks
            raise ValueError(f"Benchmark block '{block}': CPUs {counts} multiply to {product}, not ntasks={ntasks}")  # clear error
        lines[f"{names[block]}_CPU"] = " ".join(str(c) for c in counts)  # e.g. "1 1 8"
        lines[f"{names[block]}_ROLEs"] = " ".join(roles)  # same order as counts
    return lines  # var -> string value


def patch_input(path, lines):
    """Replace existing NAME= lines of a Yambo input, append missing ones, keep the rest."""
    text = Path(path).read_text().splitlines()  # input lines
    for var, value in lines.items():  # each parallel variable
        new = f'{var}= "{value}"'  # Yambo string syntax
        pattern = re.compile(rf"^\s*{re.escape(var)}\s*=", re.IGNORECASE)  # existing assignment (Yambo is case-insensitive)
        hits = [i for i, line in enumerate(text) if pattern.match(line)]  # matching line indices
        for i in hits:  # replace every occurrence
            text[i] = new  # overwrite
        if not hits:  # variable missing
            text.append(new)  # append at the end
    Path(path).write_text("\n".join(text) + "\n")  # save


def write_job(job_dir, cluster, nodes, ntasks_per_node, threads, cmd):
    """Write job.sh from the packaged SLURM template and return its path."""
    default = importlib.resources.files("yambo_tester.data") / "slurm_job.sh"  # packaged neutral template
    template = Path(cluster["template"]).expanduser().read_text() if cluster.get("template") else default.read_text()  # site template wins
    modules = cluster.get("modules", [])  # modules to load
    modules = [modules] if isinstance(modules, str) and modules else list(modules or [])  # accept str or list
    script = template.format(nodes=nodes, ntasks_per_node=ntasks_per_node, threads=threads,  # resources
                             partition=cluster.get("partition", ""), account=cluster.get("account", ""), qos=cluster.get("qos", ""),  # site
                             time=cluster.get("time", "01:00:00"),  # walltime
                             modules="\n".join([f"module load {m}" for m in modules] + list(cluster.get("setup", []))),  # modules, then raw setup lines
                             cmd=cmd)  # command
    script = "\n".join(l for l in script.splitlines() if not (l.startswith("#SBATCH") and l.endswith("="))) + "\n"  # drop empty #SBATCH options
    job = Path(job_dir) / "job.sh"  # job file
    job.write_text(script)  # save
    return job  # path to job.sh


def submit(jobs, dry_run=False):
    """Submit job.sh files with sbatch from their own directory; dry_run only prints them."""
    for job in jobs:  # each job file
        if dry_run:  # no SLURM
            print(f"### {job}\n{job.read_text()}")  # show path and script
        else:  # real submission
            subprocess.run(["sbatch", job.name], cwd=job.parent, check=True)  # sbatch in the job dir


def prepare_jobs(config):
    """Write one job dir (config.toml + job.sh) per workflow with [benchmark] and node count."""
    par, cluster, jobs = config["parameters"], config.get("cluster", {}), []  # inputs and output list
    major = resolve_yambo_version(par.get("yambo_version"))  # overlay version (default 6)
    exe = shlex.quote(str(Path(sys.argv[0]).resolve()))  # this yambo-tester
    for name, types in config["tests"].items():  # selected workflows
        for wtype in types:  # workflow types
            with open(Path(str(par["tests_dir"])) / name / wtype / "tests.toml", "rb") as f:  # source tests.toml
                bench = resolve_workflow_metadata(tomllib.load(f), major, par.get("yambo_variant", "")).get("benchmark")  # [benchmark] table
            if not bench:  # not a benchmark workflow
                continue  # skip
            shape = {k: cluster.get(k) or bench.get(k) for k in ("nodes", "tasks_per_node", "threads")}  # node shape: [cluster] (machine) over [benchmark]
            missing = [k for k, v in shape.items() if not v]  # shape keys nobody set
            if missing:  # cannot build jobs
                raise ValueError(f"{name}/{wtype}: set {', '.join(missing)} in [cluster] of config.toml")  # clear error
            for nodes in shape["nodes"]:  # strong-scaling points
                job_dir = Path(par["scratch_dir"]).resolve() / "benchmark" / f"{name}_{wtype}" / f"nodes_{nodes:03d}"  # job dir
                job_dir.mkdir(parents=True, exist_ok=True)  # create
                keep = {k: par[k] for k in ("yambo_version", "yambo_variant", "tollerance", "runlevels") if par.get(k)}  # passthrough options
                keep.update({k: str(Path(str(par[k])).resolve()) for k in ("tests_dir", "cache_dir", "yambo_bin") if par.get(k)})  # absolute dirs
                keep["scratch_dir"] = str(job_dir)  # runs land in the job dir
                (job_dir / "config.toml").write_text(toml.dumps(  # job-local config
                    {"parameters": keep, "executables": config.get("executables", {}), "tests": {name: [wtype]}}))  # one workflow
                ntasks = nodes * shape["tasks_per_node"]  # total MPI tasks
                cmd = (f"cd {shlex.quote(str(job_dir))}\n{exe} --nodes {nodes} --np {ntasks} --thrs {shape['threads']}"  # re-invoke tester
                       f" --mpi {cluster.get('mpi') or par.get('mpi_launcher') or 'mpirun'} -l bench_n{nodes}")  # site launcher, else the usual mpi_launcher
                jobs.append(write_job(job_dir, cluster, nodes, shape["tasks_per_node"], shape["threads"], cmd))  # job.sh
    return jobs  # job files


def link_save(tar_file, cache_dir, dest):
    """Extract tar_file once under cache_dir/extracted, symlink its SAVE dirs into dest, copy the rest."""
    shared = Path(cache_dir).resolve() / "extracted" / Path(tar_file).name.split(".tar")[0]  # shared copy, one per tarball
    if not shared.exists():  # first job using this tarball
        shared.parent.mkdir(parents=True, exist_ok=True)  # cache/extracted
        tmp = Path(tempfile.mkdtemp(dir=shared.parent))  # private dir: concurrent jobs do not collide
        with tarfile.open(tar_file) as tar:  # open tarball
            tar.extractall(path=tmp, filter="data")  # extract privately, safe members only
        try:  # publish atomically
            tmp.rename(shared)  # becomes the shared copy
        except OSError:  # another job published first
            shutil.rmtree(tmp)  # drop our copy
        else:  # we published it
            for p in sorted(shared.rglob("SAVE/**/*"), reverse=True) + list(shared.rglob("SAVE")):  # SAVE content, then SAVE dirs
                p.chmod(0o555 if p.is_dir() else 0o444)  # read-only: a write into shared SAVE fails loudly (use -J/-C)
    for save in shared.rglob("SAVE"):  # every SAVE dir in the tarball
        link = Path(dest) / save.relative_to(shared)  # same place in the run tree
        link.parent.mkdir(parents=True, exist_ok=True)  # parent dir
        if save.is_dir() and not link.exists():  # not linked yet
            link.symlink_to(save, target_is_directory=True)  # symlink, no copy
    shutil.copytree(shared, dest, ignore=shutil.ignore_patterns("SAVE"), dirs_exist_ok=True)  # small extra files are copied


def time_in_seconds(value):
    """Convert Yambo times such as '0.0004s', '22m-10s', '01h-41m' to seconds."""
    parts = re.findall(r"(\d+(?:\.\d+)?)\s*([dhms])", value)  # number+unit pairs
    if not parts:  # bare number
        return float(value)  # already seconds
    return sum(float(n) * _UNITS[u] for n, u in parts)  # total seconds


def load_timer_labels():
    """Return the packaged report-label table (resources and result.dat columns, Y5+Y6)."""
    with (importlib.resources.files("yambo_tester.data") / "benchmark_timers.toml").open("rb") as f:  # packaged table
        return tomllib.load(f)  # {"resources": {...}, "columns": {...}}


def parse_report(r_file):
    """Return resources and Clock timers (seconds) from a Yambo r- report, plus MaX summary keys."""
    table = load_timer_labels()  # labels for Y5 and Y6
    labels = {label: key for key, names in table["resources"].items() for label in names}  # header label -> key
    res, timing, in_clock = {}, {}, False  # outputs and section flag
    for line in Path(r_file).read_text(errors="replace").splitlines():  # report lines
        if not line.strip():  # blank line closes the Clock section
            in_clock = False  # leave section
        elif in_clock and ":" in line:  # "timer :  12.3s P1 ..."
            key, rest = line.rsplit(" : ", 1) if " : " in line else line.split(":", 1)  # timer name and values
            timing[key.strip()] = time_in_seconds(rest.split()[0])  # MAX column
        elif "Clock:" in line:  # Clock section header
            in_clock = True  # enter section
        elif "[Time-Profile]" in line:  # total wall time
            timing["Time-Profile"] = time_in_seconds(line.split(":", 1)[1])  # seconds
        else:  # header resources
            for label, key in labels.items():  # known labels
                if line.strip().startswith(label) and ":" in line:  # e.g. " MPI Cores :  16"
                    res[key] = int(line.split(":", 1)[1])  # integer value
    summary, missing = {"Time-Profile": timing.get("Time-Profile", 0.0)}, []  # MaX columns, columns without timers
    for column, names in table["columns"].items():  # result.dat column -> timer labels
        found = [timing[n] for n in names if n in timing]  # timers present in this report
        summary[column] = sum(found)  # summed MAX times
        if not found:  # no known label in this report
            missing.append(column)  # reported by collect
    summary["Other"] = summary["Time-Profile"] - sum(v for k, v in summary.items() if k != "Time-Profile")  # remainder
    return {"resources": res, "timing": timing, "summary": summary, "missing": missing}  # parsed report


def collect(root):
    """Parse every r- report under root, write root/result.dat and print the scaling table."""
    rows = []  # (report name, nodes, tasks, threads, summary)
    for r_file in sorted(Path(root).rglob("r-*")):  # all reports
        if "REFERENCE" in r_file.parts:  # copied reference reports, not this run
            continue  # skip
        rep = parse_report(r_file)  # parse
        if "Time-Profile" not in rep["timing"]:  # incomplete run
            continue  # skip
        if rep["missing"]:  # label renamed/new in this Yambo version
            print(f"WARNING {r_file}: no timer for {', '.join(rep['missing'])}; add its label to data/benchmark_timers.toml")  # never silent 0
        m = re.search(r"nodes_(\d+)", str(r_file))  # node count from job dir
        nodes = int(m.group(1)) if m else rep["resources"].get("nodes", 0)  # fallback to report
        rows.append((r_file.name, nodes, rep["resources"].get("tasks", 0), rep["resources"].get("threads", 0), rep["summary"]))  # row
    rows.sort(key=lambda r: (r[0], r[1]))  # by report then nodes
    with open(Path(root) / "result.dat", "w") as f:  # MaX-style table
        f.write(";".join(COLUMNS) + "\n")  # header
        for _, n, t, th, s in rows:  # rows
            f.write(";".join([str(n), str(t), str(th)] + [f"{s[c]:.2f}" for c in COLUMNS[3:]]) + "\n")  # values
    base = {}  # report name -> (nodes, time) of smallest run
    print(f"{'report':<45} {'nodes':>5} {'time[s]':>10} {'speedup':>8} {'eff':>6}")  # table header
    for name, n, _, _, s in rows:  # rows
        b_nodes, b_time = base.setdefault(name, (n, s["Time-Profile"]))  # baseline per report
        speedup = b_time / s["Time-Profile"] if s["Time-Profile"] else 0.0  # strong-scaling speedup
        eff = speedup * b_nodes / n if n else 0.0  # parallel efficiency
        print(f"{name:<45} {n:>5} {s['Time-Profile']:>10.1f} {speedup:>8.2f} {eff:>6.2f}")  # table row
    return rows  # for tests
