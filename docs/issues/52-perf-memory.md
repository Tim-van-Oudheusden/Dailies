---
key: 52
title: perf: measure cold start and WebKit memory in the Flatpak
type: Task
labels: milestone::M1, type::task, priority::medium, app
parent: 3
blocked_by: 25, 46, 53
---
> **Risk tier:** low · **Size:** S · **Output:** a "Measurements" section in `docs/architecture.md`

## Why

Two of the plan's risks rest on numbers nobody has measured **[U]**:

1. **WebKitGTK memory per open game** (proposal §17 risk 4). The mitigations are already in #46 (one live WebView, destroyed on pop, `DOCUMENT_VIEWER` cache model), but the M1 exit criterion asks for a number.
2. **Python cold start in the Flatpak** (§17 risk 8). The documented fallback trigger for a Rust port is a **measured cold start above ~1 s on a modern laptop**.

## Tasks

- [ ] **Startup:** `hyperfine --warmup 1 --runs 10 'flatpak run io.github.tim_van_oudheusden.Dailies --smoke'` for warm starts. For cold starts, drop caches with `sync; echo 3 | sudo tee /proc/sys/vm/drop_caches` before each run (`--prepare`). Report the median and p95, plus the machine (CPU, RAM, disk, desktop)
- [ ] **Import profile:** `flatpak run --command=sh … -c 'python3 -X importtime -m dailies --smoke' 2> importtime.txt`; list the top 10 imports and confirm WebKit isn't among them (#45)
- [ ] **Memory:** with `smem -t -k -P 'dailies|WebKit'`, record (a) the library alone, (b) the library with one NYT game open in-app, (c) the same after popping back to the library. Also compare against `/usr/libexec/webkitgtk-6.0/MiniBrowser` on the same NYT game in `org.gnome.Platform//51`
- [ ] Confirm the WebKit `hardware-acceleration-policy` and ITP defaults at runtime; they are **[U]** in [`embedded-browser.md` §10](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/embedded-browser.md)
- [ ] Write it all up in `docs/architecture.md` §Measurements (#53), including a **Decision:** line: "Cold start = X s → no Rust port (threshold ~1 s)" or the opposite

## Acceptance criteria

- [ ] All three measurements are recorded with the commit hash and machine details
- [ ] If cold start is above 1 s, open a follow-up issue to investigate (lazy imports, gresource size) before considering a port

## References

- [`mvp-first.md` §1 (fallback trigger), §5.2 (memory), §16 (M1 exit), §17 risks 4 and 8](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/proposals/mvp-first.md)
- [`embedded-browser.md` §2.7](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/embedded-browser.md)
- [`stack-crossplatform.md` §3.3, §4](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/stack-crossplatform.md)
