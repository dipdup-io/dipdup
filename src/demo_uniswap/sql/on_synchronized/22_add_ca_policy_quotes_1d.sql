SELECT add_continuous_aggregate_policy(
    'candlestick_1d',
    start_offset => INTERVAL '2 days',
    end_offset => INTERVAL '0 minutes',
    schedule_interval => INTERVAL '1 hour',
    initial_start := '2018-07-01'
);
