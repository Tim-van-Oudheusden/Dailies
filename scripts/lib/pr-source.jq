# Where a pull request came from, shared by scripts/ai-audit-report.sh and scripts/pr-metrics.sh so the two reports
# cannot disagree about which pull requests are agent work. Reads one entry of
# `gh pr list --json author,headRefName,body`; without a body only the author and the branch decide.
#
# Sources, first match wins:
#   Hive             the body has a Hive signature line, "— hive: agent=<a> … model=<m> …" or a
#                    contributor run's "— omp (Claude Code), model=<m>" (contributor runs leave out agent=),
#                    or the author is the Hive GitHub App, hive-worker-bee (formerly hive-forge-app;
#                    both names count; gh pr list reports it as app/<slug>, the REST API as <slug>[bot])
#   Claude Code (CI) head branch claude/*
#   Dependabot       head branch dependabot/*
#   Other            anything else

def sources: ["Hive", "Claude Code (CI)", "Dependabot", "Other"];

# Hive ends every PR body it writes with a signature line; contributor runs sign as omp.
def signature:
  (.body // "") | split("\n")
  | map(rtrimstr("\r") | select(startswith("— hive: ") or test("^— omp \\(Claude Code\\), model="))) | .[0];

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
