---
key: 69
title: build(flatpak): audio for music games (`--socket=pulseaudio`) per decision
type: Task
labels: milestone::M3, type::task, priority::low, flatpak
parent: 5
blocked_by: 16, 25
---
> **Risk tier:** high (finish-args) · **Size:** XS

## Tasks (depend on #16)

**If the decision is "add":**
- [ ] Add `--socket=pulseaudio` to **both** manifests (#25)
- [ ] Add a line to the permission justification table in the PR (and later the Flathub PR): "pulseaudio: audio for music games (Bandle, Heardle Decades, Songless) played in the built-in browser"
- [ ] Add a metainfo `<release>` note for the next version: "Music games now play sound inside Dailies."
- [ ] Update `SECURITY-AI.md` / the `CONTRIBUTING.md` permission list if they enumerate finish-args

**If the decision is "wait":**
- [ ] Document it in `docs/architecture.md`: "Decision: no audio permission until requested. Why: …", and add a FAQ line to the README ("Music games: use Open in Browser")
- [ ] Close this issue as *not planned*, leaving a pointer for whoever reopens it

## Acceptance criteria

- [ ] (add) Bandle plays audio in-app, and `flatpak-builder-lint manifest` is still clean
- [ ] (wait) The documentation states the limitation and the workaround

## References

- [`mvp-first.md` §9, §16 (M3), §18.4](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/proposals/mvp-first.md)
- [`embedded-browser.md` §1.4, §9.3](https://github.com/Tim-van-Oudheusden/Dailies/blob/main/docs/research/embedded-browser.md)
