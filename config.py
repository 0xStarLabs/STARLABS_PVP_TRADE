CYCLE_MODE = False

BETWEEN_OPEN_CLOSE_TRADE_TIME_RANGE = [10, 30]  #- пауза между открытием и закрытием трейда
BETWEEN_CLOSE_NEXT_TRADE_TIME_RANGE = [10, 20] #- пауза между закрытием и открытием следующего трейда
BETWEEN_ACCOUNTS_IN_ONE_TRADE_PAUSE_RANGE = [1, 3] #- пауза между аккаунтами в одном трейде
PAUSE_BETWEEN_TRADE_SIDES = [10, 20] #- пауза между запуском сторон в одном трейде
VOLUME_RANGE = [16, 25] #- объем трейда

AMOUNT_MULTIPLIER_RANGE = [0.9, 1.1] #- множитель объема для встречного трейда
TRADES_COUNT_RANGE = [1, 2] #- количество трейдов в одной инструкции
LEVERAGE = 1 #- кредитное плечо


"""
!!!ОПИСАНИЕ ПАРАМЕТРА DISPERSION_RANGE_PERCENT:

Этот параметр определяет допустимое отклонение в размере встречных позиций для разных аккаунтов.

Пример использования:
- Если первый аккаунт открывает SHORT позицию на 1000 USDT
- То второй аккаунт откроет LONG позицию на сумму, которая будет отличаться в пределах заданного диапазона

При текущих настройках [-0.01, 0.01] (±1%):
- Для позиции в 1000 USDT
- Встречная позиция будет в диапазоне 990-1010 USDT

Это небольшое различие в размерах позиций для того чтобы не побрили, если вы делаете одновременно два сделки
pvp то можно поставить [0, 0] и тогда ваши позиции будут одинаковыми по сумме
"""
DISPERSION_RANGE_PERCENT = [-0.01, 0.01]

TICKERS = [
            #   "ETH",
            #   "BTC",
            #   "SOL",
            #   "DOGE",
              "HYPE"
]   

# Maximum allowed imbalance in account distribution (in percentage of total accounts)
# Example: 0.2 means the split can be up to 20% uneven (for 10 accounts: 4-6, 3-7 splits are possible)
# but the volume of the 3 will be approximately equal to the volume of the 7
ACCOUNT_DISTRIBUTION_IMBALANCE = 0.2  # 20% maximum imbalance

MIN_VOLUME_PER_ACCOUNT = 15  # Minimum volume allowed per account

