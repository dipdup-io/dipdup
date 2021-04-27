from tortoise import Model, fields


class Event(Model):
    id = fields.IntField(pk=True)
    bets_against_sum = fields.BigIntField()
    bets_close_time = fields.DatetimeField()
    bets_for_sum = fields.BigIntField()
    closed_dynamics = fields.IntField()
    closed_oracle_time = fields.DatetimeField()
    closed_rate = fields.IntField()
    closed_time = fields.DatetimeField()
    created_time = fields.DatetimeField()
    currency_pair = fields.CharField(255)
    expiration_fee = fields.BigIntField()
    is_bets_for_win = fields.BooleanField()
    is_closed = fields.BooleanField()
    is_measurement_started = fields.BooleanField()
    liquidity_percent = fields.IntField()
    liquidity_sum = fields.BigIntField()
    measure_oracle_start_time = fields.DatetimeField()
    measure_period = fields.BigIntField()
    measure_start_fee = fields.BigIntField()
    measure_start_time = fields.DatetimeField()
    oracle_address = fields.CharField(36)
    start_rate = fields.IntField()
    target_dynamics = fields.IntField()


class Bet(Model):
    id = fields.IntField(pk=True)
    bet_against = fields.BigIntField()
    bet_for = fields.BigIntField()
    event = fields.ForeignKeyField('models.Event')
