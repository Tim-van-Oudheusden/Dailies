---
key: 5
title: [Epic] M3 Agentic report and hygiene → v0.3.0
type: Task
labels: epic, milestone::M3, priority::medium
parent: 1
---
**Target:** weeks 6–8 · **Source:** [`mvp-first.md` §8 (agentic report), §11, §16 (M3)](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/proposals/mvp-first.md)

## Goal

Add the agentic weekly report. Claude writes prose only; the numbers stay deterministic Python. Also add the `flatpak-external-data-checker` and the operational runbooks, polish the toasts, act on the audio decision, and cut the **third** tagged release. Three releases are the history Flathub expects before a submission (`flatpak-release-pipeline.md` §4.2).

## Exit criteria

- [ ] Three tagged releases exist (`v0.1.0`, `v0.2.0`, `v0.3.0`) (#71)
- [ ] `nightly-compliance` has been green for two consecutive weeks
- [ ] At least one `docs/popularity/<week>.md` report written by the pipeline and merged (#66)

## Sub-issues

Decisions that gate this milestone: #14 (narrative model/path), #16 (audio).

{{CHILDREN}}
