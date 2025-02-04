ИНСТРУКЦИЯ

Логинитесь телеграмм аккаунтом на https://my.telegram.org/auth. 

В разделе API получается ApiID и HashID. Выглядят они вот так: 20147527, 82b52527124nv125se7e8b1ca79de0bf7

В data/telegram_accounts.txt вставляете данные от одного аккаунта в одну строчку в таком формате:

номер:пароль_тг_аккаунта:api_id:hash_id Пример: 12124567890:qwerty123:20147527:82b52527164nv125se7e8b1ca79de0bf7

Если пароля нету, то просто пишите в том месте pass. Пример: 12124567890:pass:20147527:82b52527624nv125se7e8b1ca79de0bf7

После того как выставите настройки в конфиге, используйте функцию 4. Generate instructions чтобы сгенерить трейды.
Затем функция 2. Start trading чтобы начать торговлю. 

Кошельки должны быть пополненны USDC на Perps. 


CONFIG.PY настройки:

- TIME_RANGE = [10, 30]  #- пауза между трейдами 

- VOLUME_RANGE = [16, 25] #- объем трейда

- AMOUNT_MULTIPLIER_RANGE = [0.9, 1.1] #- множитель объема для встречного трейда

- TRADES_COUNT_RANGE = [3, 5] #- количество трейдов в одной инструкции

- LEVERAGE = 1 #- кредитное плечо

"""
!!!ОПИСАНИЕ ПАРАМЕТРА DISPERSION_RANGE_PERCENT:

Этот параметр определяет допустимое отклонение в размере встречных позиций для разных аккаунтов.

Пример использования:
- Если первый аккаунт открывает SHORT позицию на 1000 USDT
- То второй аккаунт откроет LONG позицию на сумму, которая будет отличаться в пределах заданного диапазона

При текущих настройках [-0.01, 0.01] (±1%):
- Для позиции в 1000 USDT
- Встречная позиция будет в диапазоне 990-1010 USDT

Это небольшое различие в размерах позиций для того, чтобы не задетеклили как бота.
"""

DISPERSION_RANGE_PERCENT = [-0.01, 0.01]

