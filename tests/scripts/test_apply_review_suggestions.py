import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "apply-review-suggestions.sh"
BASH = shutil.which("bash")

pytestmark = pytest.mark.skipif(
    BASH is None or not all(shutil.which(tool) for tool in ("jq", "base64", "realpath")),
    reason="needs bash, jq and coreutils",
)

FILE = "one\ntwo\nthree\nfour\nfive\n"


def comment(comment_id: int, path: str, line: int | None, body: str, **fields: object) -> dict:
    """One entry of `GET /repos/{owner}/{repo}/pulls/{number}/comments`; `fields` overrides the other fields."""
    return {
        "id": comment_id,
        "path": path,
        "line": line,
        "start_line": None,
        "side": "RIGHT",
        "start_side": None,
        "author_association": "MEMBER",
        "body": body,
        **fields,
    }


def suggestion(*lines: str) -> str:
    return "Try this:\n```suggestion\n" + "".join(f"{line}\n" for line in lines) + "```\n"


def apply(
    tmp_path: Path, comments: list[dict], cwd: Path | None = None
) -> tuple[subprocess.CompletedProcess[str], Path]:
    checkout = tmp_path / "pr"
    checkout.mkdir(exist_ok=True)
    if not (checkout / "a.txt").exists():
        (checkout / "a.txt").write_text(FILE, encoding="utf-8")
    comments_file = tmp_path / "comments.json"
    comments_file.write_text(json.dumps(comments), encoding="utf-8")
    scratch = tmp_path / "scratch"
    scratch.mkdir(exist_ok=True)
    cwd = cwd or checkout
    result = subprocess.run(  # noqa: S603 - fixed script, test-controlled environment
        [BASH, str(SCRIPT)],
        cwd=cwd,
        env={**os.environ, "COMMENTS_FILE": str(comments_file), "PWD": str(cwd), "TMPDIR": str(scratch)},
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )
    return result, checkout


def test_applies_a_single_line_suggestion(tmp_path: Path) -> None:
    result, checkout = apply(tmp_path, [comment(1, "a.txt", 2, suggestion("TWO"))])

    assert result.returncode == 0, result.stderr
    assert result.stdout == "applied: a.txt:2-2 (comment 1)\n"
    assert (checkout / "a.txt").read_text(encoding="utf-8") == "one\nTWO\nthree\nfour\nfive\n"


def test_replaces_a_line_range(tmp_path: Path) -> None:
    result, checkout = apply(tmp_path, [comment(1, "a.txt", 4, suggestion("middle"), start_line=2)])

    assert "applied: a.txt:2-4 (comment 1)" in result.stdout
    assert (checkout / "a.txt").read_text(encoding="utf-8") == "one\nmiddle\nfive\n"


def test_an_empty_suggestion_deletes_the_lines(tmp_path: Path) -> None:
    _, checkout = apply(tmp_path, [comment(1, "a.txt", 3, "```suggestion\n```")])

    assert (checkout / "a.txt").read_text(encoding="utf-8") == "one\ntwo\nfour\nfive\n"


def test_applies_several_suggestions_in_one_file_bottom_up(tmp_path: Path) -> None:
    comments = [
        comment(1, "a.txt", 1, suggestion("ONE", "ONE-AND-A-HALF")),
        comment(2, "a.txt", 4, suggestion("FOUR")),
    ]

    result, checkout = apply(tmp_path, comments)

    assert result.returncode == 0, result.stderr
    assert (checkout / "a.txt").read_text(encoding="utf-8") == "ONE\nONE-AND-A-HALF\ntwo\nthree\nFOUR\nfive\n"


def test_skips_an_overlapping_suggestion(tmp_path: Path) -> None:
    comments = [
        comment(1, "a.txt", 3, suggestion("A"), start_line=2),
        comment(2, "a.txt", 4, suggestion("B"), start_line=3),
    ]

    result, checkout = apply(tmp_path, comments)

    assert "applied: a.txt:3-4 (comment 2)" in result.stdout
    assert "skipped: comment 1 on a.txt: overlaps another applied suggestion" in result.stdout
    assert (checkout / "a.txt").read_text(encoding="utf-8") == "one\ntwo\nB\nfive\n"


def test_a_fence_inside_a_line_is_part_of_the_suggestion(tmp_path: Path) -> None:
    _, checkout = apply(tmp_path, [comment(1, "a.txt", 1, suggestion("use ``` here"))])

    assert (checkout / "a.txt").read_text(encoding="utf-8").startswith("use ``` here\ntwo\n")


def test_a_suggested_fence_line_is_content_until_a_bare_closing_fence(tmp_path: Path) -> None:
    # CommonMark: a closing fence holds only backticks and spaces, so ```bash is the suggestion's content (#162).
    checkout = tmp_path / "pr"
    checkout.mkdir()
    (checkout / "a.txt").write_text("Install:\n```sh\nmake\n```\n", encoding="utf-8")
    comments = [
        comment(1, "a.txt", 2, suggestion("```bash")),
        comment(2, "a.txt", 3, suggestion("make all", "``` not a fence")),
    ]

    result, _ = apply(tmp_path, comments)

    assert result.returncode == 0, result.stderr
    assert (checkout / "a.txt").read_text(encoding="utf-8") == "Install:\n```bash\nmake all\n``` not a fence\n```\n"


def test_a_longer_fence_lets_a_suggestion_carry_a_code_block(tmp_path: Path) -> None:
    body = "Nit:\n````suggestion\nRun:\n```sh\nmake\n```\n`````  \nThanks.\n"

    result, checkout = apply(tmp_path, [comment(1, "a.txt", 2, body)])

    assert result.returncode == 0, result.stderr
    assert result.stdout == "applied: a.txt:2-2 (comment 1)\n"
    assert (checkout / "a.txt").read_text(encoding="utf-8") == "one\nRun:\n```sh\nmake\n```\nthree\nfour\nfive\n"


@pytest.mark.parametrize(
    "body",
    [
        pytest.param("Try ```suggestion\nX\n```\n", id="fence after other text"),
        pytest.param("``suggestion\nX\n``\n", id="two backticks"),
    ],
)
def test_only_a_fence_of_three_backticks_at_the_start_of_a_line_opens_a_suggestion(tmp_path: Path, body: str) -> None:
    result, checkout = apply(tmp_path, [comment(1, "a.txt", 2, body)])

    assert result.stdout == "no suggestions to apply\n"
    assert (checkout / "a.txt").read_text(encoding="utf-8") == FILE


def test_blanks_after_the_opening_fence_are_ignored(tmp_path: Path) -> None:
    _, checkout = apply(tmp_path, [comment(1, "a.txt", 1, "```suggestion \t\nONE\n```\n")])

    assert (checkout / "a.txt").read_text(encoding="utf-8").startswith("ONE\ntwo\n")


def test_windows_line_endings_in_the_comment_are_ignored(tmp_path: Path) -> None:
    _, checkout = apply(tmp_path, [comment(1, "a.txt", 1, "```suggestion\r\nONE\r\n```\r\n")])

    assert (checkout / "a.txt").read_text(encoding="utf-8").startswith("ONE\ntwo\n")


@pytest.mark.parametrize("association", ["OWNER", "MEMBER", "COLLABORATOR"])
def test_applies_a_suggestion_from_anyone_with_write_access(tmp_path: Path, association: str) -> None:
    result, _ = apply(tmp_path, [comment(1, "a.txt", 2, suggestion("TWO"), author_association=association)])

    assert result.stdout == "applied: a.txt:2-2 (comment 1)\n"


def test_each_file_has_its_own_line_count_and_overlaps(tmp_path: Path) -> None:
    # b.txt is longer than a.txt, and its range sorts between the two overlapping ranges of a.txt.
    checkout = tmp_path / "pr"
    checkout.mkdir()
    (checkout / "b.txt").write_text("".join(f"{number}\n" for number in range(1, 9)), encoding="utf-8")
    comments = [
        comment(1, "a.txt", 4, suggestion("A"), start_line=3),
        comment(2, "b.txt", 8, suggestion("B"), start_line=3),
        comment(3, "a.txt", 3, suggestion("C"), start_line=2),
    ]

    result, _ = apply(tmp_path, comments)

    assert result.stdout.splitlines() == [
        "applied: a.txt:3-4 (comment 1)",
        "skipped: comment 3 on a.txt: overlaps another applied suggestion",
        "applied: b.txt:3-8 (comment 2)",
    ]
    assert (checkout / "a.txt").read_text(encoding="utf-8") == "one\ntwo\nA\nfive\n"
    assert (checkout / "b.txt").read_text(encoding="utf-8") == "1\n2\nB\n"


def test_applies_to_a_last_line_without_a_trailing_newline(tmp_path: Path) -> None:
    checkout = tmp_path / "pr"
    checkout.mkdir()
    (checkout / "a.txt").write_text("one\ntwo", encoding="utf-8")

    result, _ = apply(tmp_path, [comment(1, "a.txt", 2, suggestion("TWO"))])

    assert result.stdout == "applied: a.txt:2-2 (comment 1)\n"
    assert (checkout / "a.txt").read_text(encoding="utf-8") == "one\nTWO\n"


def test_keeps_the_mode_of_the_file(tmp_path: Path) -> None:
    checkout = tmp_path / "pr"
    checkout.mkdir()
    (checkout / "a.txt").write_text(FILE, encoding="utf-8")
    (checkout / "a.txt").chmod(0o755)

    apply(tmp_path, [comment(1, "a.txt", 2, suggestion("TWO"))])

    assert (checkout / "a.txt").stat().st_mode & 0o777 == 0o755


def test_leaves_no_temporary_file_behind(tmp_path: Path) -> None:
    apply(tmp_path, [comment(1, "a.txt", 2, suggestion("TWO"))])

    assert not list((tmp_path / "scratch").iterdir())


def test_a_checkout_entered_through_a_symlink_is_still_the_checkout(tmp_path: Path) -> None:
    checkout = tmp_path / "pr"
    checkout.mkdir()
    link = tmp_path / "link"
    link.symlink_to(checkout)

    result, _ = apply(tmp_path, [comment(1, "a.txt", 2, suggestion("TWO"))], cwd=link)

    assert result.stdout == "applied: a.txt:2-2 (comment 1)\n"


@pytest.mark.parametrize(
    ("review_comment", "reason"),
    [
        pytest.param(
            comment(1, "a.txt", 2, suggestion("X"), author_association="CONTRIBUTOR"),
            "author CONTRIBUTOR has no write access",
            id="untrusted author",
        ),
        pytest.param(comment(1, "a.txt", None, suggestion("X")), "outdated", id="outdated"),
        pytest.param(
            comment(1, "a.txt", 2, suggestion("X"), side="LEFT"), "on the base side of the diff", id="base side"
        ),
        pytest.param(
            comment(1, "a.txt", 2, suggestion("X"), start_line=1, start_side="LEFT"),
            "on the base side of the diff",
            id="range starting on the base side",
        ),
        pytest.param(
            comment(1, "a.txt", 2, suggestion("X") + suggestion("Y")),
            "more than one suggestion block",
            id="two blocks",
        ),
        pytest.param(comment(1, "a.txt", 9, suggestion("X")), "lines 9-9 are not in the file", id="past the end"),
        pytest.param(
            comment(1, "a.txt", 2, suggestion("X"), start_line=0),
            "lines 0-2 are not in the file",
            id="before the start",
        ),
        pytest.param(
            comment(1, "a.txt", 2, suggestion("X"), start_line=3), "lines 3-2 are not in the file", id="reversed range"
        ),
        pytest.param(comment(1, "missing.txt", 1, suggestion("X")), "not a regular file in the checkout", id="missing"),
        pytest.param(
            comment(1, "../outside.txt", 1, suggestion("X")), "not a regular file in the checkout", id="outside"
        ),
    ],
)
def test_skips_suggestions_it_must_not_apply(tmp_path: Path, review_comment: dict, reason: str) -> None:
    outside = tmp_path / "outside.txt"
    outside.write_text(FILE, encoding="utf-8")

    result, checkout = apply(tmp_path, [review_comment])

    assert result.returncode == 0, result.stderr
    assert result.stdout == f"skipped: comment 1 on {review_comment['path']}: {reason}\n"
    assert (checkout / "a.txt").read_text(encoding="utf-8") == FILE
    assert outside.read_text(encoding="utf-8") == FILE


def test_never_writes_through_a_symlink_out_of_the_checkout(tmp_path: Path) -> None:
    outside = tmp_path / "outside.txt"
    outside.write_text(FILE, encoding="utf-8")
    checkout = tmp_path / "pr"
    checkout.mkdir()
    (checkout / "link.txt").symlink_to(outside)

    result, _ = apply(tmp_path, [comment(1, "link.txt", 1, suggestion("X"))])

    assert "skipped: comment 1 on link.txt: not a regular file in the checkout" in result.stdout
    assert outside.read_text(encoding="utf-8") == FILE


def test_a_directory_named_like_the_checkout_is_outside_it(tmp_path: Path) -> None:
    sibling = tmp_path / "pr-other"
    sibling.mkdir()
    (sibling / "b.txt").write_text(FILE, encoding="utf-8")

    result, _ = apply(tmp_path, [comment(1, "../pr-other/b.txt", 1, suggestion("X"))])

    assert result.stdout == "skipped: comment 1 on ../pr-other/b.txt: not a regular file in the checkout\n"
    assert (sibling / "b.txt").read_text(encoding="utf-8") == FILE


def test_skips_a_directory(tmp_path: Path) -> None:
    (tmp_path / "pr" / "sub").mkdir(parents=True)

    result, _ = apply(tmp_path, [comment(1, "sub", 1, suggestion("X"))])

    assert result.stdout == "skipped: comment 1 on sub: not a regular file in the checkout\n"


def test_skips_a_symlink_to_a_workflow_file(tmp_path: Path) -> None:
    checkout = tmp_path / "pr"
    workflows = checkout / ".github" / "workflows"
    workflows.mkdir(parents=True)
    (workflows / "ci.yml").write_text("name: CI\n", encoding="utf-8")
    (checkout / "link.yml").symlink_to(workflows / "ci.yml")

    result, _ = apply(tmp_path, [comment(1, "link.yml", 1, suggestion("name: Evil"))])

    assert "workflow files cannot be pushed with the workflow token" in result.stdout
    assert (workflows / "ci.yml").read_text(encoding="utf-8") == "name: CI\n"


def test_applies_to_other_files_under_dot_github(tmp_path: Path) -> None:
    github = tmp_path / "pr" / ".github"
    github.mkdir(parents=True)
    (github / "CODEOWNERS").write_text("* @old\n", encoding="utf-8")

    result, _ = apply(tmp_path, [comment(1, ".github/CODEOWNERS", 1, suggestion("* @new"))])

    assert result.stdout == "applied: .github/CODEOWNERS:1-1 (comment 1)\n"
    assert (github / "CODEOWNERS").read_text(encoding="utf-8") == "* @new\n"


def test_a_file_name_starting_with_a_dash_is_not_an_option(tmp_path: Path) -> None:
    checkout = tmp_path / "pr"
    checkout.mkdir()
    (checkout / "-x.txt").write_text(FILE, encoding="utf-8")

    result, _ = apply(tmp_path, [comment(1, "-x.txt", 2, suggestion("TWO"))])

    assert result.stdout == "applied: -x.txt:2-2 (comment 1)\n"


def test_skips_workflow_files(tmp_path: Path) -> None:
    workflows = tmp_path / "pr" / ".github" / "workflows"
    workflows.mkdir(parents=True)
    (workflows / "ci.yml").write_text("name: CI\n", encoding="utf-8")

    result, _ = apply(tmp_path, [comment(1, ".github/workflows/ci.yml", 1, suggestion("name: Evil"))])

    assert "workflow files cannot be pushed with the workflow token" in result.stdout
    assert (workflows / "ci.yml").read_text(encoding="utf-8") == "name: CI\n"


def test_comments_without_suggestions_change_nothing(tmp_path: Path) -> None:
    result, checkout = apply(tmp_path, [comment(1, "a.txt", 2, "Looks good, but ```code``` here.")])

    assert result.returncode == 0, result.stderr
    assert result.stdout == "no suggestions to apply\n"
    assert (checkout / "a.txt").read_text(encoding="utf-8") == FILE


def test_needs_the_comments_file(tmp_path: Path) -> None:
    env = {key: value for key, value in os.environ.items() if key != "COMMENTS_FILE"}
    result = subprocess.run(  # noqa: S603 - fixed script, test-controlled environment
        [BASH, str(SCRIPT)], cwd=tmp_path, env=env, capture_output=True, text=True, check=False, timeout=60
    )

    assert result.returncode != 0
    assert "COMMENTS_FILE must point to the review comments JSON" in result.stderr
