# V16 — Trading Desk 2.0 / AI Operations Centre

Trading Desk now answers the important live-management questions first:

- how many positions are open
- how much capital is working
- how much cash is waiting
- rule-based planned maximum loss
- current open P/L
- estimated profit already protected by current wallet rules
- each trade's current mission and health

Every active position receives a connected case file. The case file combines the current wallet, fresh Observer/microstructure price, Risk Guardian, Investment Committee, Winner School and Failure School.

The 15-minute Observer records a bounded chronological management thought history for every active trade. When a position closes, Performance Lab's trade review inherits that thought history so later learning can inspect how the engine's mission and evidence changed while the trade was alive.

Risk/protected-profit values are labelled as rule-based estimates. They are not guaranteed execution values and do not assume perfect fills.

Winner School similarity is descriptive historical matching, not a forecast or probability of profit.
