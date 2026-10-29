"""Invariants every workflow in .github/workflows/ keeps, so a careless edit fails CI instead of weakening security.

Each check is a function that returns a list of violations for one parsed workflow (or for the labeler and policy
files). The tests at the top run them over the repository's files; the tests at the bottom feed each one an inline
YAML fixture that breaks it. A new workflow passes as is when it asks for nothing beyond `contents: read`; a job that
needs more gets a reviewed row in `JOB_PERMISSIONS`.
"""

import fnmatch
import re
import shlex
from pathlib import Path

import pytest
from ruamel.yaml import YAML

ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = ROOT / ".github" / "workflows"
LABELER = ROOT / ".github" / "labeler.yml"
POLICY = ROOT / ".github" / "policies" / "risk-tiers.policy"

# Every workflow's top-level token: jobs that need more declare it themselves.
TOP_LEVEL_PERMISSIONS = {"contents": "read"}

# Reviewed job-level token scopes, by (workflow file, job id). A job that declares `permissions:` must match its row
# exactly; a job without a row must not declare any (it inherits the read-only top level).
JOB_PERMISSIONS: dict[tuple[str, str], dict[str, str]] = {
    # Push the suggestions commit to the PR branch; react to the command and post the report comment.
    ("auto-review.yml", "apply"): {"contents": "write", "pull-requests": "write"},
    # Download the Nightly compliance run's report artifact; open, update or close the nightly compliance issue.
    ("auto-issues.yml", "compliance-issue"): {"actions": "read", "contents": "read", "issues": "write"},
    # claude-code-action's documented minimum: push claude/* branches, open and comment on PRs and issues, and mint
    # its GitHub App token via OIDC.
    ("claude.yml", "claude"): {
        "contents": "write",
        "pull-requests": "write",
        "issues": "write",
        "id-token": "write",
    },
    # The checker edits the manifest; create-pull-request pushes the update branch and opens the PR.
    ("external-data-checker.yml", "flatpak-external-data-checker"): {
        "contents": "write",
        "pull-requests": "write",
    },
    # Comment the validation report on the submission issue and set its labels.
    ("game-submission-check.yml", "check"): {"contents": "read", "issues": "write"},
    # Stage B: comment on an invalid submission. The pull request job opens the PR with the bot App's token.
    ("game-submission-approve.yml", "add"): {"contents": "read", "issues": "write"},
    # Link the pull request, opened with the bot App's token, on the submission issue.
    ("game-submission-approve.yml", "pull-request"): {"contents": "read", "issues": "write"},
    # actions/labeler reads .github/labeler.yml and labels the PR.
    ("labeler.yml", "label"): {"contents": "read", "pull-requests": "write"},
    # List Dependabot alerts; open or update the broken-links `data` issue; download last week's link-check state
    # artifact.
    ("nightly-compliance.yml", "compliance"): {
        "actions": "read",
        "contents": "read",
        "issues": "write",
        "vulnerability-alerts": "read",
    },
    # actions/deploy-pages: deploy the artifact, authenticated through OIDC.
    ("pages.yml", "deploy"): {"pages": "write", "id-token": "write"},
    # Check out scripts/ and list closed PRs.
    ("pr-metrics.yml", "acceptance"): {"contents": "read", "pull-requests": "read"},
    # Check out scripts/ and the popularity.json history, list popularity.yml runs and merged data/popularity PRs.
    ("pr-metrics.yml", "popularity"): {"contents": "read", "actions": "read", "pull-requests": "read"},
    # Create the GitHub Release and upload the bundles.
    ("release.yml", "publish"): {"contents": "write"},
}

# docker:// actions referenced by tag instead of a digest, with the reason. Prefer pinning by digest
# (`docker://image@sha256:<64 hex>`); external-data-checker.yml does.
DOCKER_TAG_ALLOWLIST: dict[str, str] = {}

# Job `container:` images referenced by tag instead of a digest, with the reason. Pin by digest
# (`image@sha256:<64 hex>`, with a `# <tag> as of <date>` comment); CONTRIBUTING.md says how to bump one.
CONTAINER_TAG_ALLOWLIST: dict[str, str] = {}

# Jobs reviewed to use the `bot` environment, by (workflow file, job id). It holds the self-created GitHub App's key
# (BOT_APP_ID, BOT_APP_PRIVATE_KEY; #269), whose tokens can push workflow changes and open pull requests that start CI.
# Only main may use the environment. A job that uses it starts on a fresh runner from artifacts and our own scripts:
# it may run no docker:// image and no model step, and it never processes issue text or fetched pages itself (#79).
BOT_ENVIRONMENT_JOBS: dict[tuple[str, str], str] = {
    # Moves the flatpak-external-data-checker pin and opens the ci/checker-pin pull request.
    ("nightly-compliance.yml", "checker-pin"): "check_checker_digest.py --bump, then create-pull-request",
    # Applies the link check's changes.json to the newest main and opens data/link-status.
    (
        "nightly-compliance.yml",
        "link-status",
    ): "apply_link_status.py on the compliance artifact, then create-pull-request",
    # Puts the compute job's shelves and the report file in place, guards them and opens data/popularity.
    ("popularity.yml", "pull-request"): "report_guard.py on the compute and report artifacts, then create-pull-request",
    # Applies the add job's catalog patch and opens data/add-<slug>.
    ("game-submission-approve.yml", "pull-request"): "git apply of the add job's patch, then create-pull-request",
}

# Jobs reviewed to merge pull requests (`gh pr merge`), by (workflow file, job id). Only the weekly popularity numbers
# merge themselves once the required checks pass (#79); catalog and link-status changes stay human-merged.
AUTO_MERGE_JOBS: dict[tuple[str, str], str] = {
    ("popularity.yml", "pull-request"): "gh pr merge --auto --merge on the data/popularity pull request",
}

# The labels documented in #18, which the owner created by hand; actions/labeler cannot create them.
LABELS = frozenset(
    {
        "game-submission",
        "validated",
        "needs-changes",
        "approved",
        "data",
        "automated",
        "ai-fix-requested",
        "type::bug",
        "type::feature",
        "type::task",
        "type::chore",
        "priority::critical",
        "priority::high",
        "priority::medium",
        "priority::low",
        "app",
        "flatpak",
        "ci",
        "documentation",
    }
)
# The path labels #18 says .github/labeler.yml applies; the two must match.
PATH_LABELS = frozenset({"app", "data", "flatpak", "ci", "documentation"})

# Labeler globs whose sample path no risk-tier rule names, so the classifier gives it the default (medium).
LABEL_GLOBS_WITHOUT_TIER_RULE = {
    "data/ui/**": "Blueprint UI files are app code; the default medium is their tier, as for dailies/*",
    "data/v1/**": "covered file by file: data/v1/*.json medium, data/v1/schema/* high, data/v1/README.md low (*.md)",
    "data/*.desktop.in": "the desktop entry takes the default medium; desktop-file-validate runs in the Flatpak gate",
}
# Risk-tier globs whose sample path no label names.
TIER_GLOBS_WITHOUT_LABEL: dict[str, str] = {}

SHA_PIN = re.compile(r"^[\w.-]+/[\w./-]+@[0-9a-f]{40}$")
# The comment names the tag Dependabot pins to. flatpak/flatpak-github-actions tags as vX.Y (v6.8), so the patch
# component is optional: the comment must name a real tag.
VERSION_COMMENT = re.compile(r"^#\s*v\d+\.\d+(\.\d+)?(\s|$)")
DOCKER_DIGEST = re.compile(r"@sha256:[0-9a-f]{64}$")
USES_LINE = re.compile(r"^\s*(?:-\s+)?uses:\s*(?P<ref>[^\s#]+)\s*(?P<comment>#.*)?$")
EVENT_EXPRESSION = re.compile(r"\$\{\{[^}]*\bgithub\.event(?!_)\b")
# Webhook payloads give author_association on issue, comment and review objects, never on `sender`.
SENDER_ASSOCIATION = re.compile(r"\bgithub\.event\.sender\.author_association\b")


def load_yaml(text: str) -> dict:
    # YAML 1.2: the `on:` key stays the string "on" (PyYAML's YAML 1.1 would read it as True).
    return YAML(typ="safe", pure=True).load(text)


def workflow_files() -> list[Path]:
    return sorted([*WORKFLOWS.glob("*.yml"), *WORKFLOWS.glob("*.yaml")])


def jobs_of(workflow: dict) -> dict[str, dict]:
    return workflow.get("jobs") or {}


def steps_of(workflow: dict) -> list[tuple[str, dict]]:
    return [(job_id, step) for job_id, job in jobs_of(workflow).items() for step in job.get("steps") or []]


def container_images_of(workflow: dict) -> list[tuple[str, str]]:
    """(job id, image) for every job that runs in a container; `container:` is an image string or a mapping."""
    images = []
    for job_id, job in jobs_of(workflow).items():
        container = job.get("container")
        if container is not None:
            images.append((job_id, str(container.get("image") if isinstance(container, dict) else container)))
    return images


def triggers_of(workflow: dict) -> set[str]:
    on = workflow.get("on")
    if isinstance(on, str):
        return {on}
    return set(on or ())


# --- checks -----------------------------------------------------------------------------------------------------------


def top_level_permission_violations(name: str, workflow: dict) -> list[str]:
    permissions = workflow.get("permissions")
    if permissions != TOP_LEVEL_PERMISSIONS:
        return [f"{name}: top-level permissions are {permissions!r}, expected {TOP_LEVEL_PERMISSIONS!r}"]
    return []


def job_permission_violations(
    name: str, workflow: dict, reviewed: dict[tuple[str, str], dict[str, str]] = JOB_PERMISSIONS
) -> list[str]:
    violations = []
    for job_id, job in jobs_of(workflow).items():
        expected = reviewed.get((name, job_id))
        if "permissions" not in job:
            if expected is not None:
                violations.append(f"{name}: job {job_id} declares no permissions but has a reviewed row {expected!r}")
        elif expected is None:
            violations.append(f"{name}: job {job_id} declares unreviewed permissions {job['permissions']!r}")
        elif job["permissions"] != expected:
            violations.append(f"{name}: job {job_id} permissions are {job['permissions']!r}, reviewed {expected!r}")
    return violations


def timeout_violations(name: str, workflow: dict) -> list[str]:
    return [
        f"{name}: job {job_id} has no timeout-minutes"
        for job_id, job in jobs_of(workflow).items()
        if "timeout-minutes" not in job
    ]


def uses_violations(
    name: str, workflow: dict, text: str, docker_allowlist: dict[str, str] = DOCKER_TAG_ALLOWLIST
) -> list[str]:
    violations = []
    lines = [m for m in map(USES_LINE.match, text.splitlines()) if m]
    parsed = {step["uses"] for _, step in steps_of(workflow) if "uses" in step}
    parsed |= {job["uses"] for job in jobs_of(workflow).values() if "uses" in job}
    found = {m["ref"].strip("'\"") for m in lines}
    # Every reference has to sit on its own `uses: <ref>  # comment` line, where the comment can be read.
    violations += [f"{name}: `uses: {ref}` is not on a plain `uses:` line" for ref in sorted(parsed - found)]
    for m in lines:
        ref, comment = m["ref"].strip("'\""), m["comment"] or ""
        if ref.startswith("./"):
            continue
        if ref.startswith("docker://"):
            if not DOCKER_DIGEST.search(ref) and ref.removeprefix("docker://") not in docker_allowlist:
                violations.append(f"{name}: {ref} is neither pinned by digest nor in DOCKER_TAG_ALLOWLIST")
        elif not SHA_PIN.match(ref):
            violations.append(f"{name}: {ref} is not pinned to a 40-hex commit SHA")
        elif not VERSION_COMMENT.match(comment):
            violations.append(f"{name}: {ref} has no `# vX.Y.Z` version comment")
    return violations


def container_violations(name: str, workflow: dict, allowlist: dict[str, str] = CONTAINER_TAG_ALLOWLIST) -> list[str]:
    return [
        f"{name}: job {job_id} container image {image} is neither pinned by digest nor in CONTAINER_TAG_ALLOWLIST"
        for job_id, image in container_images_of(workflow)
        if not DOCKER_DIGEST.search(image) and image not in allowlist
    ]


def event_in_run_violations(name: str, workflow: dict) -> list[str]:
    return [
        f"{name}: job {job_id} interpolates github.event into a run: script; pass it through env:"
        for job_id, step in steps_of(workflow)
        if EVENT_EXPRESSION.search(str(step.get("run", "")))
    ]


def strings_in(value: object) -> list[str]:
    """Every string in a parsed YAML document, keys included."""
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        return [s for key, item in value.items() for s in (*strings_in(key), *strings_in(item))]
    if isinstance(value, list):
        return [s for item in value for s in strings_in(item)]
    return []


def sender_association_violations(name: str, workflow: dict) -> list[str]:
    """`github.event.sender.author_association` is always empty, so a guard on it never passes (#113)."""
    if any(SENDER_ASSOCIATION.search(s) for s in strings_in(workflow)):
        return [f"{name}: guards on github.event.sender.author_association, which webhook payloads never carry"]
    return []


PER_EVENT_GATE = re.compile(r"\bgithub\.event\.(?:label\.name|comment\.body|review\.body)\b")


def gated_concurrency_violations(name: str, workflow: dict) -> list[str]:
    """A workflow-level group is resolved before the job's `if`, so with a per-event gate (one label, one command) a
    burst of unrelated events replaces the pending run that was really asked for. Put the group on the gated job, or
    give ungated events a group of their own with `github.run_id` as claude.yml does."""
    concurrency = workflow.get("concurrency")
    if concurrency is None:
        return []
    group = str(concurrency.get("group", "") if isinstance(concurrency, dict) else concurrency)
    if "github.run_id" in group:
        return []
    return [
        f"{name}: job {job_id} gates on one event under a workflow-level concurrency group; put the group on the job"
        for job_id, job in jobs_of(workflow).items()
        if PER_EVENT_GATE.search(str(job.get("if", "")))
    ]


def pull_request_target_violations(name: str, workflow: dict) -> list[str]:
    if "pull_request_target" not in triggers_of(workflow):
        return []
    if name != "labeler.yml":
        return [f"{name}: pull_request_target is only allowed in labeler.yml"]
    return [
        f"{name}: job {job_id} checks out code under pull_request_target"
        for job_id, step in steps_of(workflow)
        if str(step.get("uses", "")).startswith("actions/checkout@")
    ]


def cron_minutes(field: str) -> set[int]:
    minutes: set[int] = set()
    for part in field.split(","):
        span, _, step = part.partition("/")
        if span == "*":
            low, high = 0, 59
        elif "-" in span:
            low, high = map(int, span.split("-"))
        else:
            low = high = int(span)
            if step:
                high = 59
        minutes.update(range(low, high + 1, int(step or 1)))
    return minutes


def cron_violations(name: str, workflow: dict) -> list[str]:
    on = workflow.get("on")
    schedules = (on.get("schedule") or []) if isinstance(on, dict) else []
    return [
        f"{name}: cron '{entry['cron']}' runs at minute 0, when GitHub's scheduler is busiest"
        for entry in schedules
        if 0 in cron_minutes(entry["cron"].split()[0])
    ]


def labeler_globs(labeler: dict) -> dict[str, list[str]]:
    """The globs of each label; only `changed-files` / `any-glob-to-any-file` rules are supported."""
    globs: dict[str, list[str]] = {}
    for label, rules in labeler.items():
        globs[label] = []
        for rule in rules:
            assert set(rule) == {"changed-files"}, f"label {label}: only changed-files rules are supported"
            for match in rule["changed-files"]:
                assert set(match) == {"any-glob-to-any-file"}, f"label {label}: only any-glob-to-any-file is supported"
                value = match["any-glob-to-any-file"]
                globs[label] += [value] if isinstance(value, str) else value
    return globs


def policy_globs(policy: str) -> list[str]:
    rules = [line.split() for line in policy.splitlines() if line.strip() and not line.lstrip().startswith("#")]
    return [glob for _, glob in rules]


def sample(glob: str) -> str:
    """A path the glob matches in both dialects: every wildcard run becomes one plain name."""
    return re.sub(r"\*+", "x", glob)


def labeler_matches(glob: str, path: str) -> bool:
    """Minimatch with `dot: true`, as actions/labeler uses: `**` spans directories, `*` and `?` stay in one."""
    pattern, i = "", 0
    while i < len(glob):
        if glob.startswith("**/", i):
            pattern, i = pattern + "(?:.*/)?", i + 3
        elif glob.startswith("**", i):
            pattern, i = pattern + ".*", i + 2
        elif glob[i] == "*":
            pattern, i = pattern + "[^/]*", i + 1
        elif glob[i] == "?":
            pattern, i = pattern + "[^/]", i + 1
        else:
            pattern, i = pattern + re.escape(glob[i]), i + 1
    return re.fullmatch(pattern, path) is not None


def policy_matches(glob: str, path: str) -> bool:
    """scripts/tier-classify.sh's `[[ $path == $glob ]]`: `*` matches across `/`."""
    return fnmatch.fnmatchcase(path, glob)


def label_violations(
    labeler: dict, labels: frozenset[str] = LABELS, path_labels: frozenset[str] = PATH_LABELS
) -> list[str]:
    violations = [f"labeler.yml: label {label} is not in the #18 label list" for label in sorted(set(labeler) - labels)]
    if set(labeler) != path_labels:
        violations.append(f"labeler.yml labels {sorted(labeler)} differ from the #18 path labels {sorted(path_labels)}")
    return violations


def unruled_label_globs(labeler: dict, policy: str) -> list[str]:
    rules = policy_globs(policy)
    return [
        glob
        for globs in labeler_globs(labeler).values()
        for glob in globs
        if not any(policy_matches(rule, sample(glob)) for rule in rules)
    ]


def unlabelled_tier_globs(labeler: dict, policy: str) -> list[str]:
    all_globs = [glob for globs in labeler_globs(labeler).values() for glob in globs]
    return [rule for rule in policy_globs(policy) if not any(labeler_matches(glob, sample(rule)) for glob in all_globs)]


def parity_violations(
    labeler: dict,
    policy: str,
    unruled_ok: dict[str, str] = LABEL_GLOBS_WITHOUT_TIER_RULE,
    unlabelled_ok: dict[str, str] = TIER_GLOBS_WITHOUT_LABEL,
) -> list[str]:
    unruled, unlabelled = unruled_label_globs(labeler, policy), unlabelled_tier_globs(labeler, policy)
    return [
        *(f"labeler.yml glob {glob} has no risk-tiers.policy rule" for glob in unruled if glob not in unruled_ok),
        *(
            f"risk-tiers.policy glob {glob} has no labeler.yml label"
            for glob in unlabelled
            if glob not in unlabelled_ok
        ),
        *(f"LABEL_GLOBS_WITHOUT_TIER_RULE row {glob} is stale" for glob in unruled_ok if glob not in unruled),
        *(f"TIER_GLOBS_WITHOUT_LABEL row {glob} is stale" for glob in unlabelled_ok if glob not in unlabelled),
    ]


def pages_violations(workflow: dict, data_files: list[str]) -> list[str]:
    """Every data file must land in the upload-pages-artifact path, directly or through a `cp` in the same job."""
    covered: set[str] = set()
    for job in jobs_of(workflow).values():
        steps = job.get("steps") or []
        artifacts = [
            str((step.get("with") or {}).get("path", "_site")).rstrip("/")
            for step in steps
            if str(step.get("uses", "")).startswith("actions/upload-pages-artifact@")
        ]
        copies = [
            shlex.split(line)
            for step in steps
            for line in str(step.get("run", "")).splitlines()
            if re.match(r"\s*cp\s", line)
        ]
        for file in data_files:
            for artifact in artifacts:
                if within(file, artifact):
                    covered.add(file)
                for args in copies:
                    operands = [arg for arg in args[1:] if not arg.startswith("-")]
                    sources, dest = operands[:-1], operands[-1].rstrip("/")
                    if within(dest, artifact) and any(within(file, src.rstrip("/")) for src in sources):
                        covered.add(file)
    return [f"pages.yml: {file} is not in the Pages artifact" for file in data_files if file not in covered]


def within(path: str, parent: str) -> bool:
    return path == parent or path.startswith(parent + "/") or fnmatch.fnmatchcase(path, parent)


FLATHUB_MEDIA = "https://dl.flathub.org/media"
FLATPAK_BUILDER_ACTION = "flatpak/flatpak-github-actions/flatpak-builder@"


def screenshot_mirror_violations(name: str, workflow: dict) -> list[str]:
    """A job that lints its exported repo by Flathub's rules without exceptions must mirror the screenshots.

    Flathub's own build rewrites the screenshot URLs to dl.flathub.org/media and commits the images to the repo's
    `screenshots/<arch>` ref; without that the repo lint fails with `appstream-external-screenshot-url` and
    `appstream-screenshots-not-mirrored-in-ostree`, as the first v0.1.0 release run did.
    """
    violations = []
    for job_id, job in jobs_of(workflow).items():
        steps = job.get("steps") or []
        strict_repo_lint = any(
            "flatpak-builder-lint" in args and "repo" in args and "--exceptions" not in args
            for step in steps
            for args in (line.split() for line in str(step.get("run", "")).splitlines())
        )
        if not strict_repo_lint:
            continue
        builds = [step for step in steps if str(step.get("uses", "")).startswith(FLATPAK_BUILDER_ACTION)]
        mirrors = [(step.get("with") or {}).get("mirror-screenshots-url") for step in builds]
        if not builds or any(mirror != FLATHUB_MEDIA for mirror in mirrors):
            violations.append(
                f"{name}: job {job_id} lints its repo without exceptions but does not mirror screenshots to "
                f"{FLATHUB_MEDIA}"
            )
    return violations


ADD_GAME = "scripts/add_game.py"
FETCH_ICON = "scripts/icons/fetch_icon.py"
CREATE_PULL_REQUEST = "peter-evans/create-pull-request@"


def needs_of(job: dict) -> set[str]:
    """The job ids a job `needs`; `needs:` is one id or a list."""
    needs = job.get("needs") or []
    return {needs} if isinstance(needs, str) else set(needs)


def icon_fetch_violations(name: str, workflow: dict) -> list[str]:
    """A job that adds a game with scripts/add_game.py and opens a pull request must fetch the game's icon (#148).

    The fetch goes between the new entry and the catalog check, so `check-jsonschema` sees the `icon` and
    `icon_source` fields it writes, and the pull request commits its `--out` directory; otherwise a game approved
    through the Add a game form gets no icon until someone runs the fetcher by hand. The pull request is opened in the
    same job or, from that job's artifact, in a job that needs it (#79: only that job holds the bot App's token).
    """
    jobs = jobs_of(workflow)
    violations = []
    for job_id, job in jobs.items():
        steps = job.get("steps") or []
        runs = [str(step.get("run", "")) for step in steps]
        adds = [i for i, run in enumerate(runs) if ADD_GAME in run]
        if not adds:
            continue
        prs = [i for i, step in enumerate(steps) if str(step.get("uses", "")).startswith(CREATE_PULL_REQUEST)]
        later = [
            step
            for other in jobs.values()
            if job_id in needs_of(other)
            for step in other.get("steps") or []
            if str(step.get("uses", "")).startswith(CREATE_PULL_REQUEST)
        ]
        if prs:
            end, pr_step = prs[0], steps[prs[0]]
        elif later:
            end, pr_step = len(steps), later[0]
        else:
            continue
        add = adds[0]
        fetches = [i for i, run in enumerate(runs) if FETCH_ICON in run and add < i < end]
        if not fetches:
            violations.append(f"{name}: job {job_id} adds a game but does not fetch its icon")
            continue
        fetch = fetches[0]
        if not any("check-jsonschema" in run for run in runs[fetch + 1 : end]):
            violations.append(f"{name}: job {job_id} does not check the catalog after fetching the icon")
        args = shlex.split(runs[fetch].replace("\\\n", " "))
        out = args[args.index("--out") + 1].rstrip("/") if "--out" in args[:-1] else None
        add_paths = re.split(r"[\s,]+", str((pr_step.get("with") or {}).get("add-paths", "")).strip())
        if out is None or not any(within(out, path.rstrip("/")) for path in add_paths if path):
            violations.append(f"{name}: job {job_id} fetches icons into {out} but its pull request does not add them")
    return violations


CHECKER = "docker://ghcr.io/flathub/flatpak-external-data-checker"


def checker_push_violations(name: str, workflow: dict) -> list[str]:
    """flatpak-external-data-checker only edits the manifest; create-pull-request pushes and opens the PR (#200).

    The checker's step is never given the GITHUB_TOKEN and checkout keeps no credentials, so the image cannot push.
    Images before 2026-10-29 also pushed to https://TOKEN:x-oauth-basic@github.com/..., which GitHub refuses for the
    workflow's GITHUB_TOKEN ("Invalid username or token"), so a run with a new tag failed instead of opening the pin PR.
    """
    violations = []
    for job_id, job in jobs_of(workflow).items():
        steps = job.get("steps") or []
        for i, step in enumerate(steps):
            if not str(step.get("uses", "")).startswith(CHECKER):
                continue
            if "--edit-only" not in shlex.split(str((step.get("with") or {}).get("args", ""))):
                violations.append(f"{name}: job {job_id} runs flatpak-external-data-checker without --edit-only")
            elif not any(str(later.get("uses", "")).startswith(CREATE_PULL_REQUEST) for later in steps[i + 1 :]):
                violations.append(
                    f"{name}: job {job_id} runs flatpak-external-data-checker but no create-pull-request step after it"
                )
    return violations


def environment_of(job: dict) -> str | None:
    """The job's environment name; `environment:` is a name or a mapping with `name`."""
    environment = job.get("environment")
    return str(environment.get("name")) if isinstance(environment, dict) else environment


CLAUDE_ACTION = "anthropics/claude-code-action@"


def bot_environment_violations(
    name: str, workflow: dict, reviewed: dict[tuple[str, str], str] = BOT_ENVIRONMENT_JOBS
) -> list[str]:
    violations = []
    for job_id, job in jobs_of(workflow).items():
        if environment_of(job) != "bot":
            continue
        if (name, job_id) not in reviewed:
            violations.append(f"{name}: job {job_id} uses the bot environment without a reviewed row")
        violations.extend(
            f"{name}: job {job_id} uses the bot environment and runs {step['uses']}"
            for step in job.get("steps") or []
            if str(step.get("uses", "")).startswith(("docker://", CLAUDE_ACTION))
        )
    return violations


GH_PR_MERGE = re.compile(r"\bgh\s+pr\s+merge\b")


def merge_violations(name: str, workflow: dict, reviewed: dict[tuple[str, str], str] = AUTO_MERGE_JOBS) -> list[str]:
    """Only reviewed jobs merge pull requests; every other bot pull request waits for a maintainer (#79)."""
    return [
        f"{name}: job {job_id} merges pull requests without a reviewed row"
        for job_id, job in jobs_of(workflow).items()
        if (name, job_id) not in reviewed
        and any(GH_PR_MERGE.search(str(step.get("run", ""))) for step in job.get("steps") or [])
    ]


# --- the repository's files -------------------------------------------------------------------------------------------

FILES = workflow_files()
IDS = [path.name for path in FILES]


def load(path: Path) -> dict:
    return load_yaml(path.read_text(encoding="utf-8"))


def test_there_are_workflows_to_check() -> None:
    assert FILES


@pytest.mark.parametrize("path", FILES, ids=IDS)
def test_top_level_permissions_are_read_only(path: Path) -> None:
    assert top_level_permission_violations(path.name, load(path)) == []


@pytest.mark.parametrize("path", FILES, ids=IDS)
def test_job_permissions_match_the_reviewed_map(path: Path) -> None:
    assert job_permission_violations(path.name, load(path)) == []


def test_every_reviewed_job_permission_row_names_an_existing_job() -> None:
    existing = {(path.name, job_id) for path in FILES for job_id in jobs_of(load(path))}
    assert sorted(set(JOB_PERMISSIONS) - existing) == []


@pytest.mark.parametrize("path", FILES, ids=IDS)
def test_every_job_has_a_timeout(path: Path) -> None:
    assert timeout_violations(path.name, load(path)) == []


@pytest.mark.parametrize("path", FILES, ids=IDS)
def test_actions_are_pinned_to_a_sha_with_a_version_comment(path: Path) -> None:
    assert uses_violations(path.name, load(path), path.read_text(encoding="utf-8")) == []


def test_every_docker_allowlist_entry_is_used() -> None:
    texts = "\n".join(path.read_text(encoding="utf-8") for path in FILES)
    assert [image for image in DOCKER_TAG_ALLOWLIST if f"docker://{image}" not in texts] == []


@pytest.mark.parametrize("path", FILES, ids=IDS)
def test_job_containers_are_pinned_by_digest(path: Path) -> None:
    assert container_violations(path.name, load(path)) == []


def test_every_container_allowlist_entry_is_used() -> None:
    images = {image for path in FILES for _, image in container_images_of(load(path))}
    assert sorted(set(CONTAINER_TAG_ALLOWLIST) - images) == []


@pytest.mark.parametrize("path", FILES, ids=IDS)
def test_no_event_field_is_interpolated_into_run(path: Path) -> None:
    assert event_in_run_violations(path.name, load(path)) == []


@pytest.mark.parametrize("path", FILES, ids=IDS)
def test_no_guard_reads_the_senders_author_association(path: Path) -> None:
    assert sender_association_violations(path.name, load(path)) == []


@pytest.mark.parametrize("path", FILES, ids=IDS)
def test_a_per_event_gate_does_not_share_a_workflow_level_group(path: Path) -> None:
    assert gated_concurrency_violations(path.name, load(path)) == []


@pytest.mark.parametrize("path", FILES, ids=IDS)
def test_pull_request_target_only_in_labeler_without_checkout(path: Path) -> None:
    assert pull_request_target_violations(path.name, load(path)) == []


@pytest.mark.parametrize("path", FILES, ids=IDS)
def test_no_cron_runs_at_minute_zero(path: Path) -> None:
    assert cron_violations(path.name, load(path)) == []


def test_labeler_labels_are_documented() -> None:
    assert label_violations(load(LABELER)) == []


def test_labeler_and_risk_tier_policy_name_the_same_paths() -> None:
    assert parity_violations(load(LABELER), POLICY.read_text(encoding="utf-8")) == []


def test_pages_publishes_every_data_file() -> None:
    data_files = sorted(str(path.relative_to(ROOT)) for path in (ROOT / "data" / "v1").glob("*.json"))
    assert data_files
    assert pages_violations(load(WORKFLOWS / "pages.yml"), data_files) == []


@pytest.mark.parametrize("path", FILES, ids=IDS)
def test_strict_repo_lint_builds_with_mirrored_screenshots(path: Path) -> None:
    assert screenshot_mirror_violations(path.name, load(path)) == []


@pytest.mark.parametrize("path", FILES, ids=IDS)
def test_a_game_added_for_a_pull_request_gets_its_icon(path: Path) -> None:
    assert icon_fetch_violations(path.name, load(path)) == []


@pytest.mark.parametrize("path", FILES, ids=IDS)
def test_the_external_data_checker_leaves_the_push_to_create_pull_request(path: Path) -> None:
    assert checker_push_violations(path.name, load(path)) == []


@pytest.mark.parametrize("path", FILES, ids=IDS)
def test_only_reviewed_jobs_use_the_bot_environment(path: Path) -> None:
    assert bot_environment_violations(path.name, load(path)) == []


def test_every_reviewed_bot_environment_row_names_a_job_that_uses_it() -> None:
    using = {
        (path.name, job_id)
        for path in FILES
        for job_id, job in jobs_of(load(path)).items()
        if environment_of(job) == "bot"
    }
    assert sorted(set(BOT_ENVIRONMENT_JOBS) - using) == []


@pytest.mark.parametrize("path", FILES, ids=IDS)
def test_only_reviewed_jobs_merge_pull_requests(path: Path) -> None:
    assert merge_violations(path.name, load(path)) == []


def test_every_reviewed_merge_row_names_a_job_that_merges() -> None:
    merging = {
        (path.name, job_id)
        for path in FILES
        for job_id, job in jobs_of(load(path)).items()
        if any(GH_PR_MERGE.search(str(step.get("run", ""))) for step in job.get("steps") or [])
    }
    assert sorted(set(AUTO_MERGE_JOBS) - merging) == []


# --- each check catches a broken fixture ------------------------------------------------------------------------------

PIN = "actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1"


def test_fixture_top_level_write_permission_fails() -> None:
    workflow = load_yaml("""
on: push
permissions:
  contents: write
jobs: {}
""")
    assert top_level_permission_violations("x.yml", workflow) == [
        "x.yml: top-level permissions are {'contents': 'write'}, expected {'contents': 'read'}"
    ]


def test_fixture_missing_top_level_permissions_fails() -> None:
    assert top_level_permission_violations("x.yml", load_yaml("on: push\njobs: {}\n"))


def test_fixture_unreviewed_job_permissions_fail() -> None:
    workflow = load_yaml("""
jobs:
  build:
    permissions:
      contents: write
""")
    assert job_permission_violations("x.yml", workflow, reviewed={}) == [
        "x.yml: job build declares unreviewed permissions {'contents': 'write'}"
    ]


def test_fixture_job_permissions_wider_than_reviewed_fail() -> None:
    workflow = load_yaml("""
jobs:
  build:
    permissions:
      contents: write
      issues: write
""")
    assert job_permission_violations("x.yml", workflow, reviewed={("x.yml", "build"): {"contents": "write"}})


def test_fixture_reviewed_job_without_permissions_fails() -> None:
    workflow = load_yaml("jobs:\n  build:\n    runs-on: ubuntu-latest\n")
    assert job_permission_violations("x.yml", workflow, reviewed={("x.yml", "build"): {"contents": "write"}})


def test_fixture_job_without_timeout_fails() -> None:
    workflow = load_yaml("""
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - run: true
""")
    assert timeout_violations("x.yml", workflow) == ["x.yml: job build has no timeout-minutes"]


@pytest.mark.parametrize(
    ("uses", "message"),
    [
        ("actions/checkout@v7", "is not pinned to a 40-hex commit SHA"),
        ("actions/checkout@3d3c42e", "is not pinned to a 40-hex commit SHA"),
        (PIN, "has no `# vX.Y.Z` version comment"),
        (f"{PIN} # latest", "has no `# vX.Y.Z` version comment"),
        ("docker://ghcr.io/flathub/flatpak-external-data-checker:latest", "neither pinned by digest"),
    ],
)
def test_fixture_unpinned_uses_fails(uses: str, message: str) -> None:
    text = f"""
jobs:
  build:
    steps:
      - uses: {uses}
"""
    violations = uses_violations("x.yml", load_yaml(text), text, docker_allowlist={})
    assert len(violations) == 1
    assert message in violations[0]


def test_fixture_pinned_uses_pass() -> None:
    text = f"""
jobs:
  build:
    steps:
      - uses: {PIN} # v7.0.1
      - uses: flatpak/flatpak-github-actions/flatpak-builder@79327416609af08178ad73b352877e51450790b3 # v6.8
      - uses: ./.github/actions/local
      - uses: docker://ghcr.io/flathub/flatpak-external-data-checker@sha256:{"a" * 64}
      - uses: docker://example.org/tagged:1
"""
    allowlist = {"example.org/tagged:1": "fixture"}
    assert uses_violations("x.yml", load_yaml(text), text, docker_allowlist=allowlist) == []


def test_fixture_uses_hidden_from_the_line_scan_fails() -> None:
    text = """
jobs:
  build:
    steps:
      - {uses: actions/checkout@v7}
"""
    assert uses_violations("x.yml", load_yaml(text), text) == [
        "x.yml: `uses: actions/checkout@v7` is not on a plain `uses:` line"
    ]


@pytest.mark.parametrize(
    "container",
    [
        "\n      image: ghcr.io/flathub-infra/flatpak-github-actions:gnome-51\n      options: --privileged",
        " ghcr.io/flathub-infra/flatpak-github-actions:gnome-51",
        f"\n      image: ghcr.io/flathub-infra/flatpak-github-actions@sha256:{'a' * 63}",
    ],
    ids=["mapping", "string", "short-digest"],
)
def test_fixture_container_image_by_tag_fails(container: str) -> None:
    workflow = load_yaml(f"""
jobs:
  flatpak:
    container:{container}
""")
    violations = container_violations("x.yml", workflow, allowlist={})
    assert len(violations) == 1
    assert "job flatpak container image" in violations[0]
    assert "neither pinned by digest nor in CONTAINER_TAG_ALLOWLIST" in violations[0]


def test_fixture_container_image_by_digest_or_allowlisted_tag_passes() -> None:
    workflow = load_yaml(f"""
jobs:
  flatpak:
    container:
      # gnome-51 as of 2026-10-16
      image: ghcr.io/flathub-infra/flatpak-github-actions@sha256:{"a" * 64}
      options: --privileged
  short:
    container: ghcr.io/flathub-infra/flatpak-github-actions:gnome-51@sha256:{"b" * 64}
  reviewed:
    container: example.org/tagged:1
  host:
    runs-on: ubuntu-latest
""")
    assert container_violations("x.yml", workflow, allowlist={"example.org/tagged:1": "fixture"}) == []


def test_fixture_event_field_in_run_fails() -> None:
    workflow = load_yaml("""
jobs:
  review:
    steps:
      - env:
          TITLE: ${{ github.event.pull_request.title }}
        run: echo "$TITLE"
      - run: echo "${{ github.event.pull_request.title }}"
      - run: echo "${{ github.event_name }}"
""")
    assert event_in_run_violations("x.yml", workflow) == [
        "x.yml: job review interpolates github.event into a run: script; pass it through env:"
    ]


def test_fixture_sender_author_association_guard_fails() -> None:
    workflow = load_yaml("""
jobs:
  add:
    if: contains(fromJSON('["OWNER"]'), github.event.sender.author_association)
""")
    assert sender_association_violations("x.yml", workflow) == [
        "x.yml: guards on github.event.sender.author_association, which webhook payloads never carry"
    ]


def test_fixture_comment_author_association_guard_passes() -> None:
    workflow = load_yaml("""
jobs:
  apply:
    # A comment about github.event.sender.author_association is not a guard.
    if: contains(fromJSON('["OWNER"]'), github.event.comment.author_association)
""")
    assert sender_association_violations("x.yml", workflow) == []


def test_fixture_label_gate_under_a_workflow_level_group_fails() -> None:
    workflow = load_yaml("""
concurrency:
  group: ${{ github.workflow }}-${{ github.event.issue.number }}
jobs:
  add:
    if: github.event.label.name == 'approved'
""")
    assert gated_concurrency_violations("x.yml", workflow) == [
        "x.yml: job add gates on one event under a workflow-level concurrency group; put the group on the job"
    ]


@pytest.mark.parametrize(
    "workflow",
    [
        # The group sits on the gated job, so a skipped event never joins it.
        """
jobs:
  add:
    if: github.event.label.name == 'approved'
    concurrency:
      group: add
""",
        # Ungated events get a group of their own (claude.yml).
        """
concurrency:
  group: c-${{ github.event.label.name == 'x' && 'queue' || github.run_id }}
jobs:
  run:
    if: github.event.label.name == 'x'
""",
        # The gate reads issue state, which every event on the issue shares (game-submission-check.yml).
        """
concurrency:
  group: c-${{ github.event.issue.number }}
jobs:
  check:
    if: contains(github.event.issue.labels.*.name, 'game-submission')
""",
    ],
)
def test_fixture_gate_with_its_own_group_passes(workflow: str) -> None:
    assert gated_concurrency_violations("x.yml", load_yaml(workflow)) == []


def test_fixture_pull_request_target_outside_labeler_fails() -> None:
    workflow = load_yaml("on:\n  pull_request_target:\njobs: {}\n")
    assert pull_request_target_violations("ci.yml", workflow) == [
        "ci.yml: pull_request_target is only allowed in labeler.yml"
    ]


def test_fixture_pull_request_target_in_a_trigger_list_fails() -> None:
    workflow = load_yaml("on: [push, pull_request_target]\njobs: {}\n")
    assert pull_request_target_violations("ci.yml", workflow)


def test_fixture_labeler_checkout_fails() -> None:
    workflow = load_yaml(f"""
on: pull_request_target
jobs:
  label:
    steps:
      - uses: {PIN} # v7.0.1
      - uses: actions/labeler@bf12e9b00b37c5c0ca2b87b79b2daf7891dbda13 # v7.0.0
""")
    assert pull_request_target_violations("labeler.yml", workflow) == [
        "labeler.yml: job label checks out code under pull_request_target"
    ]


@pytest.mark.parametrize("cron", ["0 4 * * 1", "*/15 * * * *", "0,30 * * * *", "* 4 * * *", "0-5 6 * * 1"])
def test_fixture_cron_at_minute_zero_fails(cron: str) -> None:
    workflow = load_yaml(f"on:\n  schedule:\n    - cron: '{cron}'\njobs: {{}}\n")
    assert cron_violations("x.yml", workflow) == [
        f"x.yml: cron '{cron}' runs at minute 0, when GitHub's scheduler is busiest"
    ]


def test_fixture_cron_off_the_hour_passes() -> None:
    workflow = load_yaml("on:\n  schedule:\n    - cron: '17 4 * * 1'\n    - cron: '7/20 * * * *'\njobs: {}\n")
    assert cron_violations("x.yml", workflow) == []


def test_fixture_undocumented_label_fails() -> None:
    labeler = load_yaml("""
app:
  - changed-files:
      - any-glob-to-any-file: 'dailies/**'
build:
  - changed-files:
      - any-glob-to-any-file: 'meson.build'
""")
    violations = label_violations(labeler, path_labels=frozenset({"app"}))
    assert violations == [
        "labeler.yml: label build is not in the #18 label list",
        "labeler.yml labels ['app', 'build'] differ from the #18 path labels ['app']",
    ]


def test_fixture_missing_path_label_fails() -> None:
    labeler = load_yaml("app:\n  - changed-files:\n      - any-glob-to-any-file: 'dailies/**'\n")
    assert label_violations(labeler)


PARITY_LABELER = """
app:
  - changed-files:
      - any-glob-to-any-file: ['dailies/**', 'data/ui/**']
ci:
  - changed-files:
      - any-glob-to-any-file: '.github/**'
"""


def test_fixture_labelled_path_without_tier_rule_fails() -> None:
    policy = "high .github/*\nmedium dailies/*\n"
    assert parity_violations(load_yaml(PARITY_LABELER), policy, unruled_ok={}, unlabelled_ok={}) == [
        "labeler.yml glob data/ui/** has no risk-tiers.policy rule"
    ]


def test_fixture_tier_rule_without_label_fails() -> None:
    policy = "high .github/*\nhigh meson.build\nmedium dailies/*\nmedium data/ui/*\n"
    assert parity_violations(load_yaml(PARITY_LABELER), policy, unruled_ok={}, unlabelled_ok={}) == [
        "risk-tiers.policy glob meson.build has no labeler.yml label"
    ]


def test_fixture_stale_parity_exemption_fails() -> None:
    policy = "high .github/*\nmedium dailies/*\nmedium data/ui/*\n"
    exemption = {"data/ui/**": "fixture"}
    assert parity_violations(load_yaml(PARITY_LABELER), policy, unruled_ok=exemption, unlabelled_ok={}) == [
        "LABEL_GLOBS_WITHOUT_TIER_RULE row data/ui/** is stale"
    ]


def test_fixture_pages_artifact_missing_a_data_file_fails() -> None:
    workflow = load_yaml("""
jobs:
  build:
    steps:
      - run: |
          mkdir _site
          cp data/v1/games.json _site/v1/
      - uses: actions/upload-pages-artifact@fc324d3547104276b827a68afc52ff2a11cc49c9 # v5.0.0
        with:
          path: _site
""")
    files = ["data/v1/games.json", "data/v1/popularity.json"]
    assert pages_violations(workflow, files) == ["pages.yml: data/v1/popularity.json is not in the Pages artifact"]


def test_fixture_pages_copy_outside_the_artifact_fails() -> None:
    workflow = load_yaml("""
jobs:
  build:
    steps:
      - run: cp -r data/v1 public/v1
      - uses: actions/upload-pages-artifact@fc324d3547104276b827a68afc52ff2a11cc49c9 # v5.0.0
        with:
          path: _site
""")
    assert pages_violations(workflow, ["data/v1/games.json"]) == [
        "pages.yml: data/v1/games.json is not in the Pages artifact"
    ]


def test_fixture_pages_artifact_of_the_data_directory_passes() -> None:
    workflow = load_yaml("""
jobs:
  build:
    steps:
      - uses: actions/upload-pages-artifact@fc324d3547104276b827a68afc52ff2a11cc49c9 # v5.0.0
        with:
          path: data/v1/
""")
    assert pages_violations(workflow, ["data/v1/games.json"]) == []


def strict_lint_fixture(mirror: str | None, lint: str = "flatpak-builder-lint --gha-format repo repo") -> dict:
    with_mirror = f"\n          mirror-screenshots-url: {mirror}" if mirror else ""
    return load_yaml(f"""
jobs:
  build:
    steps:
      - uses: {FLATPAK_BUILDER_ACTION}79327416609af08178ad73b352877e51450790b3 # v6.8
        with:
          manifest-path: app.json{with_mirror}
      - run: {lint}
""")


def test_fixture_strict_repo_lint_without_mirrored_screenshots_fails() -> None:
    assert screenshot_mirror_violations("release.yml", strict_lint_fixture(None)) == [
        f"release.yml: job build lints its repo without exceptions but does not mirror screenshots to {FLATHUB_MEDIA}"
    ]


def test_fixture_strict_repo_lint_mirroring_elsewhere_fails() -> None:
    assert screenshot_mirror_violations("release.yml", strict_lint_fixture("https://example.org/media"))


def test_fixture_strict_repo_lint_with_mirrored_screenshots_passes() -> None:
    assert screenshot_mirror_violations("release.yml", strict_lint_fixture(FLATHUB_MEDIA)) == []


def test_fixture_repo_lint_with_exceptions_needs_no_mirror() -> None:
    lint = "flatpak-builder-lint --exceptions --user-exceptions lint-exceptions.json repo repo"
    assert screenshot_mirror_violations("ci.yml", strict_lint_fixture(None, lint)) == []


FETCH_STEP = """
      - run: |
          python -I scripts/icons/fetch_icon.py \\
            --catalog data/v1/games.json \\
            --out data/v1/icons \\
            --id "$SLUG\""""
CHECK_STEP = """
      - run: check-jsonschema --schemafile data/v1/schema/catalog.schema.json data/v1/games.json"""
ICON_ADD_PATHS = "|\n            data/v1/games.json\n            data/v1/icons"


def submission_fixture(middle: str, add_paths: str = ICON_ADD_PATHS) -> dict:
    return load_yaml(f"""
jobs:
  add:
    steps:
      - id: add
        run: python -I scripts/add_game.py --entry result.json --catalog data/v1/games.json{middle}
      - uses: {CREATE_PULL_REQUEST}5f6978faf089d4d20b00c7766989d076bb2fc7f1 # v8.1.1
        with:
          add-paths: {add_paths}
""")


def test_fixture_added_game_without_an_icon_fetch_fails() -> None:
    assert icon_fetch_violations("approve.yml", submission_fixture(CHECK_STEP)) == [
        "approve.yml: job add adds a game but does not fetch its icon"
    ]


def test_fixture_icon_fetch_after_the_catalog_check_fails() -> None:
    assert icon_fetch_violations("approve.yml", submission_fixture(CHECK_STEP + FETCH_STEP)) == [
        "approve.yml: job add does not check the catalog after fetching the icon"
    ]


def test_fixture_icons_left_out_of_the_pull_request_fail() -> None:
    workflow = submission_fixture(FETCH_STEP + CHECK_STEP, add_paths="data/v1/games.json")
    assert icon_fetch_violations("approve.yml", workflow) == [
        "approve.yml: job add fetches icons into data/v1/icons but its pull request does not add them"
    ]


@pytest.mark.parametrize("add_paths", ["|\n            data/v1/games.json\n            data/v1/icons/", "data/**"])
def test_fixture_icon_fetched_checked_and_committed_passes(add_paths: str) -> None:
    assert icon_fetch_violations("approve.yml", submission_fixture(FETCH_STEP + CHECK_STEP, add_paths)) == []


def test_fixture_job_that_adds_no_game_needs_no_icon() -> None:
    workflow = load_yaml(f"""
jobs:
  links:
    steps:
      - run: python -I scripts/links/apply_status.py
      - uses: {CREATE_PULL_REQUEST}5f6978faf089d4d20b00c7766989d076bb2fc7f1 # v8.1.1
        with:
          add-paths: data/v1/games.json
""")
    assert icon_fetch_violations("links.yml", workflow) == []


def split_submission_fixture(add_paths: str) -> dict:
    """The add job prepares the change; the pull-request job, which needs it, opens the PR from its artifact."""
    return load_yaml(f"""
jobs:
  add:
    steps:
      - id: add
        run: python -I scripts/add_game.py --entry result.json --catalog data/v1/games.json{FETCH_STEP}{CHECK_STEP}
  pull-request:
    needs: add
    steps:
      - run: git apply "$RUNNER_TEMP/change/catalog.patch"
      - uses: {CREATE_PULL_REQUEST}5f6978faf089d4d20b00c7766989d076bb2fc7f1 # v8.1.1
        with:
          add-paths: {add_paths}
""")


def test_fixture_icon_committed_by_the_job_that_needs_the_add_job_passes() -> None:
    assert icon_fetch_violations("approve.yml", split_submission_fixture(ICON_ADD_PATHS)) == []


def test_fixture_icon_left_out_by_the_job_that_needs_the_add_job_fails() -> None:
    assert icon_fetch_violations("approve.yml", split_submission_fixture("data/v1/games.json")) == [
        "approve.yml: job add fetches icons into data/v1/icons but its pull request does not add them"
    ]


def test_fixture_added_game_without_an_icon_fetch_before_a_dependent_pull_request_fails() -> None:
    workflow = split_submission_fixture(ICON_ADD_PATHS)
    workflow["jobs"]["add"]["steps"] = workflow["jobs"]["add"]["steps"][:1]
    assert icon_fetch_violations("approve.yml", workflow) == [
        "approve.yml: job add adds a game but does not fetch its icon"
    ]


def checker_fixture(args: str, then: str = "") -> dict:
    return load_yaml(f"""
jobs:
  check:
    steps:
      - uses: {CHECKER}@sha256:{"a" * 64}
        with:
          args: {args} build-aux/flatpak/io.github.tim_van_oudheusden.Dailies.json{then}
""")


CHECKER_PR_STEP = f"""
      - uses: {CREATE_PULL_REQUEST}5f6978faf089d4d20b00c7766989d076bb2fc7f1 # v8.1.1
        with:
          add-paths: build-aux/flatpak/io.github.tim_van_oudheusden.Dailies.json"""


@pytest.mark.parametrize("args", ["--update --never-fork", "--commit-only", ""])
def test_fixture_checker_that_commits_or_pushes_itself_fails(args: str) -> None:
    assert checker_push_violations("checker.yml", checker_fixture(args, CHECKER_PR_STEP)) == [
        "checker.yml: job check runs flatpak-external-data-checker without --edit-only"
    ]


def test_fixture_checker_edit_without_a_pull_request_fails() -> None:
    assert checker_push_violations("checker.yml", checker_fixture("--edit-only")) == [
        "checker.yml: job check runs flatpak-external-data-checker but no create-pull-request step after it"
    ]


def test_fixture_checker_edit_then_create_pull_request_passes() -> None:
    workflow = checker_fixture("--edit-only --require-important-update", CHECKER_PR_STEP)
    assert checker_push_violations("checker.yml", workflow) == []


@pytest.mark.parametrize(
    "environment",
    ["bot", "\n      name: bot\n      deployment: false"],
    ids=["name", "mapping"],
)
def test_fixture_unreviewed_job_in_the_bot_environment_fails(environment: str) -> None:
    workflow = load_yaml(f"jobs:\n  ask:\n    environment: {environment}\n    runs-on: ubuntu-latest\n")
    assert bot_environment_violations("x.yml", workflow, reviewed={}) == [
        "x.yml: job ask uses the bot environment without a reviewed row"
    ]


def test_fixture_bot_environment_job_that_runs_a_docker_image_fails() -> None:
    workflow = load_yaml(f"""
jobs:
  pin:
    environment: bot
    steps:
      - uses: {CHECKER}@sha256:{"a" * 64}
""")
    assert bot_environment_violations("x.yml", workflow, reviewed={("x.yml", "pin"): "fixture"}) == [
        f"x.yml: job pin uses the bot environment and runs {CHECKER}@sha256:{'a' * 64}"
    ]


def test_fixture_bot_environment_job_with_a_model_step_fails() -> None:
    claude = "anthropics/claude-code-action@db77d4d3c98f3f6380e7cd45ffba2342a3dbde3c"
    workflow = load_yaml(f"""
jobs:
  publish:
    environment: bot
    steps:
      - uses: {claude} # v1.0.254
""")
    assert bot_environment_violations("x.yml", workflow, reviewed={("x.yml", "publish"): "fixture"}) == [
        f"x.yml: job publish uses the bot environment and runs {claude}"
    ]


def test_fixture_reviewed_bot_environment_job_and_other_environments_pass() -> None:
    workflow = load_yaml(f"""
jobs:
  pin:
    environment:
      name: bot
    steps:
      - uses: {PIN} # v7.0.1
  deploy:
    environment: github-pages
    steps:
      - uses: {CHECKER}@sha256:{"a" * 64}
""")
    assert bot_environment_violations("x.yml", workflow, reviewed={("x.yml", "pin"): "fixture"}) == []


@pytest.mark.parametrize(
    "run",
    ['gh pr merge --auto --merge "$PR_URL"', "gh  pr merge 12", "set -e\nGH_TOKEN=x gh pr merge --squash 3"],
    ids=["auto", "spaced", "later-line"],
)
def test_fixture_unreviewed_job_that_merges_pull_requests_fails(run: str) -> None:
    workflow = load_yaml("jobs:\n  links:\n    steps:\n      - run: |\n          " + run.replace("\n", "\n          "))
    assert merge_violations("x.yml", workflow, reviewed={}) == [
        "x.yml: job links merges pull requests without a reviewed row"
    ]


def test_fixture_reviewed_merge_and_other_gh_pr_commands_pass() -> None:
    workflow = load_yaml("""
jobs:
  publish:
    steps:
      - run: gh pr merge --auto --merge "$PR_URL"
  links:
    steps:
      - run: gh pr view 12 --json mergedAt && gh pr list --state merged
""")
    assert merge_violations("x.yml", workflow, reviewed={("x.yml", "publish"): "fixture"}) == []
