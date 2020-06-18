# coding=gbk
"""实盘运行时需要的模块"""
# TODO 重新测试，找到了不停下单的原因是因为撤单后订单挂掉需要等待几个wait_update().需要继续测试是否正常挂撤单。
# TODO 下单后生成的虚拟订单没有关联到虚拟账户，在realBroker的update（）里面。
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
    继承pyalgotrade的基类，以实现和tqsdk交互
    """

    def __init__(self, api: 'TqApi', position=None, allTick=None, strategy=None):
        """
        :param strategy: 包含所有策略名称的list
        strategy和alltick需要一起传，否则还是等于没有，需要重新读取
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
        self.strategy = {}  # 存放所有的strategy
        self.strategyNow = None  # 代表这个时候onbars运行的strategy，在RealBroker的实例中可以修改这个值，用来提示内部此时运行的策略
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
                # !!! 策略不可重名， 如需同策略不同参数，可以继承一个，然后换个名字。
                self.strategy[item[0]] = item[1:]  # 将strategy to  run 中的策略对应的 名字和合约记录下来。
                for contract in item[1:]:
                    if contract[0] not in self.allTick:
                        self.allTick[contract[0]] = self.api.get_quote(contract[0])
                        # 如果是指数合约那么把对应的主力合约也订阅上。
                        if 'KQ.i' in contract[0] and contract[0].replace('KQ.i', 'KQ.m') not in self.allTick:
                            self.allTick[contract[0].replace('KQ.i', 'KQ.m')] = \
                                self.api.get_quote(contract[0].replace('KQ.i', 'KQ.m'))
                            self.allTick[self.allTick[contract[0].replace('KQ.i', 'KQ.m')].underlying_symbol] = \
                                self.allTick[contract[0].replace('KQ.i', 'KQ.m')]
        else:
            self.allTick = allTick
            self.strategy = strategy

        self.strategyAccount = {}  # 存储一个虚拟的分策略的账户信息

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
        logger.debug('现金是' + str(self.strategyAccount[strategyName].getCash()))
        return self.strategyAccount[strategyName].getCash()

    def getShares(self, instrument, strategyName=None):
        """Returns the number of shares for an instrument."""
        if strategyName==None:
            strategyName = type(self.strategyNow).__name__  # 获取实例的类名
        return self.getPositions(strategyName).loc[:, 'volume'].sum()  # 返回一个对多空仓加总了的数量。

    def getPositions(self, strategyName=None):
        """Returns a dictionary that maps instruments to shares."""
        if strategyName==None:
            strategyName = type(self.strategyNow).__name__  # 获取实例的类名
        logger.debug('持仓是' + str(self.strategyAccount[strategyName].getPosition()))
        return self.strategyAccount[strategyName].getPosition()

    def getEquity(self, strategyName=None):
        """获取虚拟持仓的权益"""
        if strategyName==None:
            strategyName = type(self.strategyNow).__name__  # 获取实例的类名
        logger.debug('权益是： ' + str(self.strategyAccount[strategyName].getPosition()))
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
        self.strategyAccount[type(self.strategyNow).__name__].addOrder(order)  # 给虚拟账户更新订单流
        self.orderQueue.append(order)  # 给实际订单处理序列增加订单流。

    def creatOrder(self, direction, volume, contract, open, strategyName=None, price=None, orderType='Market'):
        """创建新的订单类"""
        if strategyName==None:
            strategyName = type(self.strategyNow).__name__  # 获取实例的类名
        logger.debug('创建订单->' + str(direction) + str(volume) + str(contract) + str(open) + str(price))

        if orderType == 'Market':  # 市价单
            return virtualOrder(direction, volume, contract, open, strategyName, oldOrNew='new')
        else:
            return virtualOrder(direction, volume, contract, open, strategyName, oldOrNew='new', price=price,
                                orderType=orderType)

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
        :param limitPrice: The order price. 如果没有填写默认None则用排队最优价处理
        :type limitPrice: float
        :param quantity: Order quantity.
        :type quantity: int/float.
        :rtype: A :class:`LimitOrder` subclass.
        """

        if action == Action.BUY:
            if not limitPrice:  # 没有提供价格的限价单。
                limitPrice = self.allTick[instrument].ask_price1-10
            return self.creatOrder("BUY", quantity, instrument, open=True, price=limitPrice, orderType='Limit')
        elif action == Action.SELL_SHORT:
            if not limitPrice:  # 没有提供价格的限价单。
                limitPrice = self.allTick[instrument].bid_price1+10
            return self.creatOrder("SELL", quantity, instrument, open=True, price=limitPrice, orderType='Limit')
        elif action == Action.SELL:
            if not limitPrice:  # 没有提供价格的限价单。
                limitPrice = self.allTick[instrument].bid_price1+10
            return self.creatOrder("SELL", quantity, instrument, open=False, price=limitPrice, orderType='Limit')
        elif action == Action.BUY_TO_COVER:
            if not limitPrice:  # 没有提供价格的限价单。
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
        logger.debug('撤掉的订单id是： ' + str(order.id))

    # ===============================================================
    def start(self):  # pyalgotrade 中有abstract methods 非写不可。
        pass

    def stop(self):  # pyalgotrade 中有abstract methods 非写不可。
        temp = pd.concat([self.strategyAccount[key].account for key in self.strategyAccount.keys()])
        temp.to_csv('currentAccount.csv')

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
        # print(self.allTick['SHFE.rb2010']['last_price'])
        self.cash = self.accountInfo.available
        self.balence = self.accountInfo.balance
        logger.debug('real account cash is: ' + str(self.cash))
        logger.debug('real account balance is: ' + str(self.balence))
        """--------------------------------------------下单----------------------------------------------"""
        #  注，所有的Queue里面全部都是VirtualOrder
        if self.orderQueue:  # 如果队列中有订单。
            logger.debug('有要下的单分别是：')
            groupbyOrder = {}  # 用一个dict来装分类订单。
            for order in self.orderQueue:
                logger.debug(str(order))
                if not order.virContract in groupbyOrder:  # 还没有这个合约
                    groupbyOrder[order.virContract] = {'long': [], 'short': [], 'other':[]}
                    # 初始化为dict Of list , 分为多空两边, 限价单直接进入other 不予对冲
                if order.orderType == 'Limit':  # 限价单
                    groupbyOrder[order.virContract]['other'].append(order)
                else:
                    if order.virDirection == 'BUY':  # 分买卖两边分类。
                        groupbyOrder[order.virContract]['long'].append(order)
                    else:
                        groupbyOrder[order.virContract]['short'].append(order)

            logger.debug('分类完成，dict是： ')
            logger.debug(str(groupbyOrder))

            for contract in groupbyOrder:  # 对分类好的虚拟单进行循环，看有没有可以互相抵消的。
                if groupbyOrder[contract]['long'] and groupbyOrder[contract]['short']:  # 确保两个都不是空
                    b = 0  # 初始化两个指针， 用来确定消去到了两个list的那个位置。
                    s = 0
                    while True:
                        if groupbyOrder[contract]['long'][b].volumeLeft == groupbyOrder[contract]['short'][s].volumeLeft:
                            groupbyOrder[contract]['long'][b].is_dead = True  # 相等直接两个单消掉。全部dead，位置加一
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
                            raise Exception('数量标价出现问题')

                        if b == len(contract['long']) or s == len(contract['short']):
                            break
            logger.debug('抵消完成，结果是：')
            logger.debug(str(groupbyOrder))

            for item in groupbyOrder:  # 进行下单
                pos = self.posDict.get(item, None)
                if pos:
                    availablePos = pos.pos_long - pos.pos_short
                else:
                    availablePos = 0

                if groupbyOrder[item]['long']:
                    for order in groupbyOrder[item]['long']:
                        if availablePos >= 0:  # 要买，持仓大于0 那么不论虚拟单开平，都要开多
                            logger.debug('下单1')
                            logger.info(str(order))
                            res = self.api.insert_order(order.contract, order.direction,
                                                        'OPEN', order.volumeLeft,
                                                        self.allTick[order.virContract]['upper_limit'])
                            order.attach(res)
                            self.unfilledQueue.append(order)
                            availablePos -= order.volumeLeft
                        elif availablePos < 0:
                            if abs(availablePos) > order.volumeLeft:  # 需要交易的量少于已有，可以一笔直接平
                                logger.debug('下单2')
                                logger.info(str(order))
                                res = self.api.insert_order(order.contract, order.direction,
                                                            'CLOSE', order.volumeLeft,
                                                            self.allTick[order.virContract]['upper_limit'])

                                order.attach(res)
                                self.unfilledQueue.append(order)
                                availablePos += order.volumeLeft
                            else:  # 先平再开
                                logger.debug('下单3')
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
                        if availablePos <= 0:  # 要卖，持仓小于0
                            logger.debug('下单4')
                            logger.info(str(order))
                            res = self.api.insert_order(order.contract, order.direction,
                                                        'OPEN', order.volumeLeft,
                                                        self.allTick[order.virContract]['lower_limit'])
                            order.attach(res)
                            self.unfilledQueue.append(order)
                            availablePos += order.volumeLeft
                        elif availablePos > 0:
                            if availablePos > order.volumeLeft:  # 需要交易的量少于已有，可以一笔直接平
                                logger.debug('下单5')
                                logger.info(str(order))
                                res = self.api.insert_order(order.contract, order.direction,
                                                            'CLOSE', order.volumeLeft,
                                                            self.allTick[order.virContract]['lower_limit'])
                                order.attach(res)
                                self.unfilledQueue.append(order)
                                availablePos -= order.volumeLeft
                            else:
                                logger.debug('下单6')
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
                            if availablePos <= 0:  # 要卖，持仓小于0
                                logger.debug('下单7')
                                logger.info(str(order))
                                res = self.api.insert_order(order.contract, order.direction,
                                                            'OPEN', order.volumeLeft,
                                                            order.price)
                                order.attach(res)
                                self.unfilledQueue.append(order)
                                availablePos += order.volumeLeft
                            elif availablePos > 0:
                                if availablePos > order.volumeLeft:  # 需要交易的量少于已有，可以一笔直接平
                                    logger.debug('下单8')
                                    logger.info(str(order))
                                    res = self.api.insert_order(order.contract, order.direction,
                                                                'CLOSE', order.volumeLeft,
                                                                order.price)
                                    order.attach(res)
                                    self.unfilledQueue.append(order)
                                    availablePos -= order.volumeLeft
                                else:
                                    logger.debug('下单9')
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
                            if availablePos <= 0:  # 要卖，持仓小于0
                                logger.debug('下单10')
                                logger.info(str(order))
                                res = self.api.insert_order(order.contract, order.direction,
                                                            'OPEN', order.volumeLeft,
                                                            order.price)
                                order.attach(res)
                                self.unfilledQueue.append(order)
                                availablePos += order.volumeLeft
                            elif availablePos > 0:
                                if availablePos > order.volumeLeft:  # 需要交易的量少于已有，可以一笔直接平
                                    logger.debug('下单11')
                                    logger.info(str(order))
                                    res = self.api.insert_order(order.contract, order.direction,
                                                                'CLOSE', order.volumeLeft,
                                                                order.price)
                                    order.attach(res)
                                    self.unfilledQueue.append(order)
                                    availablePos -= order.volumeLeft
                                else:
                                    logger.debug('下单12')
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

            self.orderQueue = []  # 重新归零。

        """-------------------------------------未成交处理。先暂时按照等待5秒撤单处理。-----------------------------"""
        if self.unfilledQueue:
            logger.debug('处理未成交的单')
            tempList = []
            while self.unfilledQueue:
                temp = self.unfilledQueue.pop()  # 把第一个拿出来，如果没有dead就重新append回去，append在末尾，正好整个循环一次。
                if not temp.is_dead:  # 如果dead了就不在append回来了，直接不管了。
                    # if not temp.insert_date_time:
                    #     temp.insert_date_time = time.time()
                    logger.debug('有单未死,单号是：')
                    logger.debug(str(temp.id))
                    logger.debug('挂单时间是：')
                    logger.debug(temp.insert_date_time)
                    if time.time() - temp.insert_date_time > 5:
                        # 大于5秒，且价格不是最优撤单
                        logger.debug('超时未成交！')
                        if temp.direction == 'BUY':
                            if temp.limit_price != self.allTick[temp.instrument_id].bid_price1:
                                self.cancelOrderQueue.append(temp)
                                logger.debug('要撤' + str(temp))
                                continue
                                # 只要被撤单queue接受了就不在保留在未成交queue，避免由于撤单状态返回延迟而导致此处又觉得这个单
                                # 需要撤，于是重新添加到撤单queue中，导致同一个单被复制很多次，下面的continue一样。
                        else:
                            if temp.limit_price != self.allTick[temp.instrument_id].ask_price1:
                                self.cancelOrderQueue.append(temp)
                                logger.debug('要撤' + str(temp))
                                continue
                    tempList.append(temp)
                else:  # 此单已经被撤了，或者完全成交了。
                    logger.debug('完成了，即被撤了，或者完全成交了')
                    logger.info(str(temp))

            self.unfilledQueue = tempList
            logger.debug('unfilled queue 的情况是：')
            logger.debug(str(self.unfilledQueue))
        """--------------------------------------------撤单--------------------------------------------------------"""
        if self.cancelOrderQueue:  # 撤单处理。
            logger.debug('撤单处理')
            while self.cancelOrderQueue:
                temp = self.cancelOrderQueue.pop()
                logger.debug('撤' + str(temp))
                for i in temp.realOrder:
                    if not i.is_dead:
                        self.api.cancel_order(i.order_id)
                self.reInsertQueue.append(temp)

        """------------------------等待交易所检查到撤单，让挂单已死再重新下单-----------------------------------------"""
        # tqsdk需要过几个wait_update以后才能检测到撤单。
        if self.reInsertQueue:
            logger.debug('检查是否可以重下')
            tempList = []
            while self.reInsertQueue:
                temp = self.reInsertQueue.pop()
                if temp.is_dead:  # tqsdk确认了，我再重下。
                    if temp.orderType == 'limit':
                        # 重新下限价单
                        logger.debug('重下限价单')
                        self.orderQueue.append(virtualOrder(temp.virDirection, temp.volumeLeft,
                                               temp.virContract, temp.open, type(self.strategyNow).__name__, price=None))
                    else:
                        # 重新下单
                        logger.debug('重下市价单')
                        self.orderQueue.append(virtualOrder(temp.virDirection, temp.volumeLeft,
                                                            temp.virContract, temp.open, type(self.strategyNow).__name__))
                else:
                    tempList.append(temp)
            self.unfilledQueue = tempList
            logger.debug('需要检查是否重下的queue是：')
            logger.debug(str(self.reInsertQueue))

        """------------------------------------------更新各个虚拟账户。------------------------------------------"""
        for item in self.strategy:  # 更新各个虚拟账户数据
            self.strategyAccount[item].update(self.allTick, self.posDict)


class _virtualAccountHelp:
    """
    帮助计算不同策略的虚拟持仓
    """
    generalTickerInfo = pd.read_csv('general_ticker_info.csv')
    def __init__(self, account):
        """
        :param account表示从本地文件读取的时候有多少各种持仓的df
        """
        self.orders = []
        self.account = account.reset_index(drop=True)
        try:
            self.balance = self.account['balance'][0]
        except :
            print('检查是否在currentAccount里面有所有运行策略持仓！')

    def getCash(self):
        return self.balance - self.account['funds_occupied'].sum()

    def getPosition(self):
        return self.account

    def getEquity(self):
        return self.balance

    def addOrder(self, order: 'virtualOrder'):
        """
        记录最新的下单情况的order
        :param order:
        :return:
        """
        self.orders.append(order)

    def update(self, allTick: dict, position: dict):
        """
        根据最新的行情或者成交来更新账户
        :param allTick: 包含所有品种的Tick的dict
        :param position: tqsdk的position， 用来计算每个不同合约的保证金占用。
        :return:
        """
        # logger.debug('tick 是：')
        # logger.debug(str(allTick))
        for i in range(len(self.account)):
            if self.account.loc[i, 'direction'] == 'BUY':
                # 更新权益，用tick的变动乘上持有的数量，再乘上合约乘数。
                self.account['balance'] += \
                    (allTick[self.account.loc[i, 'contract']].last_price - self.account.loc[i, 'prePrice']) \
                    * self.account.loc[i, 'volume'] * allTick[self.account.loc[i, 'contract']].volume_multiple

            elif self.account.loc[i, 'direction'] == 'SELL':
                # 更新权益，用tick的变动乘上持有的数量，再乘上合约乘数。
                self.account['balance'] -= \
                    (allTick[self.account.loc[i, 'contract']].last_price - self.account.loc[i, 'prePrice']) \
                    * self.account.loc[i, 'volume'] * allTick[self.account.loc[i, 'contract']].volume_multiple
            if self.account.loc[i, 'account'] != 1:  # 不是记录信息的行，才计算
                self.account.loc[i, 'prePrice'] = allTick[self.account.loc[i, 'contract']].last_price
                pos = position[self.account.loc[i, 'contract']]
                self.account.loc[i, 'fund occupied'] = \
                    pos.margin / (pos.pos_long + pos.pos_short)
        # logger.debug('账户情况是：')
        # logger.debug(str(self.account))

        # 处理订单的更新。更新position account 就是 position
        for order in self.orders[:]:  # 对原list进行拷贝，避免因为删除导致index溢出
            logger.debug('处理订单变化')
            if order.is_dead and order.volume != order.volumeLeft:
                # 检查挂单量是否和剩余量相等，避免完全未成交的撤单被用来更新持仓导致出现问题。 比如会被创建一个持仓数量为0的持
                # 仓记录
                logger.debug('有完成的订单')
                self.orders.remove(order)
                tempTrade = self.account.groupby(by=['contract', 'direction', 'oldOrNew']).apply(lambda x: x)
                tempStr = str(order.contract) + str(order.direction) + str(order.oldOrNew)
                if tempStr in tempTrade:  # 说明有这个持仓
                    logger.debug('修改旧持仓。')
                    if order.open:
                        tempTrade['volume'] += (order.volume - order.volumeLeft)  # 将成交的数量加上即可
                    else:  # 平仓
                        if order.volume < tempTrade['volume']:
                            tempTrade['volume'] -= (order.volume - order.volumeLeft)
                        elif order.volume == tempTrade['volume']:
                            tempTrade.drop(tempStr, inplace=True)
                        else:
                            logger.error('平仓数量超过已有持仓，请检查！')
                            raise Exception('平仓数量超过已有持仓，请检查！')

                    self.account = tempTrade.reset_index()
                else:
                    logger.debug('创建新持仓')
                    self.account.loc[len(self.account), ['direction', 'volume', 'contract']] = \
                        [order.virDirection, order.virVolume - order.volumeLeft, order.virContract]
                self.account['balance'] -= order.fee  # 去掉这次交易的手续费。
                self.account['fee'] += order.fee
        logger.debug('更新完订单以后的账户情况是：')
        logger.debug('\n' + str(self.account))


class virtualOrder:
    """
    模拟的订单类， 因为虚拟账户有时候是几个虚拟单发成同一个实盘单，所以要重写。
    """
    count = [0]  # 用来记录当天创建了多少订单，以确定每个实例不会出现重复的id

    def __init__(self, direction, volume, contract, open, strategyName, oldOrNew='old', price=None, orderType='Market'):
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
        self.id = self.count[0]
        self.__volumeLeft = volume  # 已成交数量
        self.__is_dead = False
        self.count[0] += 1
        self.strategyName = strategyName
        self.orderType = orderType

        self.realOrder = []
        self.price = price

    def __str__(self):
        return 'direction: {}, volume: {}, volumeLeft: {}, contract: {}, open: {}, oldOrNew：{}, time: {}, ' \
               '.isdead: {}, strategyName: {}, countNum: {}'.format(self.virDirection, self.virVolume, self.volumeLeft,
                                                      self.virContract, self.open, self.oldOrNew, self.time,
                                                      self.is_dead, self.strategyName, self.id)

    def attach(self, order: 'tqsdk order'):
        """
        关联到真正的order上
        :param order: 和这个单对应的tqsdk账户的单，有可能多个虚拟单关联到同一个tqsdk的单上。
        :return:
        """
        self.realOrder.append(order)

    @property
    def is_dead(self):
        #  如果全部真实单都死了，虚拟单才会死
        for item in self.realOrder:
            logger.debug('真实订单的情况：')
            logger.debug(str(item.is_dead))
            if not item.is_dead:
                self.__is_dead = False
            else:
                self.__is_dead = True
        logger.debug('最终订单情况是：' + str(self.__is_dead))
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
        return self.price  # 有可能有多个真实订单， 但是限价下单的价钱一定一样。

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
        """获取这一单的手续费"""
        # TODO 以后再想怎么计算手续费。
        return 0


class RealFeed(csvfeed.GenericBarFeed):
    """模拟pyalgotrade 的feed"""

    def __init__(self):
        super().__init__(Frequency.MINUTE)
        self.allDataSource = {}
        self.i = 0
        self.j = 0

    def __getitem__(self, item):
        return self.allDataSource[item]

    def __contains__(self, item):  # 当代码中对这个类的实例调用 in 的时候触发这个方法。
        return True if item in self.allDataSource else False

    # iter 和 next方法实现了 for in 语句
    def __iter__(self):
        return self

    def __next__(self):
        self.i = self.j
        if self.i < len(self.allDataSource):
            self.j = self.i + 1
            return list(self.allDataSource.keys())[self.i]

        self.i = 0  # 没有return需要将i清零。
        raise StopIteration()


    def addDataSource(self, sourceName, source):
        self.allDataSource[sourceName] = RealSeries(source)

    def keys(self):
        return self.allDataSource.keys()


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