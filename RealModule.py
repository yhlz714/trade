# coding=gbk
"""实盘运行时需要的模块"""

from pyalgotrade import broker
from tqsdk import TqApi
import pandas as pd

class RealBroker(broker.Broker):
    """
    继承pyalgotrade的基类，以实现和tqsdk交互
    """

    def __init__(self):
        """

        :param strategy: 包含所有策略名称的list
        """
        super().__init__()
        realAccount = pd.read_csv('currentAccount.csv')
        f = open('strategytorun.txt')
        temp = f.readlines()
        f.close()
        self.orderQueue = []
        self.strategy = []
        for item in temp:
            self.strategy.append(item[0])
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
        pass

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
        :param allTick: 包含所有品种的最新价
        :return:
        """
        for order in self.orders[:]: # 对原list进行拷贝，避免因为删除导致index溢出

            if order.is_dead:
                self.orders.remove(order)
                tempTrade = self.account.groupby(by=['contract', 'direction', 'oldOrNew']).apply(lambda x:x)
                tempStr = str(order.contract) + str(order.direction) +str(order.oldOrNew)
                if tempStr in tempTrade: # 说明有这个持仓
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
        :param open:
        :param oldOrNew:  默认昨仓。
        """
        self.direction = direction
        self.volume =volume
        self.contract = contract
        self.open = open
        self.oldOrNew = oldOrNew

    def attach(self, order: 'tqsdk order'):
        """
        关联到真正的order上
        :param order: 和这个单对应的tqsdk账户的单，有可能多个虚拟单关联到同一个tqsdk的单上。
        :return:
        """
        self.realOrder = order

    @property
    def is_dead(self):
        return self.realOrder.is_dead # 返回tqsdk订单是否完结。

    @property
    def instrument_id(self):
        return self.realOrder.instrument_id
