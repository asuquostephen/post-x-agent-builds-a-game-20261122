#!/usr/bin/env python3
"""NEON DASH simulation — mirrors game/neon-dash.html constants exactly.
An autopilot plays: dodge blocks, chase orbs. Deterministic (seeded).
Used to render the gameplay section of the entry video frame by frame,
and to emit event timestamps (orb collects, near misses) for the audio.
"""
import random

W, H = 540, 960
LANES = [90, 270, 450]
SHIP_Y = H - 150
BLOCK_W, BLOCK_H = 118, 46
ORB_R = 21
START_SPEED, MAX_SPEED, ACCEL = 380, 920, 15
SPAWN_EVERY = 0.55
ORB_CHANCE = 0.38
ORB_SCORE, FLOW_SCORE = 60, 12
FPS = 30
DT = 1.0 / FPS


class Sim:
    def __init__(self, seed=7):
        self.rng = random.Random(seed)
        self.lane = 1
        self.ship_x = float(LANES[1])
        self.ship_from = float(LANES[1])
        self.ship_t = 1.0
        self.entities = []          # dicts: lane, y, kind, got
        self.speed = START_SPEED
        self.spawn_t = 0.0
        self.time = 0.0
        self.score = 0.0
        self.pops = []              # {x, y, t, text}
        self.events = []            # (time, kind, data)
        self.move_cd = 0.0
        self.last_dodge = -9.0      # time ship last left a lane
        self.last_dodge_from = None
        self.crashed = False
        self.speedup_flagged = False

    def _move(self, nl):
        if nl != self.lane and 0 <= nl <= 2:
            self.last_dodge = self.time
            self.last_dodge_from = self.lane
            self.ship_from = self.ship_x
            self.lane = nl
            self.ship_t = 0.0
            self.move_cd = 0.16

    def _autopilot(self):
        if self.move_cd > 0:
            return
        blocks = [e for e in self.entities if e["kind"] == "block"]
        orbs = [e for e in self.entities if e["kind"] == "orb" and not e["got"]]

        def t_hit(b):
            return (SHIP_Y - b["y"]) / max(self.speed, 1.0)

        # threat: a block in my lane reaching the ship row within 0.55 s
        threat = None
        for b in blocks:
            if b["lane"] == self.lane and 0 < t_hit(b) < 0.55:
                if threat is None or t_hit(b) < t_hit(threat):
                    threat = b
        if threat is not None:
            safe = []
            for nl in (self.lane - 1, self.lane + 1):
                if 0 <= nl <= 2:
                    # safe only if nothing in that lane is at the row now or
                    # arriving within 0.8 s (the slide keeps us wide for ~0.3 s)
                    danger = any(b["lane"] == nl and b["y"] < SHIP_Y + 50 and t_hit(b) < 0.8
                                 for b in blocks)
                    if not danger:
                        orb_bonus = any(o["lane"] == nl and o["y"] > 60 for o in orbs)
                        safe.append((0 if orb_bonus else 1, nl))
            if safe:
                safe.sort()
                self._move(safe[0][1])
            return
        # no threat: drift toward the lowest reachable orb whose lane is clear
        chase = None
        for o in orbs:
            if o["lane"] != self.lane and 40 < o["y"] < SHIP_Y - 90:
                # never slide into a lane where a block is in the collision
                # band right now, or arriving within a second
                blocked_path = any(
                    b["lane"] == o["lane"] and (SHIP_Y - 150 < b["y"] < SHIP_Y + 75 or 0 < t_hit(b) < 1.0)
                    for b in blocks)
                if not blocked_path and (chase is None or o["y"] > chase["y"]):
                    chase = o
        if chase is not None:
            self._move(self.lane + (1 if chase["lane"] > self.lane else -1))

    def step(self):
        dt = DT
        self.time += dt
        self.speed = min(MAX_SPEED, START_SPEED + ACCEL * self.time)
        if not self.speedup_flagged and self.speed > 640:
            self.speedup_flagged = True
            self.events.append((self.time, "speedup", None))
        self.score += FLOW_SCORE * dt
        if self.move_cd > 0:
            self.move_cd -= dt
        # ship tween (0.12 s cubic, same as JS)
        if self.ship_t < 1:
            self.ship_t = min(1, self.ship_t + dt / 0.12)
            k = 1 - (1 - self.ship_t) ** 3
            self.ship_from + (LANES[self.lane] - self.ship_from) * k
            self.ship_x = self.ship_from + (LANES[self.lane] - self.ship_from) * k
        self._autopilot()
        self.spawn_t -= dt
        if self.spawn_t <= 0:
            lane = self.rng.randrange(3)
            kind = "orb" if self.rng.random() < ORB_CHANCE else "block"
            self.entities.append({"lane": lane, "y": -60.0, "kind": kind, "got": False, "counted": False})
            self.spawn_t = SPAWN_EVERY
        for e in self.entities:
            prev_y = e["y"]
            e["y"] += self.speed * dt
            if e["kind"] == "block":
                if (abs(e["y"] - SHIP_Y) < (BLOCK_H + 44) / 2 and
                        abs(LANES[e["lane"]] - self.ship_x) < (BLOCK_W + 52) / 2):
                    self.crashed = True
                # near miss: block crosses the ship row in a lane beside the ship
                # just after a dodge (or mid-slide) — reads as a whisker escape
                if not e["counted"] and prev_y < SHIP_Y <= e["y"]:
                    e["counted"] = True
                    if (e["lane"] != self.lane and abs(e["lane"] - self.lane) <= 1
                            and (self.ship_t < 1 or self.time - self.last_dodge < 0.55)):
                        self.events.append((self.time, "close", e["lane"]))
            elif not e["got"]:
                if abs(e["y"] - SHIP_Y) < 52 and abs(LANES[e["lane"]] - self.ship_x) < 56:
                    e["got"] = True
                    self.score += ORB_SCORE
                    self.pops.append({"x": LANES[e["lane"]], "y": e["y"], "t": 0.0, "text": "+%d" % ORB_SCORE})
                    self.events.append((self.time, "orb", e["lane"]))
        self.entities = [e for e in self.entities if e["y"] < H + 80 and not e["got"]]
        for p in self.pops:
            p["t"] += dt
            p["y"] -= 60 * dt
        self.pops = [p for p in self.pops if p["t"] < 0.7]

    def snapshot(self):
        return {
            "time": self.time, "speed": self.speed, "score": int(self.score),
            "ship_x": self.ship_x, "ship_lane": self.lane,
            "entities": [dict(e) for e in self.entities],
            "pops": [dict(p) for p in self.pops],
            "crashed": self.crashed,
        }


def run(duration=24.0, seed=7):
    sim = Sim(seed)
    frames = []
    steps = int(duration * FPS)
    for _ in range(steps):
        sim.step()
        frames.append(sim.snapshot())
        if sim.crashed:
            break
    return sim, frames


if __name__ == "__main__":
    for seed in (7, 11, 3, 21, 5):
        sim, frames = run(24.0, seed)
        orbs = sum(1 for _, k, _ in sim.events if k == "orb")
        closes = sum(1 for _, k, _ in sim.events if k == "close")
        print(f"seed {seed}: crashed={sim.crashed} at t={sim.time:.1f} score={int(sim.score)} orbs={orbs} close={closes} frames={len(frames)}")
