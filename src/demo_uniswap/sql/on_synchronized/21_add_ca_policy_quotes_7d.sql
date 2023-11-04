SELECT add_continuous_aggregate_policy(
    'candlestick_7d',
    start_offset => INTERVAL '7 days',
    end_offset => INTERVAL '0 minutes',
    schedule_interval => INTERVAL '1 day',
    initial_start := '2018-07-01'
);
