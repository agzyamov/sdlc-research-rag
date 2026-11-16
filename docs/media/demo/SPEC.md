# Spec: README demo (silent)

- 1920×1080, 30 fps, 30 s, no audio (by request). The README shows a GIF that links to the MP4.
- Real app frames only: `web/capture/demo.capture.ts` (Playwright, live stack, light theme, DPR 2) writes `assets/capture/*.jpg` and `capture.json` (click-target boxes). Counts on screen are whatever the live corpus returns.
- Screen inset at 90% on a #e7e8ea ground, radius 18 px, soft shadow.
- Camera: scale 1–1.85, `power2.inOut`, 0.7–1.0 s per move. Cursor: 48 px arrow, `power3.inOut` moves, press 0.82 → 1, orange (#e8590c) ripple; adapted from registry `cursor-zoom-follow`.
- Captions: ≤ 6 words, Geist (the app font) 700 42 px, dark pill, 132 px above the bottom; blur-in 0.6 s `expo.out` (registry `soft-blur-in`), exit 0.25 s `power3.in`.
- - Beats (s): title card 0–4.4 (name on screen from frame 0); chat 4–12 (type, send, the answer wipes in, sources highlighted); landscape 12–16; graph 16–20; detail 20–26 (4. Testing → its papers → "Why these tags?" → quote highlighted); end card 26.8–30.
- Chat: `/api/chat` is the only mocked route in the capture. The answer is staged so the capture never calls the LLM; every sentence restates a verified abstract quote from `/api/papers` evidence, and the three cited papers are real. The README caption says it is staged.
Banned: stock UI mockups, made-up numbers, music, voice, rhetorical hook lines.
