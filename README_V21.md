# V21 — Learning Architecture V2

V21 changes how the AI is allowed to learn.

## Core principle
Experience can accumulate quickly. Live behaviour changes slowly.

## Dataset separation
Every validated experience receives a deterministic split:
- 60% TRAIN — discovery
- 20% VALIDATION — test candidate lessons
- 20% HOLDOUT — locked from discovery and reserved for final evaluation

The same experience always receives the same split.

## Multi-dimensional rewards
Completed trades are not reduced to WIN/LOSS. Diagnostic rewards separately grade:
- direction accuracy
- risk discipline
- stop compliance
- entry quality
- profit capture
- holding-time quality
- re-entry recognition
- data integrity

A stopped-out trade can therefore receive positive risk/stop rewards while receiving a negative direction reward.

## Adversarial learning
Candidate lessons are challenged with counterexamples. A lesson is not considered stronger merely because supporting examples exist.

## Counterfactual Lab
Alternative entry delays and hard-stop policies are replayed after the trade using real recorded price paths. These simulations never rewrite historical results.

## Curriculum
Advanced autonomy remains locked until earlier competencies have measurable evidence:
1. Trust the data
2. Protect capital
3. Read direction
4. Manage winners
5. Reversal / re-entry
6. Context intelligence
7. Capital allocation

## Learning Governor
V21 never automatically changes live trading rules. A lesson must survive discovery, validation and adversarial challenge before it can even become HOLDOUT REVIEW ELIGIBLE.

Holdout information is not exposed to discovery engines.
