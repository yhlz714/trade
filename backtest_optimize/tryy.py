#!/usr/bin/env python
#  -*- coding: utf-8 -*-
import time

from tqsdk import TqApi, TqAccount

api = TqApi(TqAccount('快期模拟', 'yhlz714', '86888196'), web_gui=True)
# 获得 m2005 的持仓引用，当持仓有变化时 position 中的字段会对应更新
position = api.get_position("SHFE.rb2010")
# 获得资金账户引用，当账户有变化时 account 中的字段会对应更新
account = api.get_account()
# 下单并返回委托单的引用，当该委托单有变化时 order 中的字段会对应更新
# order = api.insert_order(symbol="SHFE.rb2010", direction="BUY", offset="OPEN", volume=5, limit_price=3575)
orders = api.get_order()
for i in orders:
    api.cancel_order(orders[i])
count = 0
while True:

    api.wait_update()
    # if api.is_changing(order, ["status", "volume_orign", "volume_left"]):
    #     print("单状态: %s, 已成交: %d 手" % (order.status, order.volume_orign - order.volume_left))
    # print(order.status)
    if api.is_changing(position, "pos_long_today"):
        print("今多头: %d 手" % (position.pos_long_today))
    if api.is_changing(account, "available"):
        print("可用资金: %.2f" % (account.available))
    count += 1
    if 50 < count < 52:
        pass
        # api.cancel_order(order)