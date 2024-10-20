insert into
    holder (
        [address],
        balance,
        turnover,
        tx_count,
        last_seen
    )
values
    (:address, :balance, abs(:balance), 1, :level) on conflict ([address]) do
update
set
    balance = balance + :balance,
    turnover = turnover + abs(:balance),
    tx_count = tx_count + 1,
    last_seen = :level;