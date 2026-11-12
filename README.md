# Roblox Up-and-Coming Top 10 Forecaster

Predicts which Roblox games will hold each of the top 10 places on the Up-and-Coming chart over the next 3 days.

## Strategy

**Empirical transition model:** Learns P(next_rank | current_rank) from 34 historical snapshots. Rank #1 is very stable (76% stay rate), while ranks #8-10 are volatile.

**Momentum:** Games climbing the chart get a boost for higher places; falling games get a boost for lower places. Recent trend (last 3 snapshots) matters more than long-term history.

**Player growth:** Games with rapidly growing player counts are more likely to climb. Note: absolute player count does NOT correlate with rank — the chart ranks by growth rate, not size.

**Stability:** Games that have held a rank for multiple consecutive snapshots get higher probability to stay there.

**Honest probabilities:** Top probability capped at 0.55 (3-day forecast has real uncertainty). 15% left unnamed for games outside the top 20 candidates. Each place's probabilities sum to ~0.85, with the rest distributed among unnamed games.

## Output

Writes `/output/forecast.json` with:
- `probabilities`: list of {universe_id, place, p} — probability each game holds each place
- `top10`: ordered list of 10 universe_ids — best guess at the top 10

## Files

- `main.py` — the forecaster (Python 3.13, stdlib only)
- `README.md` — this file
- `LICENSE` — MIT license
