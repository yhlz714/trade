# coding=gbk
"""实盘运行时需要的模块"""

import time

from pyalgotrade import broker
from pyalgotrade.bar import Bars
from pyalgotrade.barfeed import csvfeed
from tqsdk import TqApi
import pandas as pd


class RealBroker(broker.Broker):
    """
    继承pyalgotrade的基类，以实现和tqsdk交互
    """

    def __init__(self, api: 'TqApi'):
        """
        :param strategy: 包含所有策略名称的list
        """
        super().__init__()
        self.api = api
        self.accountInfo = self.api.get_account()
        self.posDict = self.api.get_position()
        self.orderQueue = []
        self.unfilledQueue = []
        self.cancelOrderQueue = []
        self.strategy = {}
        self.cash = 0
        self.balence = 0
        self.allTick = {}

        realAccount = pd.read_csv('currentAccount.csv')
        f = open('strategytorun.txt')
        temp = f.readlines()
        f.close()

        for item in temp:
            item = eval(item)
            # !!! 策略不可重名， 如需同策略不同参数，可以继承一个，然后换个名字。
            self.strategy[item[0]] = item[1:]  # 将strategy to  run 中的策略对应的 名字和合约记录下来。
            for contract in item[1:]:
                if contract[0] not in self.allTick:
                    self.allTick[contract[0]] = self.api.get_quote(contract[0])

        self.strategyAccount = {}  # 存储一个虚拟的分策略的账户信息
        for item in self.strategy:
            self.strategyAccount[item] = _virtualAccountHelp(realAccount[realAccount.loc['strategy'] == item])

    def getInstrumentTraits(self, instrument):
        pass

    def getCash(self, includeShort=True, strategyName=None):
        """
        Returns the available cash.

        :param includeShort: Include cash from short positions.
        :type includeShort: boolean.
        """
        return self.strategyAccount[strategyName].getCash()

    def getShares(self, instrument, strategyName=None):
        """Returns the number of shares for an instrument."""
        pass

    def getPositions(self, strategyName=None):
        """Returns a dictionary that maps instruments to shares."""
        return self.strategyAccount[strategyName].getPosition()

    def getEquity(self, strategyName=None):
        """获取虚拟持仓的权益"""
        return self.strategyAccount[strategyName].getPosition()

    def getActiveOrders(self, instrument=None):
        """Returns a sequence with the orders that are still active.

        :param instrument: An optional instrument identifier to return only the active orders for the given instrument.
        :type instrument: string.
        """
        pass

    def submitOrder(self, order: 'virtualOrder'):
        """Submits an order.
        :param order: The order to submit.
        :type order: :class:`Order`.
        """
        self.orderQueue.append(order)

    def creatOrder(self, direction, volume, contract, openOrClose):
        """创建新的订单类"""
        return virtualOrder(direction, volume, contract, open=openOrClose, oldOrNew='new')

    def createMarketOrder(self, action, instrument, quantity, strategyNmae=None, onClose=False):
        """Creates a Market order.
        A market order is an order to buy or sell a stock at the best available price.
        Generally, this type of order will be executed immediately. However, the price at which a market order will be executed
        is not guaranteed.

        :param strategyNmae: 使用这个策略的名字来下单
        :param action: The order action.
        :type action: Order.Action.BUY, or Order.Action.BUY_TO_COVER, or Order.Action.SELL or Order.Action.SELL_SHORT.
        :param instrument: Instrument identifier.
        :type instrument: string.
        :param quantity: Order quantity.
        :type quantity: int/float.
        :param onClose: True if the order should be filled as close to the closing price as possible (Market-On-Close order). Default is False.
        :type onClose: boolean.
        :rtype: A :class:`MarketOrder` subclass.
        """
        pass

    def createLimitOrder(self, action, instrument, limitPrice, quantity):
        """Creates a Limit order.
        A limit order is an order to buy or sell a stock at a specific price or better.
        A buy limit order can only be executed at the limit price or lower, and a sell limit order can only be executed at the
        limit price or higher.

        :param action: The order action.
        :type action: Order.Action.BUY, or Order.Action.BUY_TO_COVER, or Order.Action.SELL or Order.Action.SELL_SHORT.
        :param instrument: Instrument identifier.
        :type instrument: string.
        :param limitPrice: The order price.
        :type limitPrice: float
        :param quantity: Order quantity.
        :type quantity: int/float.
        :rtype: A :class:`LimitOrder` subclass.
        """
        raise NotImplementedError()

    def createStopOrder(self, action, instrument, stopPrice, quantity):
        """Creates a Stop order.
        A stop order, also referred to as a stop-loss order, is an order to buy or sell a stock once the price of the stock
        reaches a specified price, known as the stop price.
        When the stop price is reached, a stop order becomes a market order.
        A buy stop order is entered at a stop price above the current market price. Investors generally use a buy stop order
        to limit a loss or to protect a profit on a stock that they have sold short.
        A sell stop order is entered at a stop price below the current market price. Investors generally use a sell stop order
        to limit a loss or to protect a profit on a stock that they own.

        :param action: The order action.
        :type action: Order.Action.BUY, or Order.Action.BUY_TO_COVER, or Order.Action.SELL or Order.Action.SELL_SHORT.
        :param instrument: Instrument identifier.
        :type instrument: string.
        :param stopPrice: The trigger price.
        :type stopPrice: float
        :param quantity: Order quantity.
        :type quantity: int/float.
        :rtype: A :class:`StopOrder` subclass.
        """
        pass

    def createStopLimitOrder(self, action, instrument, stopPrice, limitPrice, quantity):
        """Creates a Stop-Limit order.
        A stop-limit order is an order to buy or sell a stock that combines the features of a stop order and a limit order.
        Once the stop price is reached, a stop-limit order becomes a limit order that will be executed at a specified price
        (or better). The benefit of a stop-limit order is that the investor can control the price at which the order can be executed.

        :param action: The order action.
        :type action: Order.Action.BUY, or Order.Action.BUY_TO_COVER, or Order.Action.SELL or Order.Action.SELL_SHORT.
        :param instrument: Instrument identifier.
        :type instrument: string.
        :param stopPrice: The trigger price.
        :type stopPrice: float
        :param limitPrice: The price for the limit order.
        :type limitPrice: float
        :param quantity: Order quantity.
        :type quantity: int/float.
        :rtype: A :class:`StopLimitOrder` subclass.
        """
        pass

    def cancelOrder(self, order):
        """Requests an order to be canceled. If the order is filled an Exception is raised.
        :param order: The order to cancel.
        :type order: :class:`Order`.
        """
        self.cancelOrderQueue.append(order)

    # ===============================================================
    def start(self):  # pyalgotrade 中有abstract methods 非写不可。
        pass

    def stop(self):  # pyalgotrade 中有abstract methods 非写不可。
        pass
        # TODO 将各个虚拟账户的持仓重新整理然后写入csv

    def join(self):  # pyalgotrade 中有abstract methods 非写不可。
        pass

    def eof(self):  # pyalgotrade 中有abstract methods 非写不可。
        pass

    def dispatch(self):  # pyalgotrade 中有abstract methods 非写不可。
        pass

    def peekDateTime(self):  # pyalgotrade 中有abstract methods 非写不可。
        pass

    def update(self):
        """每一个Onbar循环最后来处理这个时间点所有的需要更新的任务，比如更新虚拟账户的情况，订单报单等。"""

        self.cash = self.accountInfo.available
        self.balence = self.accountInfo.balance
        # TODO 完成 pass的内容。 需要考虑怎么将真实的订单和虚拟的订单进行映射的问题。
        if self.orderQueue:  # 如果队列中有订单。
            pass

        if self.unfilledQueue:  # 未成交处理。先暂时按照等待10秒撤单处理。
            while self.unfilledQueue:
                temp = self.unfilledQueue.pop()
                if not temp.is_dead:
                    if time.time() - temp.time > 10:  # 大于10秒，且价格不是最优撤单。
                        if temp.direction == 'BUY':
                            if temp.limit_price != self.allTick[temp.instrument_id].bid_price1:
                                self.cancelOrderQueue.append(temp)
                        else:
                            if temp.limit_price != self.allTick[temp.instrument_id].ask_price1:
                                self.cancelOrderQueue.append(temp)

        if self.cancelOrderQueue:  # 撤单处理。
            while self.cancelOrderQueue:
                temp = self.cancelOrderQueue.pop()
                for i in temp.realOrder:
                    if not i.is_dead:
                        self.api.cancel_order(i.order_id)

        for item in self.strategy:  # 更新各个虚拟账户。
            temp = {}
            for contract in self.strategy[item]:
                temp[contract] = self.allTick[contract]
            self.strategyAccount[item].update(temp)


class _virtualAccountHelp:
    """
    帮助计算不同策略的虚拟持仓
    """

    def __init__(self, account):
        """
        :param account表示从本地文件读取的时候有多少各种持仓的df
        """
        self.orders = []
        self.account = account
        self.equity = self.account['equity'][0]
        self.cash = self.equity - self.account['funds_occupied'].sum()

    def getCash(self):
        return self.cash

    def getPosition(self):
        return self.account

    def getEquity(self):
        return self.equity

    def addOrder(self, order: 'virtualOrder'):
        """
        记录最新的下单情况的order
        :param order:
        :return:
        """
        self.orders.append(order)

    def update(self, allTick: dict):
        """
        根据最新的行情或者成交来更新账户
        :param allTick: 包含所有品种的Tick的dict
        :return:
        """
        # TODO 还没写完， 需要update cash equity
        # 处理订单的更新。更新position
        for order in self.orders[:]:  # 对原list进行拷贝，避免因为删除导致index溢出

            if order.is_dead:
                self.orders.remove(order)
                tempTrade = self.account.groupby(by=['contract', 'direction', 'oldOrNew']).apply(lambda x: x)
                tempStr = str(order.contract) + str(order.direction) + str(order.oldOrNew)
                if tempStr in tempTrade:  # 说明有这个持仓
                    if order.open:
                        tempTrade['volume'] += order.volume  # 将这个数量加上即可
                    else:  # 平仓
                        if order.volume < tempTrade['volume']:
                            tempTrade['volume'] -= order.volume
                        elif order.volume == tempTrade['volume']:
                            tempTrade.drop(tempStr, inplace=True)
                        else:
                            raise Exception('平仓数量超过已有持仓，请检查！')
                    self.account = tempTrade.reset_index()
                else:
                    self.account.loc[len(self.account), ['direction', 'volume', 'contract']] = \
                        [order.direction, order.volume, order.contract]


class virtualOrder:
    """
    模拟的订单类， 因为虚拟账户有时候是几个虚拟单发成同一个实盘单，所以要重写。
    """

    def __init__(self, direction, volume, contract, open, oldOrNew='old'):
        """

        :param direction:
        :param volume:
        :param contract:
        :param open: 是否是开仓
        :param oldOrNew:  默认昨仓。
        """
        self.virDirection = direction
        self.virVolume = volume
        self.virContract = contract
        self.open = open
        self.oldOrNew = oldOrNew
        self.time = time.time()  # 记录创建时间

        self.realOrder = []

    def attach(self, order: 'tqsdk order'):
        """
        关联到真正的order上
        :param order: 和这个单对应的tqsdk账户的单，有可能多个虚拟单关联到同一个tqsdk的单上。
        :return:
        """
        self.realOrder.append(order)

    @property
    def is_dead(self):
        dead = True
        for item in self.realOrder:
            if not item.is_dead:
                dead = False
        return dead

    @property
    def instrument_id(self):
        return self.virContract

    @property
    def insert_date_time(self):
        return self.time

    @property
    def limit_price(self):
        return self.realOrder[0].limit_price  # 有可能有多个真实订单， 但是限价下单的价钱一定一样。

    @property
    def direction(self):
        return self.virDirection


class RealFeed:
    """模拟pyalgotrade 的feed"""

    def __init__(self):
        self.allDataSource = {}

    def __getitem__(self, item):
        return self.allDataSource[item]

    def addDataSource(self, contract, source):
        self.allDataSource[contract] = RealSeries(source)


class RealSeries:
    """模拟pyalgotrade 的dataSeries"""

    def __init__(self, source: 'pd.DataFrame'):
        self.data = source

    def getPriceDataSeries(self):
        return self.data['close']

    def getLowDataSeries(self):
        return self.data['low']

    def getHighDataSeries(self):
        return self.data['high']

    def getCloseDataSeries(self):
        return self.data['close']


class RealBars:
    """模拟onBars的Bars"""

    def __init__(self):
        self.__data = {}

    def getInstruments(self):
        return self.__data.keys

    def getDateTime(self):
        return self.getBar(list(self.getInstruments())[0]).getDateTime()

    def getBar(self, instrument):
        return self.__data[instrument]

    def setValue(self, value: 'dict of pd.Series'):
        for item in value:
            self.__data[item] = RealBar()
            self.__data[item].set(value[item])


class RealBar:

    def __init__(self):
        self.__data = pd.Series()

    def getClose(self):
        return self.__data['close']

    def getDataTime(self):
        return self.__data['datetime']

    def set(self, value: 'pd.Series'):
        self.__data = value
