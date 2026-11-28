# Where a pull request came from, shared by scripts/ai-audit-report.sh and scripts/pr-metrics.sh so the two reports
# cannot disagree about which pull requests are agent work. Reads one entry of
# `gh pr list --json author,headRefName,body`; without a body only the author and the branch decide.
#
# Sources, first match wins:
#   Hive             the body has a Hive signature line, "-- hive: agent=<a> … model=<m> …" (contributor runs
#                    leave out agent=); PRs merged before 2026-11-20 signed with an em-dash, "— hive: …", and
#                    contributor runs then signed "— omp (Claude Code), model=<m>"; both older forms still count;
#                    or the author is the Hive GitHub App, hive-worker-bee (formerly hive-forge-app;
#                    both names count; gh pr list reports it as app/<slug>, the REST API as <slug>[bot])
#   Claude Code (CI) head branch claude/*
#   Dependabot       head branch dependabot/*
#   Other            anything else

def sources: ["Hive", "Claude Code (CI)", "Dependabot", "Other"];

# Hive's signature is a line of its own, usually near the end of the body but not always last, so read every line.
# Hive signs "-- hive: " since 2026-11-20; the em-dash and omp forms keep older PRs attributed.
def signature:
  (.body // "") | split("\n")
  | map(rtrimstr("\r")
    | select(startswith("-- hive: ") or startswith("— hive: ") or test("^— omp \\(Claude Code\\), model=")))
  | .[0];

def source:
  (.headRefName // "") as $branch
  | if signature != null
      or ((.author.login // "")
        | IN("app/hive-worker-bee", "hive-worker-bee[bot]", "app/hive-forge-app", "hive-forge-app[bot]"))
    then "Hive"
    elif ($branch | startswith("claude/")) then "Claude Code (CI)"
    elif ($branch | startswith("dependabot/")) then "Dependabot"
    else "Other" end;

def agent_authored: source | IN("Hive", "Claude Code (CI)");
