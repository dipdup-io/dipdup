SELECT add_continuous_aggregate_policy(
    'candlestick_30d',
    start_offset => INTERVAL '30 days',
    end_offset => INTERVAL '0 minutes',
    schedule_interval => INTERVAL '1 day',
    initial_start := '2018-07-01'
);
