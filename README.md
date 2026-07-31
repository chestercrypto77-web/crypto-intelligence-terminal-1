# Crypto Intelligence Terminal V5.4.1

Objective-signals update built directly from the official V5.4.0 release.

## Changes

- Removed the 4H Intelligence score and confidence percentage from view
- Replaced them with fixed-rule, colour-coded arrows
- Added separate price direction, RVOL change, current RVOL and volume-flow fields
- Green up: price and volume rising together
- Red down: volume rising while price falls
- Blue up: volume rising before price direction is clear
- Orange down: price rising while volume fades
- Yellow or grey: mixed, falling or stable activity
- Narrative ordering now uses observed volume-flow counts and RVOL change
- Removed visible health, attention and opportunity scores from the main pages
- Rebuilt the Research matrix around observable price, volume, RVOL and portfolio-weight data
- Existing holdings, navigation and Signal Lab remain available

## Upload

Extract the ZIP, drag all five extracted items into GitHub **Add file → Upload files**, commit the replacements, then reboot Streamlit.
