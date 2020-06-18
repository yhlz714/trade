# coding=gbk
"""ʵ������ʱ��Ҫ��ģ��"""
# TODO ���²��ԣ��ҵ��˲�ͣ�µ���ԭ������Ϊ�����󶩵��ҵ���Ҫ�ȴ�����wait_update().��Ҫ���������Ƿ������ҳ�����
# TODO �µ������ɵ����ⶩ��û�й����������˻�����realBroker��update�������档
import time
import logging

from pyalgotrade.broker import backtesting
from pyalgotrade.bar import Bars
from pyalgotrade.barfeed import csvfeed
from pyalgotrade.bar import Frequency
from tqsdk import TqApi
import pandas as pd
pd.set_option('display.max_columns', None)
logger = logging.getLogger('Yhlz')

class RealBroker(backtesting.Broker):
    """
    �̳�pyalgotrade�Ļ��࣬��ʵ�ֺ�tqsdk����
    """

    def __init__(self, api: 'TqApi', position=None, allTick=None, strategy=None):
        """
        :param strategy: �������в������Ƶ�list
        strategy��alltick��Ҫһ�𴫣������ǵ���û�У���Ҫ���¶�ȡ
        """
        feed = RealFeed()
        super().__init__(10000, feed)
        self.api = api
        self.accountInfo = self.api.get_account()
        if position:
            self.posDict = position
        else:
            self.posDict = self.api.get_position()

        self.orderQueue = []
        self.unfilledQueue = []
        self.cancelOrderQueue = []
        self.reInsertQueue = []
        self.strategy = {}  # ������е�strategy
        self.strategyNow = None  # �������ʱ��onbars���е�strategy����RealBroker��ʵ���п����޸����ֵ��������ʾ�ڲ���ʱ���еĲ���
        self.cash = 0
        self.balence = 0
        if not allTick or not strategy:
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
                        # �����ָ����Լ��ô�Ѷ�Ӧ��������ԼҲ�����ϡ�
                        if 'KQ.i' in contract[0] and contract[0].replace('KQ.i', 'KQ.m') not in self.allTick:
                            self.allTick[contract[0].replace('KQ.i', 'KQ.m')] = \
                                self.api.get_quote(contract[0].replace('KQ.i', 'KQ.m'))
                            self.allTick[self.allTick[contract[0].replace('KQ.i', 'KQ.m')].underlying_symbol] = \
                                self.allTick[contract[0].replace('KQ.i', 'KQ.m')]
        else:
            self.allTick = allTick
            self.strategy = strategy

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
        logger.debug('�ֽ���' + str(self.strategyAccount[strategyName].getCash()))
        return self.strategyAccount[strategyName].getCash()

    def getShares(self, instrument, strategyName=None):
        """Returns the number of shares for an instrument."""
        if strategyName==None:
            strategyName = type(self.strategyNow).__name__  # ��ȡʵ��������
        return self.getPositions(strategyName).loc[:, 'volume'].sum()  # ����һ���Զ�ղּ����˵�������

    def getPositions(self, strategyName=None):
        """Returns a dictionary that maps instruments to shares."""
        if strategyName==None:
            strategyName = type(self.strategyNow).__name__  # ��ȡʵ��������
        logger.debug('�ֲ���' + str(self.strategyAccount[strategyName].getPosition()))
        return self.strategyAccount[strategyName].getPosition()

    def getEquity(self, strategyName=None):
        """��ȡ����ֲֵ�Ȩ��"""
        if strategyName==None:
            strategyName = type(self.strategyNow).__name__  # ��ȡʵ��������
        logger.debug('Ȩ���ǣ� ' + str(self.strategyAccount[strategyName].getPosition()))
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
        self.strategyAccount[type(self.strategyNow).__name__].addOrder(order)  # �������˻����¶�����
        self.orderQueue.append(order)  # ��ʵ�ʶ��������������Ӷ�������

    def creatOrder(self, direction, volume, contract, open, strategyName=None, price=None, orderType='Market'):
        """�����µĶ�����"""
        if strategyName==None:
            strategyName = type(self.strategyNow).__name__  # ��ȡʵ��������
        logger.debug('��������->' + str(direction) + str(volume) + str(contract) + str(open) + str(price))

        if orderType == 'Market':  # �м۵�
            return virtualOrder(direction, volume, contract, open, strategyName, oldOrNew='new')
        else:
            return virtualOrder(direction, volume, contract, open, strategyName, oldOrNew='new', price=price,
                                orderType=orderType)

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
        if action==Action.BUY :
            return self.creatOrder("BUY", quantity, instrument, open=True)
        elif action==Action.SELL_SHORT:
            return self.creatOrder("SELL", quantity, instrument, open=True)
        elif action == Action.SELL:
            return self.creatOrder("SELL", quantity, instrument, open=False)
        elif action == Action.BUY_TO_COVER:
            return self.creatOrder("BUY", quantity, instrument, open=False)
        else:
            raise Exception('unkown action!')

    def createLimitOrder(self, action, instrument, quantity, limitPrice=None):
        """Creates a Limit order.
        A limit order is an order to buy or sell a stock at a specific price or better.
        A buy limit order can only be executed at the limit price or lower, and a sell limit order can only be executed at the
        limit price or higher.

        :param action: The order action.
        :type action: Order.Action.BUY, or Order.Action.BUY_TO_COVER, or Order.Action.SELL or Order.Action.SELL_SHORT.
        :param instrument: Instrument identifier.
        :type instrument: string.
        :param limitPrice: The order price. ���û����дĬ��None�����Ŷ����ż۴���
        :type limitPrice: float
        :param quantity: Order quantity.
        :type quantity: int/float.
        :rtype: A :class:`LimitOrder` subclass.
        """

        if action == Action.BUY:
            if not limitPrice:  # û���ṩ�۸���޼۵���
                limitPrice = self.allTick[instrument].ask_price1-10
            return self.creatOrder("BUY", quantity, instrument, open=True, price=limitPrice, orderType='Limit')
        elif action == Action.SELL_SHORT:
            if not limitPrice:  # û���ṩ�۸���޼۵���
                limitPrice = self.allTick[instrument].bid_price1+10
            return self.creatOrder("SELL", quantity, instrument, open=True, price=limitPrice, orderType='Limit')
        elif action == Action.SELL:
            if not limitPrice:  # û���ṩ�۸���޼۵���
                limitPrice = self.allTick[instrument].bid_price1+10
            return self.creatOrder("SELL", quantity, instrument, open=False, price=limitPrice, orderType='Limit')
        elif action == Action.BUY_TO_COVER:
            if not limitPrice:  # û���ṩ�۸���޼۵���
                limitPrice = self.allTick[instrument].ask_price1-10
            return self.creatOrder("BUY", quantity, instrument, open=False, price=limitPrice, orderType='Limit')
        else:
            raise Exception('unkown action!')

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
        logger.debug('�����Ķ���id�ǣ� ' + str(order.id))

    # ===============================================================
    def start(self):  # pyalgotrade ����abstract methods ��д���ɡ�
        pass

    def stop(self):  # pyalgotrade ����abstract methods ��д���ɡ�
        temp = pd.concat([self.strategyAccount[key].account for key in self.strategyAccount.keys()])
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
        # print(self.allTick['SHFE.rb2010']['last_price'])
        self.cash = self.accountInfo.available
        self.balence = self.accountInfo.balance
        logger.debug('real account cash is: ' + str(self.cash))
        logger.debug('real account balance is: ' + str(self.balence))
        """--------------------------------------------�µ�----------------------------------------------"""
        #  ע�����е�Queue����ȫ������VirtualOrder
        if self.orderQueue:  # ����������ж�����
            logger.debug('��Ҫ�µĵ��ֱ��ǣ�')
            groupbyOrder = {}  # ��һ��dict��װ���ඩ����
            for order in self.orderQueue:
                logger.debug(str(order))
                if not order.virContract in groupbyOrder:  # ��û�������Լ
                    groupbyOrder[order.virContract] = {'long': [], 'short': [], 'other':[]}
                    # ��ʼ��Ϊdict Of list , ��Ϊ�������, �޼۵�ֱ�ӽ���other ����Գ�
                if order.orderType == 'Limit':  # �޼۵�
                    groupbyOrder[order.virContract]['other'].append(order)
                else:
                    if order.virDirection == 'BUY':  # ���������߷��ࡣ
                        groupbyOrder[order.virContract]['long'].append(order)
                    else:
                        groupbyOrder[order.virContract]['short'].append(order)

            logger.debug('������ɣ�dict�ǣ� ')
            logger.debug(str(groupbyOrder))

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
                            groupbyOrder[contract]['long'][b].is_dead = True
                            groupbyOrder[contract]['short'][s].volumeLeft = \
                            groupbyOrder[contract]['short'][s].volumeLeft - groupbyOrder[contract]['long'][b].volumeLeft
                            b += 1

                        elif groupbyOrder[contract]['long'][b].volumeLeft > groupbyOrder[contract]['short'][s].volumeLeft:
                            groupbyOrder[contract]['short'][s].is_dead = True
                            groupbyOrder[contract]['long'][b].volumeLeft = \
                            groupbyOrder[contract]['long'][b].volumeLeft - groupbyOrder[contract]['short'][s].volumeLeft
                            s += 1

                        else:
                            raise Exception('������۳�������')

                        if b == len(contract['long']) or s == len(contract['short']):
                            break
            logger.debug('������ɣ�����ǣ�')
            logger.debug(str(groupbyOrder))

            for item in groupbyOrder:  # �����µ�
                pos = self.posDict.get(item, None)
                if pos:
                    availablePos = pos.pos_long - pos.pos_short
                else:
                    availablePos = 0

                if groupbyOrder[item]['long']:
                    for order in groupbyOrder[item]['long']:
                        if availablePos >= 0:  # Ҫ�򣬳ֲִ���0 ��ô�������ⵥ��ƽ����Ҫ����
                            logger.debug('�µ�1')
                            logger.info(str(order))
                            res = self.api.insert_order(order.contract, order.direction,
                                                        'OPEN', order.volumeLeft,
                                                        self.allTick[order.virContract]['upper_limit'])
                            order.attach(res)
                            self.unfilledQueue.append(order)
                            availablePos -= order.volumeLeft
                        elif availablePos < 0:
                            if abs(availablePos) > order.volumeLeft:  # ��Ҫ���׵����������У�����һ��ֱ��ƽ
                                logger.debug('�µ�2')
                                logger.info(str(order))
                                res = self.api.insert_order(order.contract, order.direction,
                                                            'CLOSE', order.volumeLeft,
                                                            self.allTick[order.virContract]['upper_limit'])

                                order.attach(res)
                                self.unfilledQueue.append(order)
                                availablePos += order.volumeLeft
                            else:  # ��ƽ�ٿ�
                                logger.debug('�µ�3')
                                logger.info(str(order))
                                res = self.api.insert_order(order.contract, order.direction,
                                                            'CLOSE', abs(availablePos),
                                                            self.allTick[order.virContract]['upper_limit'])
                                res1 = self.api.insert_order(order.contract, order.direction,
                                                             'OPEN', order.volumeLeft - abs(availablePos),
                                                             self.allTick[order.virContract]['upper_limit'])
                                order.attach(res)
                                order.attach(res1)
                                self.unfilledQueue.append(order)
                                availablePos = 0

                elif groupbyOrder[item]['short']:
                    for order in groupbyOrder[item]['short']:
                        if availablePos <= 0:  # Ҫ�����ֲ�С��0
                            logger.debug('�µ�4')
                            logger.info(str(order))
                            res = self.api.insert_order(order.contract, order.direction,
                                                        'OPEN', order.volumeLeft,
                                                        self.allTick[order.virContract]['lower_limit'])
                            order.attach(res)
                            self.unfilledQueue.append(order)
                            availablePos += order.volumeLeft
                        elif availablePos > 0:
                            if availablePos > order.volumeLeft:  # ��Ҫ���׵����������У�����һ��ֱ��ƽ
                                logger.debug('�µ�5')
                                logger.info(str(order))
                                res = self.api.insert_order(order.contract, order.direction,
                                                            'CLOSE', order.volumeLeft,
                                                            self.allTick[order.virContract]['lower_limit'])
                                order.attach(res)
                                self.unfilledQueue.append(order)
                                availablePos -= order.volumeLeft
                            else:
                                logger.debug('�µ�6')
                                logger.info(str(order))
                                res = self.api.insert_order(order.contract, order.direction,
                                                            'CLOSE', availablePos,
                                                            self.allTick[order.virContract]['lower_limit'])
                                res1 = self.api.insert_order(order.contract, order.direction,
                                                             'OPEN', order.volumeLeft - availablePos,
                                                             self.allTick[order.virContract]['lower_limit'])
                                order.attach(res)
                                order.attach(res1)
                                self.unfilledQueue.append(order)
                                availablePos = 0

                if groupbyOrder[item]['other']:
                    for order in groupbyOrder[item]['other']:
                        if order.virDirection == 'SELL':
                            if availablePos <= 0:  # Ҫ�����ֲ�С��0
                                logger.debug('�µ�7')
                                logger.info(str(order))
                                res = self.api.insert_order(order.contract, order.direction,
                                                            'OPEN', order.volumeLeft,
                                                            order.price)
                                order.attach(res)
                                self.unfilledQueue.append(order)
                                availablePos += order.volumeLeft
                            elif availablePos > 0:
                                if availablePos > order.volumeLeft:  # ��Ҫ���׵����������У�����һ��ֱ��ƽ
                                    logger.debug('�µ�8')
                                    logger.info(str(order))
                                    res = self.api.insert_order(order.contract, order.direction,
                                                                'CLOSE', order.volumeLeft,
                                                                order.price)
                                    order.attach(res)
                                    self.unfilledQueue.append(order)
                                    availablePos -= order.volumeLeft
                                else:
                                    logger.debug('�µ�9')
                                    logger.info(str(order))
                                    res = self.api.insert_order(order.contract, order.direction,
                                                                'CLOSE', availablePos,
                                                                order.price)
                                    res1 = self.api.insert_order(order.contract, order.direction,
                                                                 'OPEN', order.volumeLeft - availablePos,
                                                                 order.price)
                                    order.attach(res)
                                    order.attach(res1)
                                    self.unfilledQueue.append(order)
                                    availablePos = 0

                        elif order.virDirection == 'BUY':
                            if availablePos <= 0:  # Ҫ�����ֲ�С��0
                                logger.debug('�µ�10')
                                logger.info(str(order))
                                res = self.api.insert_order(order.contract, order.direction,
                                                            'OPEN', order.volumeLeft,
                                                            order.price)
                                order.attach(res)
                                self.unfilledQueue.append(order)
                                availablePos += order.volumeLeft
                            elif availablePos > 0:
                                if availablePos > order.volumeLeft:  # ��Ҫ���׵����������У�����һ��ֱ��ƽ
                                    logger.debug('�µ�11')
                                    logger.info(str(order))
                                    res = self.api.insert_order(order.contract, order.direction,
                                                                'CLOSE', order.volumeLeft,
                                                                order.price)
                                    order.attach(res)
                                    self.unfilledQueue.append(order)
                                    availablePos -= order.volumeLeft
                                else:
                                    logger.debug('�µ�12')
                                    logger.info(str(order))
                                    res = self.api.insert_order(order.contract, order.direction,
                                                                'CLOSE', availablePos,
                                                                order.price)
                                    res1 = self.api.insert_order(order.contract, order.direction,
                                                                 'OPEN', order.volumeLeft - availablePos,
                                                                 order.price)
                                    order.attach(res)
                                    order.attach(res1)
                                    self.unfilledQueue.append(order)
                                    availablePos = 0

            self.orderQueue = []  # ���¹��㡣

        """-------------------------------------δ�ɽ���������ʱ���յȴ�5�볷������-----------------------------"""
        if self.unfilledQueue:
            logger.debug('����δ�ɽ��ĵ�')
            tempList = []
            while self.unfilledQueue:
                temp = self.unfilledQueue.pop()  # �ѵ�һ���ó��������û��dead������append��ȥ��append��ĩβ����������ѭ��һ�Ρ�
                if not temp.is_dead:  # ���dead�˾Ͳ���append�����ˣ�ֱ�Ӳ����ˡ�
                    # if not temp.insert_date_time:
                    #     temp.insert_date_time = time.time()
                    logger.debug('�е�δ��,�����ǣ�')
                    logger.debug(str(temp.id))
                    logger.debug('�ҵ�ʱ���ǣ�')
                    logger.debug(temp.insert_date_time)
                    if time.time() - temp.insert_date_time > 5:
                        # ����5�룬�Ҽ۸������ų���
                        logger.debug('��ʱδ�ɽ���')
                        if temp.direction == 'BUY':
                            if temp.limit_price != self.allTick[temp.instrument_id].bid_price1:
                                self.cancelOrderQueue.append(temp)
                                logger.debug('Ҫ��' + str(temp))
                                continue
                                # ֻҪ������queue�����˾Ͳ��ڱ�����δ�ɽ�queue���������ڳ���״̬�����ӳٶ����´˴��־��������
                                # ��Ҫ��������������ӵ�����queue�У�����ͬһ���������ƺܶ�Σ������continueһ����
                        else:
                            if temp.limit_price != self.allTick[temp.instrument_id].ask_price1:
                                self.cancelOrderQueue.append(temp)
                                logger.debug('Ҫ��' + str(temp))
                                continue
                    tempList.append(temp)
                else:  # �˵��Ѿ������ˣ�������ȫ�ɽ��ˡ�
                    logger.debug('����ˣ��������ˣ�������ȫ�ɽ���')
                    logger.info(str(temp))

            self.unfilledQueue = tempList
            logger.debug('unfilled queue ������ǣ�')
            logger.debug(str(self.unfilledQueue))
        """--------------------------------------------����--------------------------------------------------------"""
        if self.cancelOrderQueue:  # ��������
            logger.debug('��������')
            while self.cancelOrderQueue:
                temp = self.cancelOrderQueue.pop()
                logger.debug('��' + str(temp))
                for i in temp.realOrder:
                    if not i.is_dead:
                        self.api.cancel_order(i.order_id)
                self.reInsertQueue.append(temp)

        """------------------------�ȴ���������鵽�������ùҵ������������µ�-----------------------------------------"""
        # tqsdk��Ҫ������wait_update�Ժ���ܼ�⵽������
        if self.reInsertQueue:
            logger.debug('����Ƿ��������')
            tempList = []
            while self.reInsertQueue:
                temp = self.reInsertQueue.pop()
                if temp.is_dead:  # tqsdkȷ���ˣ��������¡�
                    if temp.orderType == 'limit':
                        # �������޼۵�
                        logger.debug('�����޼۵�')
                        self.orderQueue.append(virtualOrder(temp.virDirection, temp.volumeLeft,
                                               temp.virContract, temp.open, type(self.strategyNow).__name__, price=None))
                    else:
                        # �����µ�
                        logger.debug('�����м۵�')
                        self.orderQueue.append(virtualOrder(temp.virDirection, temp.volumeLeft,
                                                            temp.virContract, temp.open, type(self.strategyNow).__name__))
                else:
                    tempList.append(temp)
            self.unfilledQueue = tempList
            logger.debug('��Ҫ����Ƿ����µ�queue�ǣ�')
            logger.debug(str(self.reInsertQueue))

        """------------------------------------------���¸��������˻���------------------------------------------"""
        for item in self.strategy:  # ���¸��������˻�����
            self.strategyAccount[item].update(self.allTick, self.posDict)


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
        self.account = account.reset_index(drop=True)
        try:
            self.balance = self.account['balance'][0]
        except :
            print('����Ƿ���currentAccount�������������в��Գֲ֣�')

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
        # logger.debug('tick �ǣ�')
        # logger.debug(str(allTick))
        for i in range(len(self.account)):
            if self.account.loc[i, 'direction'] == 'BUY':
                # ����Ȩ�棬��tick�ı䶯���ϳ��е��������ٳ��Ϻ�Լ������
                self.account['balance'] += \
                    (allTick[self.account.loc[i, 'contract']].last_price - self.account.loc[i, 'prePrice']) \
                    * self.account.loc[i, 'volume'] * allTick[self.account.loc[i, 'contract']].volume_multiple

            elif self.account.loc[i, 'direction'] == 'SELL':
                # ����Ȩ�棬��tick�ı䶯���ϳ��е��������ٳ��Ϻ�Լ������
                self.account['balance'] -= \
                    (allTick[self.account.loc[i, 'contract']].last_price - self.account.loc[i, 'prePrice']) \
                    * self.account.loc[i, 'volume'] * allTick[self.account.loc[i, 'contract']].volume_multiple
            if self.account.loc[i, 'account'] != 1:  # ���Ǽ�¼��Ϣ���У��ż���
                self.account.loc[i, 'prePrice'] = allTick[self.account.loc[i, 'contract']].last_price
                pos = position[self.account.loc[i, 'contract']]
                self.account.loc[i, 'fund occupied'] = \
                    pos.margin / (pos.pos_long + pos.pos_short)
        # logger.debug('�˻�����ǣ�')
        # logger.debug(str(self.account))

        # �������ĸ��¡�����position account ���� position
        for order in self.orders[:]:  # ��ԭlist���п�����������Ϊɾ������index���
            logger.debug('�������仯')
            if order.is_dead and order.volume != order.volumeLeft:
                # ���ҵ����Ƿ��ʣ������ȣ�������ȫδ�ɽ��ĳ������������³ֲֵ��³������⡣ ����ᱻ����һ���ֲ�����Ϊ0�ĳ�
                # �ּ�¼
                logger.debug('����ɵĶ���')
                self.orders.remove(order)
                tempTrade = self.account.groupby(by=['contract', 'direction', 'oldOrNew']).apply(lambda x: x)
                tempStr = str(order.contract) + str(order.direction) + str(order.oldOrNew)
                if tempStr in tempTrade:  # ˵��������ֲ�
                    logger.debug('�޸ľɳֲ֡�')
                    if order.open:
                        tempTrade['volume'] += (order.volume - order.volumeLeft)  # ���ɽ����������ϼ���
                    else:  # ƽ��
                        if order.volume < tempTrade['volume']:
                            tempTrade['volume'] -= (order.volume - order.volumeLeft)
                        elif order.volume == tempTrade['volume']:
                            tempTrade.drop(tempStr, inplace=True)
                        else:
                            logger.error('ƽ�������������гֲ֣����飡')
                            raise Exception('ƽ�������������гֲ֣����飡')

                    self.account = tempTrade.reset_index()
                else:
                    logger.debug('�����³ֲ�')
                    self.account.loc[len(self.account), ['direction', 'volume', 'contract']] = \
                        [order.virDirection, order.virVolume - order.volumeLeft, order.virContract]
                self.account['balance'] -= order.fee  # ȥ����ν��׵������ѡ�
                self.account['fee'] += order.fee
        logger.debug('�����궩���Ժ���˻�����ǣ�')
        logger.debug('\n' + str(self.account))


class virtualOrder:
    """
    ģ��Ķ����࣬ ��Ϊ�����˻���ʱ���Ǽ������ⵥ����ͬһ��ʵ�̵�������Ҫ��д��
    """
    count = [0]  # ������¼���촴���˶��ٶ�������ȷ��ÿ��ʵ����������ظ���id

    def __init__(self, direction, volume, contract, open, strategyName, oldOrNew='old', price=None, orderType='Market'):
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
        self.id = self.count[0]
        self.__volumeLeft = volume  # �ѳɽ�����
        self.__is_dead = False
        self.count[0] += 1
        self.strategyName = strategyName
        self.orderType = orderType

        self.realOrder = []
        self.price = price

    def __str__(self):
        return 'direction: {}, volume: {}, volumeLeft: {}, contract: {}, open: {}, oldOrNew��{}, time: {}, ' \
               '.isdead: {}, strategyName: {}, countNum: {}'.format(self.virDirection, self.virVolume, self.volumeLeft,
                                                      self.virContract, self.open, self.oldOrNew, self.time,
                                                      self.is_dead, self.strategyName, self.id)

    def attach(self, order: 'tqsdk order'):
        """
        ������������order��
        :param order: ���������Ӧ��tqsdk�˻��ĵ����п��ܶ�����ⵥ������ͬһ��tqsdk�ĵ��ϡ�
        :return:
        """
        self.realOrder.append(order)

    @property
    def is_dead(self):
        #  ���ȫ����ʵ�������ˣ����ⵥ�Ż���
        for item in self.realOrder:
            logger.debug('��ʵ�����������')
            logger.debug(str(item.is_dead))
            if not item.is_dead:
                self.__is_dead = False
            else:
                self.__is_dead = True
        logger.debug('���ն�������ǣ�' + str(self.__is_dead))
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
        return self.price  # �п����ж����ʵ������ �����޼��µ��ļ�Ǯһ��һ����

    @property
    def direction(self):
        return self.virDirection

    @property
    def contract(self):
        return self.virContract

    @property
    def volumeLeft(self):
        if self.realOrder:
            self.__volumeLeft = 0
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
        self.i = 0
        self.j = 0

    def __getitem__(self, item):
        return self.allDataSource[item]

    def __contains__(self, item):  # �������ж�������ʵ������ in ��ʱ�򴥷����������
        return True if item in self.allDataSource else False

    # iter �� next����ʵ���� for in ���
    def __iter__(self):
        return self

    def __next__(self):
        self.i = self.j
        if self.i < len(self.allDataSource):
            self.j = self.i + 1
            return list(self.allDataSource.keys())[self.i]

        self.i = 0  # û��return��Ҫ��i���㡣
        raise StopIteration()


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
        return self.__data.keys()

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

    def getDateTime(self):
        return self.__data['datetime']

    def set(self, value: 'pd.Series'):
        self.__data = value


class Action(object):
    BUY = 1
    BUY_TO_COVER = 2
    SELL = 3
    SELL_SHORT = 4