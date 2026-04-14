# Atlas — Backtesting Platform

Atlas is Acme Analytics' backtesting platform. It runs strategies against historical tick data with a proprietary slippage model and venue-specific fee schedules.

## Slippage model

The Atlas slippage model was calibrated on 6 years of tick data (2018-2023) across 11 venues. It accounts for:

1. Order-book depth at the moment of submission
2. Historical cancellation rate for similar orders
3. Venue-specific rebate / take fees
4. Known latency between decision and execution

On out-of-sample 2024 data, the model's predicted fill prices are within **2.3 basis points** of actual fills on average.

## Execution modes

- **Vector backtest** — fast, assumes instantaneous fills at mid. Use for strategy prototyping.
- **Event-driven backtest** — realistic, replays the full order book. Use for final validation before paper trading.
- **Paper trading** — hooks Atlas into Pulse's live feed and simulates fills in real time.

## Typical benchmarks

A one-year event-driven backtest over 500 symbols at 1-minute granularity completes in ~8 minutes on a single 16-core machine.
