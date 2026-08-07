# Crypto Intelligence Terminal V11.0.0

## Investment Committee Foundation

V11 adds a behind-the-scenes Investment Committee. The visible interface remains
simple. The committee analyses every asset before the Portfolio Manager may allocate
capital.

### Committee members

- Technical Analyst
- Volume and Liquidity Analyst
- Momentum Analyst
- News and Fundamental Analyst
- Macro and Market Regime Analyst
- Risk Manager
- Portfolio Fit Analyst

### Decision discipline

The Portfolio Manager no longer opens Core or Swing positions from the hourly signal
alone.

A trade must have:

- agreement from several independent analyst groups
- direction aligned with the hourly signal
- sufficient evidence strength
- no Risk Manager veto
- acceptable portfolio concentration
- the correct permission for Core or Swing

Core requires the strongest alignment and remains Long-only. Swing may take qualified
Long or Short opportunities.

### Learning

Every new position stores the full committee snapshot available at entry. After trades
close, the committee learning file measures which analyst conditions were associated
with positive or negative expectancy. Committee weights are never changed automatically.

### Interface

No new front-line page was added. Committee output is stored behind the scenes in:

- data/committee_latest.json
- data/committee_history.json
- data/committee_learning.json
- data/engine_health.json

### Upload

1. Extract the ZIP.
2. Upload all extracted files and folders over the current repository.
3. Commit.
4. Reboot Streamlit.
5. Run Hourly Signal Recorder once.
6. Review the workflow log for `investment_committee.py`.
