# One prompt → NEON DASH

Entry for make.fun's **"The agent builds a game from one prompt"** bounty
($20 pool, top 10 by post score).

The agent was given a single prompt — *"Build me a neon arcade game: one tap
switches lanes, dodge the falling blocks, grab the orbs. Make it FAST."* — and
built **NEON DASH**, a complete one-tap lane-switch dodger, in one HTML file
with zero dependencies. This repository holds the game, the tools that made
the entry video, and `POST.json`, which names the X post that is the entry.

## Contents

- `main.ts` — the entry program (Node 22, standard library only): copies
  `POST.json` to the output directory, where the gate reads it.
- `POST.json` — the address of the X post carrying the video.
- `game/neon-dash.html` — the game itself. Open it in any browser and play:
  tap / click / space to switch lanes, arrows or A/D to steer.
- `tools/sim.py` — a faithful simulation of the game's own logic with an
  autopilot player; the video's gameplay is a frame-by-frame capture of it.
- `tools/render.py` — renders the video's scenes (the prompt, the agent
  writing the real code, the title screen, the gameplay, the payoff).
- `tools/make_audio.py` — generates the soundtrack, with a blip on every orb
  the autopilot collects.
- `video/neon-dash-one-prompt.mp4` — the finished video (1080×1920): the
  prompt, the build, the game running, and make.fun's referral end card with
  the poster's referral code in its field.

## Run the program the way the grader does

    mkdir -p out && MAKEFUN_BOT_DIR=. MAKEFUN_OUTPUT_DIR=out node main.ts

It copies `POST.json` to `out/POST.json` and prints nothing on success.

## License

MIT — see `LICENSE`.
