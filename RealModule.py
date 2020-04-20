# coding=gbk
"""ʵ������ʱ��Ҫ��ģ��"""

import time

from pyalgotrade import broker
from pyalgotrade.bar import Bars
from pyalgotrade.barfeed import csvfeed
from pyalgotrade.bar import Frequency
from tqsdk import TqApi
import pandas as pd


class RealBroker(broker.Broker):
    """
    �̳�pyalgotrade�Ļ��࣬��ʵ�ֺ�tqsdk����
    """

    def __init__(self, api: 'TqApi'):
        """
        :param strategy: �������в������Ƶ�list
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
            # !!! ���Բ��������� ����ͬ���Բ�ͬ���������Լ̳�һ����Ȼ�󻻸����֡�
            self.strategy[item[0]] = item[1:]  # ��strategy to  run �еĲ��Զ�Ӧ�� ���ֺͺ�Լ��¼������
            for contract in item[1:]:
                if contract[0] not in self.allTick:
                    self.allTick[contract[0]] = self.api.get_quote(contract[0])

        self.strategyAccount = {}  # �洢һ������ķֲ��Ե��˻���Ϣ
        for item in self.strategy:
            self.strategyAccount[item] = _virtualAccountHelp(realAccount[realAccount.loc[:, 'strategy'] == item])

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
        self.cancelOrderQueue.append(order)

    # ===============================================================
    def start(self):  # pyalgotrade ����abstract methods ��д���ɡ�
        pass

    def stop(self):  # pyalgotrade ����abstract methods ��д���ɡ�
        temp = pd.concat([self.strategyAccount[key] for key in self.strategyAccount.keys()])
        temp.to_csv('currentAccount.csv')

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

        self.cash = self.accountInfo.available
        self.balence = self.accountInfo.balance
        """--------------------------------------------�µ�----------------------------------------------"""
        if self.orderQueue:  # ����������ж�����
            groupbyOrder = {}  # ��һ��dict��װ���ඩ����
            for order in self.orderQueue:
                if order.virContract in groupbyOrder:  # ����dict���Ѿ��������Լ��
                    if order.virDirection == 'Buy' :  # ���������߷��ࡣ
                        groupbyOrder[order.virContract]['long'].append(order)
                    else:
                        groupbyOrder[order.virContract]['short'].append(order)
                else:  # ��û�������Լ
                    groupbyOrder[order.virContract] = {'long': [], 'short': []}  # ��ʼ��Ϊdict Of list , ��Ϊ�������

            for contract in groupbyOrder:  # �Է���õ����ⵥ����ѭ��������û�п��Ի�������ġ�
                if groupbyOrder[contract]['long'] and groupbyOrder[contract]['short']:  # ȷ�����������ǿ�
                    b = 0  # ��ʼ������ָ�룬 ����ȷ����ȥ��������list���Ǹ�λ�á�
                    s = 0
                    while True:
                        if groupbyOrder[contract]['long'][b].volumeLeft == groupbyOrder[contract]['short'][s].volumeLeft:
                            groupbyOrder[contract]['long'][b].is_dead = True  # ���ֱ��������������ȫ��dead��λ�ü�һ
                            groupbyOrder[contract]['short'][s].is_dead = True
                            b += 1
                            s += 1

                        elif groupbyOrder[contract]['long'][b].volumeLeft < groupbyOrder[contract]['short'][s].volumeLeft:
                            groupbyOrder[contract]['long'][b].isdead = True
                            groupbyOrder[contract]['short'][s].volumeLeft = \
                            groupbyOrder[contract]['short'][s].volumeLeft - groupbyOrder[contract]['long'][b].volumeLeft
                            b += 1

                        elif groupbyOrder[contract]['long'][b].volumeLeft < groupbyOrder[contract]['short'][s].volumeLeft:
                            groupbyOrder[contract]['short'][s].isdead = True
                            groupbyOrder[contract]['long'][b].volumeLeft = \
                            groupbyOrder[contract]['long'][b].volumeLeft - groupbyOrder[contract]['short'][s].volumeLeft
                            s += 1

                        else:
                            raise Exception('������۳�������')

                        if b == len(contract['long']) or s == len(contract['short']):
                            break

            for item in groupbyOrder:  # �����µ�
                pos = self.posDict[item]
                availablePos = pos.pos_long - pos.pos_short
                if groupbyOrder[item]['long']:
                    for order in groupbyOrder[item]['long']:
                        if availablePos >= 0:  # Ҫ�򣬳ֲִ���0 �ҿ���
                            res = self.api.insert_order(order.contract, order.direction,
                                                        'OPEN', order.volumeLeft,
                                                        self.allTick[order.virContract]['bid_price1'])
                            order.attach(res)
                            availablePos -= order.volumeLeft
                        elif availablePos < 0:
                            if abs(availablePos) > order.volumeLeft:  # ��Ҫ���׵����������У�����һ��ֱ��ƽ
                                res = self.api.insert_order(order.contract, order.direction,
                                                            'CLOSE', order.volumeLeft,
                                                            self.allTick[order.virContract]['bid_price1'])
                                order.attach(res)
                                availablePos += order.volumeLeft
                            else:
                                res = self.api.insert_order(order.contract, order.direction,
                                                            'CLOSE', abs(availablePos),
                                                            self.allTick[order.virContract]['bid_price1'])
                                res1 = self.api.insert_order(order.contract, order.direction,
                                                             'CLOSE', order.volumeLeft - abs(availablePos),
                                                             self.allTick[order.virContract]['bid_price1'])
                                order.attach(res)
                                order.attach(res1)
                                availablePos = 0

                elif groupbyOrder[item]['short']:
                    for order in groupbyOrder[item]['short']:
                        if availablePos <= 0:  # Ҫ�����ֲ�С��0
                            res = self.api.insert_order(order.contract, order.direction,
                                                        'OPEN', order.volumeLeft,
                                                        self.allTick[order.virContract]['ask_price1'])
                            order.attach(res)
                            availablePos += order.volumeLeft
                        elif availablePos > 0:
                            if availablePos > order.volumeLeft:  # ��Ҫ���׵����������У�����һ��ֱ��ƽ
                                res = self.api.insert_order(order.contract, order.direction,
                                                            'CLOSE', order.volumeLeft,
                                                            self.allTick[order.virContract]['ask_price1'])
                                order.attach(res)
                                availablePos -= order.volumeLeft
                            else:
                                res = self.api.insert_order(order.contract, order.direction,
                                                            'CLOSE', availablePos,
                                                            self.allTick[order.virContract]['ask_price1'])
                                res1 = self.api.insert_order(order.contract, order.direction,
                                                             'CLOSE', order.volumeLeft - availablePos,
                                                             self.allTick[order.virContract]['ask_price1'])
                                order.attach(res)
                                order.attach(res1)
                                availablePos = 0
            self.orderQueue = []  # ���¹��㡣

        """-------------------------------------δ�ɽ���������ʱ���յȴ�10�볷������-----------------------------"""
        if self.unfilledQueue:
            while self.unfilledQueue:
                temp = self.unfilledQueue.pop()
                if not temp.is_dead:
                    if time.time() - temp.time > 10:  # ����10�룬�Ҽ۸������ų�����
                        if temp.direction == 'BUY':
                            if temp.limit_price != self.allTick[temp.instrument_id].bid_price1:
                                self.cancelOrderQueue.append(temp)
                        else:
                            if temp.limit_price != self.allTick[temp.instrument_id].ask_price1:
                                self.cancelOrderQueue.append(temp)
        """--------------------------------------------����--------------------------------------------------------"""
        if self.cancelOrderQueue:  # ��������
            while self.cancelOrderQueue:
                temp = self.cancelOrderQueue.pop()
                for i in temp.realOrder:
                    if not i.is_dead:
                        self.api.cancel_order(i.order_id)
                        self.orderQueue.append(virtualOrder(temp.virDirection, temp.volumeLeft,
                                                            temp.virContract, temp.open))  # �����µ�
        """------------------------------------------���¸��������˻���------------------------------------------"""
        for item in self.strategy:
            temp = {}
            for contract in self.strategy[item]:
                temp[contract] = self.allTick[contract]
            self.strategyAccount[item].update(temp, self.posDict)


class _virtualAccountHelp:
    """
    �������㲻ͬ���Ե�����ֲ�
    """
    generalTickerInfo = pd.read_csv('general_ticker_info.csv')
    def __init__(self, account):
        """
        :param account��ʾ�ӱ����ļ���ȡ��ʱ���ж��ٸ��ֲֳֵ�df
        """
        self.orders = []
        self.account = account
        self.balance = self.account['balance'][0]

    def getCash(self):
        return self.balance - self.account['funds_occupied'].sum()

    def getPosition(self):
        return self.account

    def getEquity(self):
        return self.balance

    def addOrder(self, order: 'virtualOrder'):
        """
        ��¼���µ��µ������order
        :param order:
        :return:
        """
        self.orders.append(order)

    def update(self, allTick: dict, position: dict):
        """
        �������µ�������߳ɽ��������˻�
        :param allTick: ��������Ʒ�ֵ�Tick��dict
        :param position: tqsdk��position�� ��������ÿ����ͬ��Լ�ı�֤��ռ�á�
        :return:
        """
        for i in range(len(self.account)):
            if self.account.loc[i, 'direction'] == 'Buy':
                # ����Ȩ�棬��tick�ı䶯���ϳ��е��������ٳ��Ϻ�Լ������
                self.account['balance'] += \
                    (allTick[self.account.loc[i, 'contract']].last_price - self.account.loc[i, 'prePrice']) \
                    * self.account.loc[i, 'volume'] * allTick[self.account.loc[i, 'contract']].volume_multiple

            elif self.account.loc[i, 'direction'] == 'Sell':
                # ����Ȩ�棬��tick�ı䶯���ϳ��е��������ٳ��Ϻ�Լ������
                self.account['balance'] -= \
                    (allTick[self.account.loc[i, 'contract']].last_price - self.account.loc[i, 'prePrice']) \
                    * self.account.loc[i, 'volume'] * allTick[self.account.loc[i, 'contract']].volume_multiple

            self.account.loc[i, 'prePrice'] = allTick[self.account.loc[i, 'contract']].last_price
            pos = position[self.account.loc[i, 'contract']]
            self.account.loc[i, 'fund occupied'] = \
                pos.margin / (pos.pos_long + pos.pos_short)

        # �������ĸ��¡�����position account ���� position
        for order in self.orders[:]:  # ��ԭlist���п�����������Ϊɾ������index���
            if order.is_dead:
                self.orders.remove(order)
                tempTrade = self.account.groupby(by=['contract', 'direction', 'oldOrNew']).apply(lambda x: x)
                tempStr = str(order.contract) + str(order.direction) + str(order.oldOrNew)
                if tempStr in tempTrade:  # ˵��������ֲ�
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
                self.account['balance'] -= order.fee  # ȥ����ν��׵������ѡ�
                self.account['fee'] += order.fee

class virtualOrder:
    """
    ģ��Ķ����࣬ ��Ϊ�����˻���ʱ���Ǽ������ⵥ����ͬһ��ʵ�̵�������Ҫ��д��
    """
    count = 0  # ������¼���촴���˶��ٶ�������ȷ��ÿ��ʵ����������ظ���id

    def __init__(self, direction, volume, contract, open, oldOrNew='old'):
        """

        :param direction:
        :param volume:
        :param contract:
        :param open: �Ƿ��ǿ���
        :param oldOrNew:  Ĭ����֡�
        """
        self.virDirection = direction
        self.virVolume = volume
        self.virContract = contract
        self.open = open
        self.oldOrNew = oldOrNew
        self.time = time.time()  # ��¼����ʱ��
        self.id = self.count
        self.__volumeLeft = volume  # �ѳɽ�����
        self.__is_dead = False
        self.count += 1

        self.realOrder = []

    def attach(self, order: 'tqsdk order'):
        """
        ������������order��
        :param order: ���������Ӧ��tqsdk�˻��ĵ����п��ܶ�����ⵥ������ͬһ��tqsdk�ĵ��ϡ�
        :return:
        """
        self.realOrder.append(order)

    @property
    def is_dead(self):
        for item in self.realOrder:
            if not item.is_dead:
                self.__is_dead = False
        return self.__is_dead

    @is_dead.setter
    def is_dead(self, value):
        self.__is_dead = value

    @property
    def instrument_id(self):
        return self.virContract

    @property
    def insert_date_time(self):
        return self.time

    @property
    def limit_price(self):
        return self.realOrder[0].limit_price  # �п����ж����ʵ������ �����޼��µ��ļ�Ǯһ��һ����

    @property
    def direction(self):
        return self.virDirection

    @property
    def volumeLeft(self):
        if self.realOrder:
            for item in self.realOrder:
                self.__volumeLeft += item.volume_left
        return self.__volumeLeft

    @volumeLeft.setter
    def volumeLeft(self, value):
        self.__volumeLeft = value

    @property
    def fee(self):
        """��ȡ��һ����������"""
        # TODO �Ժ�������ô���������ѡ�
        return 0

class RealFeed(csvfeed.GenericBarFeed):
    """ģ��pyalgotrade ��feed"""

    def __init__(self):
        super().__init__(Frequency.MINUTE)
        self.allDataSource = {}

    def __getitem__(self, item):
        return self.allDataSource[item]

    def __contains__(self, item):  # �������ж�������ʵ������ in ��ʱ�򴥷����������
        return True if item in self.allDataSource else False

    def addDataSource(self, sourceName, source):
        self.allDataSource[sourceName] = RealSeries(source)

    def keys(self):
        return self.allDataSource.keys()


class RealSeries:
    """ģ��pyalgotrade ��dataSeries"""

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
    """ģ��onBars��Bars"""

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
