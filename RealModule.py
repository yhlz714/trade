# coding=gbk
"""ʵ������ʱ��Ҫ��ģ��"""

from pyalgotrade import broker
from tqsdk import TqApi
import pandas as pd

class RealBroker(broker.Broker):
    """
    �̳�pyalgotrade�Ļ��࣬��ʵ�ֺ�tqsdk����
    """

    def __init__(self):
        """

        :param strategy: �������в������Ƶ�list
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
        self.strategyAccount = {}  # �洢һ������ķֲ��Ե��˻���Ϣ
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
        """��ȡ����ֲֵ�Ȩ��"""
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
        """�����µĶ�����"""
        return virtualOrder(direction, volume, contract, open=openOrClose, oldOrNew='new')

    def createMarketOrder(self, action, instrument, quantity, strategyNmae=None, onClose=False):
        """Creates a Market order.
        A market order is an order to buy or sell a stock at the best available price.
        Generally, this type of order will be executed immediately. However, the price at which a market order will be executed
        is not guaranteed.

        :param strategyNmae: ʹ��������Ե��������µ�
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
    def start(self):  # pyalgotrade ����abstract methods ��д���ɡ�
        pass

    def stop(self):  # pyalgotrade ����abstract methods ��д���ɡ�
        pass
        # TODO �����������˻��ĳֲ���������Ȼ��д��csv

    def join(self):  # pyalgotrade ����abstract methods ��д���ɡ�
        pass

    def eof(self):  # pyalgotrade ����abstract methods ��д���ɡ�
        pass

    def dispatch(self):  # pyalgotrade ����abstract methods ��д���ɡ�
        pass

    def peekDateTime(self):  # pyalgotrade ����abstract methods ��д���ɡ�
        pass

    def update(self):
        """ÿһ��Onbarѭ��������������ʱ������е���Ҫ���µ����񣬱�����������˻�����������������ȡ�"""


class _virtualAccountHelp:
    """
    �������㲻ͬ���Ե�����ֲ�
    """
    def __init__(self, account):
        """
        :param account��ʾ�ӱ����ļ���ȡ��ʱ���ж��ٸ��ֲֳֵ�df
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
        ��¼���µ��µ������order
        :param order:
        :return:
        """
        self.orders.append(order)

    def update(self, allTick: dict):
        """
        �������µ�������߳ɽ��������˻�
        :param allTick: ��������Ʒ�ֵ����¼�
        :return:
        """
        for order in self.orders[:]: # ��ԭlist���п�����������Ϊɾ������index���

            if order.is_dead:
                self.orders.remove(order)
                tempTrade = self.account.groupby(by=['contract', 'direction', 'oldOrNew']).apply(lambda x:x)
                tempStr = str(order.contract) + str(order.direction) +str(order.oldOrNew)
                if tempStr in tempTrade: # ˵��������ֲ�
                    if order.open:
                        tempTrade['volume'] += order.volume  # ������������ϼ���
                    else:  # ƽ��
                        if order.volume < tempTrade['volume']:
                            tempTrade['volume'] -= order.volume
                        elif order.volume == tempTrade['volume']:
                            tempTrade.drop(tempStr, inplace=True)
                        else:
                            raise Exception('ƽ�������������гֲ֣����飡')
                    self.account = tempTrade.reset_index() 
                else:
                    self.account.loc[len(self.account), ['direction', 'volume', 'contract']] = \
                    [order.direction, order.volume, order.contract]


class virtualOrder:
    """
    ģ��Ķ����࣬ ��Ϊ�����˻���ʱ���Ǽ������ⵥ����ͬһ��ʵ�̵�������Ҫ��д��
    """
    def __init__(self, direction, volume, contract, open, oldOrNew='old'):
        """

        :param direction:
        :param volume:
        :param contract:
        :param open:
        :param oldOrNew:  Ĭ����֡�
        """
        self.direction = direction
        self.volume =volume
        self.contract = contract
        self.open = open
        self.oldOrNew = oldOrNew

    def attach(self, order: 'tqsdk order'):
        """
        ������������order��
        :param order: ���������Ӧ��tqsdk�˻��ĵ����п��ܶ�����ⵥ������ͬһ��tqsdk�ĵ��ϡ�
        :return:
        """
        self.realOrder = order

    @property
    def is_dead(self):
        return self.realOrder.is_dead # ����tqsdk�����Ƿ���ᡣ

    @property
    def instrument_id(self):
        return self.realOrder.instrument_id
