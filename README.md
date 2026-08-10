# Crypto Intelligence Terminal V12.1.0 — Trade Replay & Learning

V12.1 makes the Performance Lab useful for human review without exposing the entire engine.

Each completed trade can now show:

- a price replay from before entry through the period after exit
- entry, exit and first fresh re-entry-evidence markers
- why the AI entered, in plain English
- why it exited
- what happened after the exit
- what the engine learned
- the AI decision-state path as conditions changed
- the best same-direction move available after exit
- the approximate value of that move on the original paper capital

The replay is reconstructed from records the platform actually captured. It does not invent
historical prices. Legacy trades with insufficient history clearly say so.

The V12 learning engine remains sample-gated. Trade Replay improves evidence quality; it does
not allow hindsight to automatically rewrite trading rules.
