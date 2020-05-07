"""
strategy file ,include all strategy nothing else
Version = 1.0
"""

import time
import logging

from pyalgotrade import strategy
from pyalgotrade.technical import ma
from pyalgotrade.technical import cross
from pyalgotrade import broker
import talib
import pandas as pd
import numpy as np

logger = logging.getLogger('Yhlz')

class YhlzStreategy(strategy.BacktestingStrategy):
    """
    重写策略类，给每个策略都加上可以检查是否移仓的方法
    """
    realTrade = False
    realBroker = ''

    def __init__(self, barFeed, cashOrBroker=1000000):
        if self.realTrade:
            super().__init__(barFeed, self.realBroker)
        else:
            super().__init__(barFeed, cashOrBroker)


    def checkTransPosition(self):
        """
        用来检查是否这个策略需要移仓
        :return:
        """
        pass

    def transInstrument(self, instrument):
        """
        接受一个品种代码输入，输出一个对应的可以交易的代码，比如有时候策略计算的是主力合约的或者是指数的数据，但是下单却下单到别
        的地方，也可以在各个策略中继承然后单独实现这个功能，和检查换合约一样。
        :return:
        """
        return instrument

    def setRealTrade(self, realBroker, realTrade=True):
        """
        设置是否实盘交易。
        :param realBroker: 设置实盘交易的broker
        :param realTrade: 为True则是实盘交易
        :return:
        """
        self.realTrade = realTrade
        self._setBroker(realBroker)


class SMACrossOver(YhlzStreategy):

    def __init__(self, feed, instrument, context, dictOfDataDf):
        super(SMACrossOver, self).__init__(feed)
        self.__instrument = instrument
        self.__position = None
        self.prices = feed[instrument].getPriceDataSeries()
        # 这个策略只有一个品种，所以pop出来必然是那个。pop后这个键值对就不存在，不能取两次
        if self.realTrade:
            logger.debug('实盘')
            self.sma = talib.SMA(self.prices.values, 10)
            self.sma1 = talib.SMA(self.prices.values, 20)
        else:
            logger.debug('回测')
            length = len(dictOfDataDf[list(dictOfDataDf.keys())[0]])  # 拿出第一个df的长度
            self.sma = ma.SMA(self.prices, 108, maxLen=length)
            self.sma1 = ma.SMA(self.prices, 694, maxLen=length)
            self.tech = {instrument: {'sma short': self.sma, 'sma long': self.sma1}}

    def getSMA(self):
        return self.sma

    def transInstrument(self, instrument):
        """
        将指数合约转换为主力合约
        :param instrument:
        :return:
        """
        if self.realTrade:
            if 'KQ.i' in instrument:  # 指数合约。
                return self.getBroker().allTick[instrument.replace('KQ.i', 'KQ.m')].underlying_symbol
            elif 'KQ.m' in instrument:  # 主力合约
                return self.getBroker().allTick[instrument].underlying_symbol
            else:  # 真实合约。
                return instrument

        else:
            return instrument

    def onBars(self, bars):
        
        logger.debug('onbars')
        quantity = 100
        if self.realTrade:
            self.sma = talib.SMA(self.prices.values, 10)
            self.sma1 = talib.SMA(self.prices.values, 20)
            logger.debug('sma是')
            logger.debug(str(self.sma[-3:]))
            logger.debug(str(self.sma1[-3:]))
            if self.sma[-1] > self.sma1[-1] and self.sma[-2] < self.sma1[-2]:
                if self.getBroker().getShares(self.transInstrument(self.__instrument)) != 0:
                    ret = self.getBroker().createMarketOrder(broker.Order.Action.BUY_TO_COVER,
                                                             self.transInstrument(self.__instrument), quantity)
                    self.getBroker().submitOrder(ret)
                    logger.debug('平仓1')
                ret = self.getBroker().createMarketOrder(broker.Order.Action.BUY,
                                                         self.transInstrument(self.__instrument), quantity)
                self.getBroker().submitOrder(ret)
                logger.debug('买1' + str(bars.getDateTime()))
            elif self.sma[-1] < self.sma1[-1] and self.sma[-2] > self.sma1[-2]:
                if self.getBroker().getShares(self.__instrument) != 0:
                    ret = self.getBroker().createMarketOrder(broker.Order.Action.SELL,
                                                             self.transInstrument(self.__instrument), quantity)
                    self.getBroker().submitOrder(ret)
                    logger.debug('平仓2')
                ret = self.getBroker().createMarketOrder(broker.Order.Action.SELL_SHORT,
                                                         self.transInstrument(self.__instrument), quantity)
                self.getBroker().submitOrder(ret)
                logger.debug('卖1' + str(bars.getDateTime()))
        else:
            if cross.cross_above(self.sma, self.sma1) > 0:
                if self.getBroker().getShares(self.__instrument) != 0:
                    ret = self.getBroker().createMarketOrder(broker.Order.Action.BUY_TO_COVER,
                                                             self.transInstrument(self.__instrument), quantity)
                    self.getBroker().submitOrder(ret)
                    logger.debug('平仓3')
                ret = self.getBroker().createMarketOrder(broker.Order.Action.BUY,
                                                         self.transInstrument(self.__instrument), quantity)
                self.getBroker().submitOrder(ret)
                logger.debug('买2' + str(bars.getDateTime()))
            elif cross.cross_below(self.sma, self.sma1) > 0:
                if self.getBroker().getShares(self.__instrument) != 0:
                    ret = self.getBroker().createMarketOrder(broker.Order.Action.SELL,
                                                             self.transInstrument(self.__instrument), quantity)
                    self.getBroker().submitOrder(ret)
                    logger.debug('平仓4')
                ret = self.getBroker().createMarketOrder(broker.Order.Action.SELL_SHORT,
                                                         self.transInstrument(self.__instrument), quantity)
                self.getBroker().submitOrder(ret)
                logger.debug('卖2' + str(bars.getDateTime()))


class TurtleTrade(YhlzStreategy):
    """
    海龟交易策略
    """
    def __init__(self, feed, instruments, context, dictOfDataDf, atrPeriod=20, short=20, long=55):
        """
        初始化
        :parm feed pyalgotrade 的feed对象，装了所有csv数据。类似于dict可以用中括号取值。
        :parm instrument 包含所有category的list，用的是简写，如‘rb’，‘ag’
        :param context context 对象，装所有变量
        :parm atrPeriod atr的周期
        :parm short 唐奇安通道的短期
        :parm long 唐奇安通道的长期
        :parm dictOfDataDf 包含所有数据的dict，其中每一个category是一个df
        """
        self.initialCash = 50000
        super(TurtleTrade, self).__init__(feed, self.initialCash)
        self.feed = feed
        if isinstance(instruments, list):  # 对于不是多个品种的情况，进行判断，如果是字符串，用list包裹在存储
            self.instruments = instruments
        else:
            self.instruments = [instruments]
        self.atrPeriod = atrPeriod
        self.short = short  # * 300  # 测试
        self.long = long  # * 300  # 测试
        self.dictOfDateDf = dictOfDataDf
        self.context = context
        self.generalTickInfo = pd.read_csv('../general_ticker_info.csv')
        self.openPriceAndATR = {}  # 用于记录每个品种的开仓价格与当时的atr
        self.equity = 0
        self.tech = {}
        # self.max = 0  # 用来存储最大的历史数据有多长， 以计算此时到了哪一根k线，以方便用 -(self.max - self.i) 来取技术指标
        for instrument in self.instruments:
            atr = talib.ATR(np.array(self.dictOfDateDf[instrument]['High']),
                            np.array(self.dictOfDateDf[instrument]['Low']),
                            np.array(self.dictOfDateDf[instrument]['Close']), self.atrPeriod)  # 返回的ndarray
            long_upper = talib.MAX(np.array(self.dictOfDateDf[instrument]['High']), self.long)
            long_lower = talib.MIN(np.array(self.dictOfDateDf[instrument]['Low']), self.long)
            short_upper = talib.MAX(np.array(self.dictOfDateDf[instrument]['High']), self.short)
            short_lower = talib.MIN(np.array(self.dictOfDateDf[instrument]['Low']), self.short)

            self.tech[instrument] = {'atr': atr, 'long upper': long_upper, 'long lower': long_lower,
                                     'short upper': short_upper, 'short lower': short_lower}
            # if len(atr) > self.max:
            #     self.max = len(atr)

        # self.i = 0  # 计数，用于确定计数指标的位置

    def onBars(self, bars):
        barTime = bars.getDateTime()
        self.equity = self.getBroker().getEquity()
        order = []
        allAtr = {}
        postion = self.getBroker().getPositions()
        readyInstrument = bars.getInstruments()
        for instrument in self.instruments:
            # t1 = time.time()
            # atr = talib.ATR(np.array(self.feed[instrument].getHighDataSeries()),
            #                 np.array(self.feed[instrument].getLowDataSeries()),
            #                 np.array(self.feed[instrument].getCloseDataSeries()), self.atrPeriod)[-1]  # 返回的ndarray
            # if np.isnan(atr):  # 为nan说明数据还不够，不做计算。
            #     continue
            # allAtr[instrument] = atr
            # quantity = self.getQuantity(instrument, atr)
            # long_upper = talib.MAX(np.array(self.feed[instrument].getHighDataSeries()), self.long)
            # long_lower = talib.MIN(np.array(self.feed[instrument].getLowDataSeries()), self.long)
            # short_upper = talib.MAX(np.array(self.feed[instrument].getHighDataSeries()), self.short)
            # short_lower = talib.MIN(np.array(self.feed[instrument].getLowDataSeries()), self.short)

            if instrument not in readyInstrument:  # 如果此时没有这个品种的bar 说明还没开始或者别的品种的夜盘和它时间冲突
                temp = self.dictOfDateDf[instrument][self.dictOfDateDf[instrument]['Date Time'] < barTime]
                if temp.index.empty:  # 如果index是空值，则说明此时这个品种还没有开始有数据
                    i = 0
                else:
                    i = temp.index[-1]  # 有数据，就说明是中间有夜盘时间不对齐的问题，用前一天的atr来代替

                atr = self.tech[instrument]['atr'][i]
                allAtr[instrument] = atr
                # 对于这种取后一天的atr来假装，避免后面取atr 之前开仓所以有持仓，但此时没有atr的报错
                continue
            i = self.dictOfDateDf[instrument][self.dictOfDateDf[instrument]['Date Time'] == barTime].index[0]
            atr = self.tech[instrument]['atr'][i]  # * 50#测试
            allAtr[instrument] = atr

            if np.isnan(atr):  # 为nan说明数据还不够，不做计算。
                continue

            #  找到这个时间在df中的位置
            quantity = self.getQuantity(instrument, atr)
            long_upper = self.tech[instrument]['long upper'][i-1:i + 1]  # 取出到此时的最后两个
            long_lower = self.tech[instrument]['long lower'][i-1:i + 1]
            short_lower = self.tech[instrument]['short lower'][i-1:i + 1]
            short_upper = self.tech[instrument]['short upper'][i-1:i + 1]
            # t2 = time.time()
            # print(t2 - t1)
            # 开仓。
            if long_upper[-1] > long_upper[-2] and postion.get(instrument, 0) == 0:  # 当期上界变高表示创新高，新低同理
                ret = self.getBroker().createMarketOrder(broker.Order.Action.BUY, instrument, quantity)
                self.openPriceAndATR[instrument] = [bars.getBar(instrument).getClose(), atr]  # 默认以收盘价开仓
                print('open long')
                print(bars.getDateTime())
                print(instrument)
                print(postion)
                order.append(ret)

            elif long_lower[-1] < long_lower[-2] and postion.get(instrument, 0) == 0:
                ret = self.getBroker().createMarketOrder(broker.Order.Action.SELL_SHORT, instrument, quantity)
                self.openPriceAndATR[instrument] = [bars.getBar(instrument).getClose(), atr]  # 默认以收盘价开仓
                print('open short')
                print(bars.getDateTime())
                print(instrument)
                print(postion)
                order.append(ret)
            # 平仓
            elif short_upper[-1] > short_upper[-2] and postion.get(instrument, 0) < 0:  # 平空
                ret = self.getBroker().createMarketOrder(broker.Order.Action.BUY_TO_COVER, instrument,
                                                         abs(postion[instrument]))
                print('close short')
                print(bars.getDateTime())
                print(instrument)
                print(postion)
                order.append(ret)
                self.openPriceAndATR.pop(instrument)  # 去掉指定的持仓


            elif short_lower[-1] < short_lower[-2] and postion.get(instrument, 0) > 0:  # 平多
                ret = self.getBroker().createMarketOrder(broker.Order.Action.SELL, instrument, abs(postion[instrument]))
                print('close long')
                print(bars.getDateTime())
                print(instrument)
                print(postion)
                order.append(ret)
                self.openPriceAndATR.pop(instrument)  # 去掉指定的持仓

            # 加仓 或止损
            elif instrument in self.openPriceAndATR:  # 表示已有持仓
                if postion.get(instrument, 0) > 0:  # 持有多仓
                    if self.openPriceAndATR[instrument][0] + 0.5 * atr < bars.getBar(instrument).getClose():
                        # 且价格超过了上次开仓价加0.5atr在加仓
                        ret = self.getBroker().createMarketOrder(broker.Order.Action.BUY, instrument,
                                                                 quantity)
                        self.openPriceAndATR[instrument][0] = bars.getBar(instrument).getClose()
                        print('add long')
                        print(bars.getDateTime())
                        print(instrument)
                        print(postion)
                        order.append(ret)

                    elif self.openPriceAndATR[instrument][0] - 0.5 * atr > bars.getBar(instrument).getClose():
                        # 且价格小于了上次开仓价减0.5atr，则止损
                        ret = self.getBroker().createMarketOrder(broker.Order.Action.SELL, instrument,
                                                                 abs(postion[instrument]))
                        self.openPriceAndATR.pop(instrument)
                        print('stop long')
                        print(bars.getDateTime())
                        print(instrument)
                        print(postion)
                        order.append(ret)

                elif postion.get(instrument, 0) < 0:  # 持有空仓
                    if self.openPriceAndATR[instrument][0] - 0.5 * atr > bars.getBar(instrument).getClose():
                        # 且价格超过了开仓价加0.5atr 则加空
                        ret = self.getBroker().createMarketOrder(broker.Order.Action.SELL_SHORT, instrument,
                                                                 quantity)
                        self.openPriceAndATR[instrument][0] = bars.getBar(instrument).getClose()
                        print('add short')
                        print(bars.getDateTime())
                        print(instrument)
                        print(postion)
                        order.append(ret)

                    elif self.openPriceAndATR[instrument][0] + 0.5 * atr < bars.getBar(instrument).getClose():
                        # 且价格大于了上次开仓价加0.5atr，则止损
                        ret = self.getBroker().createMarketOrder(broker.Order.Action.BUY_TO_COVER, instrument,
                                                                 abs(postion[instrument]))
                        self.openPriceAndATR.pop(instrument)
                        print('stop short')
                        print(bars.getDateTime())
                        print(instrument)
                        print(postion)
                        order.append(ret)
            # t3 = time.time()
            # print(t3 - t2)

        # t3 = time.time()
        allPos = 0
        for instrument in postion:
            allPos += round(postion[instrument] / self.getQuantity(instrument, allAtr[instrument]))
            # 看某个品种有多少个单位的持仓，按照现在的atr来计算
        allPos = abs(allPos)
        if allPos >= 10:
            open_mark = False  # 达到10个单位，不再开仓
        else:
            open_mark = True

        for item in order:
            item.setGoodTillCanceled(True)
            item.setAllOrNone(True)
            action = item.getAction()
            if action == broker.Order.Action.SELL or action == broker.Order.Action.BUY_TO_COVER:  # 平仓的都可以
                self.getBroker().submitOrder(item)
            else:  # 开仓的情况
                if open_mark:
                    ins = item.getInstrument()
                    exist = round(postion.get(ins, 0) / self.getQuantity(ins, allAtr[ins]))
                    if exist <= 3:  # 如果单个品种小于3个单位的持仓，就可以开
                        self.getBroker().submitOrder(item)
                        allPos += 1
                    if allPos >= 10:
                        open_mark = False
        # self.i += 1  # 自增以移向下一个计数指标的值
        t4 = time.time()
        # print(t4 - t3)

    def getQuantity(self, instrument, atr):
        """
        计算此时可以开多少张
        :return:
        """

        # quantity = self.equity
        quantity = self.initialCash  # 测试, 固定资产开仓，不随资产增长，避免回测到后期钱太多的问题

        KQFileName = self.context.categoryToFile[instrument]

        KQmultiplier = \
            self.generalTickInfo.loc[self.generalTickInfo['index_name'] == KQFileName, 'contract_multiplier'].iloc[0]

        # res = int(quantity / atr / 100 / KQmultiplier)  # 向下取整
        res = int(quantity / atr / 100)  # 由于目前回测系统没有考虑合约乘数，不需要除以合约乘数

        if res:
            return res
        else:
            return 1  # 至少开1手
        # 账户的1%的权益，除去atr值，再除去合约乘数，即得张数。表示一个atr的标准波动让账户的权益变动1%


class SmaTurtleTrade(YhlzStreategy):
    """
    海龟交易策略
    """

    def __init__(self, feed, instruments, context, dictOfDataDf, atrPeriod=20, short=108, long=694):
        """
        初始化
        :parm feed pyalgotrade 的feed对象，装了所有csv数据。类似于dict可以用中括号取值。
        :parm instrument 包含所有category的list，用的是简写，如‘rb’，‘ag’
        :param context context 对象，装所有变量
        :parm atrPeriod atr的周期
        :parm short 唐奇安通道的短期
        :parm long 唐奇安通道的长期
        :parm dictOfDataDf 包含所有数据的dict，其中每一个category是一个df
        """
        super(SmaTurtleTrade, self).__init__(feed, 10000)
        self.feed = feed
        if isinstance(instruments, list):  # 对于不是多个品种的情况，进行判断，如果是字符串，用list包裹在存储
            self.instruments = instruments
        else:
            self.instruments = [instruments]
        self.atrPeriod = atrPeriod
        self.short = short  # * 300  # 测试
        self.long = long  # * 300  # 测试
        self.dictOfDateDf = dictOfDataDf
        self.context = context
        self.generalTickInfo = pd.read_csv('../general_ticker_info.csv')
        self.openPriceAndATR = {}  # 用于记录每个品种的开仓价格与当时的atr
        self.tech = {}
        # self.max = 0  # 用来存储最大的历史数据有多长， 以计算此时到了哪一根k线，以方便用 -(self.max - self.i) 来取技术指标
        for instrument in self.instruments:
            atr = talib.ATR(np.array(self.dictOfDateDf[instrument]['High']),
                            np.array(self.dictOfDateDf[instrument]['Low']),
                            np.array(self.dictOfDateDf[instrument]['Close']), self.atrPeriod)  # 返回的ndarray
            long = talib.SMA(np.array(self.dictOfDateDf[instrument]['Close']), self.long)
            short = talib.SMA(np.array(self.dictOfDateDf[instrument]['Close']), self.short)

            self.tech[instrument] = {'atr': atr, 'long': long,
                                     'short': short}
            # if len(atr) > self.max:
            #     self.max = len(atr)

        # self.i = 0  # 计数，用于确定计数指标的位置

    def onBars(self, bars):
        barTime = bars.getDateTime()
        self.equity = self.getBroker().getEquity()
        order = []
        allAtr = {}
        postion = self.getBroker().getPositions()
        readyInstrument = bars.getInstruments()
        for instrument in self.instruments:
            # t1 = time.time()
            # atr = talib.ATR(np.array(self.feed[instrument].getHighDataSeries()),
            #                 np.array(self.feed[instrument].getLowDataSeries()),
            #                 np.array(self.feed[instrument].getCloseDataSeries()), self.atrPeriod)[-1]  # 返回的ndarray
            # if np.isnan(atr):  # 为nan说明数据还不够，不做计算。
            #     continue
            # allAtr[instrument] = atr
            # quantity = self.getQuantity(instrument, atr)
            # long_upper = talib.MAX(np.array(self.feed[instrument].getHighDataSeries()), self.long)
            # long_lower = talib.MIN(np.array(self.feed[instrument].getLowDataSeries()), self.long)
            # short_upper = talib.MAX(np.array(self.feed[instrument].getHighDataSeries()), self.short)
            # short_lower = talib.MIN(np.array(self.feed[instrument].getLowDataSeries()), self.short)

            if instrument not in readyInstrument:  # 如果此时没有这个品种的bar 说明还没开始或者别的品种的夜盘和它时间冲突
                temp = self.dictOfDateDf[instrument][self.dictOfDateDf[instrument]['Date Time'] < barTime]
                if temp.index.empty:  # 如果index是空值，则说明此时这个品种还没有开始有数据
                    i = 0
                else:
                    i = temp.index[-1]  # 有数据，就说明是中间有夜盘时间不对齐的问题，用前一天的atr来代替

                atr = self.tech[instrument]['atr'][i] * 10 #测试
                allAtr[instrument] = atr
                # 对于这种取后一天的atr来假装，避免后面取atr 之前开仓所以有持仓，但此时没有atr的报错
                continue
            i = self.dictOfDateDf[instrument][self.dictOfDateDf[instrument]['Date Time'] == barTime].index[0]
            atr = self.tech[instrument]['atr'][i]  # * 50#测试
            allAtr[instrument] = atr

            if np.isnan(atr):  # 为nan说明数据还不够，不做计算。
                continue

            #  找到这个时间在df中的位置
            quantity = self.getQuantity(instrument, atr)
            long = self.tech[instrument]['long'][i-1:i + 1]  # 取出到此时的最后两个
            short = self.tech[instrument]['short'][i-1:i + 1]
            # t2 = time.time()
            # print(t2 - t1)
            # 开仓。
            if long[-1] < short[-1] and long[-2] > short[-2] and postion.get(instrument, 0) == 0:  # 当期上界变高表示创新高，新低同理
                ret = self.getBroker().createMarketOrder(broker.Order.Action.BUY, instrument, quantity)
                if instrument in postion:
                    ret1 = self.getBroker().createMarketOrder(broker.Order.Action.BUY_TO_COVER, instrument, postion[instrument])
                    order.append(ret1)
                self.openPriceAndATR[instrument] = [bars.getBar(instrument).getClose(), atr]  # 默认以收盘价开仓
                print('long')
                print(bars.getDateTime())
                print(instrument)
                order.append(ret)

            elif short[-1] < long[-1] and long[-2] < short[-2] and postion.get(instrument, 0) == 0:
                ret = self.getBroker().createMarketOrder(broker.Order.Action.SELL_SHORT, instrument, quantity)
                if instrument in postion:
                    ret1 = self.getBroker().createMarketOrder(broker.Order.Action.SELL, instrument, postion[instrument])
                    order.append(ret1)
                self.openPriceAndATR[instrument] = [bars.getBar(instrument).getClose(), atr]  # 默认以收盘价开仓
                print('short')
                print(bars.getDateTime())
                print(instrument)
                order.append(ret)


            # 加仓 或止损
            elif instrument in self.openPriceAndATR:  # 表示已有持仓
                if postion.get(instrument, 0) > 0:  # 持有多仓
                    if self.openPriceAndATR[instrument][0] + 0.5 * atr < bars.getBar(instrument).getClose():
                        # 且价格超过了上次开仓价加0.5atr在加仓
                        ret = self.getBroker().createMarketOrder(broker.Order.Action.BUY, instrument,
                                                                 quantity)
                        self.openPriceAndATR[instrument][0] = bars.getBar(instrument).getClose()
                        print('add long')
                        print(bars.getDateTime())
                        print(instrument)
                        order.append(ret)

                    elif self.openPriceAndATR[instrument][0] - 0.5 * atr > bars.getBar(instrument).getClose():
                        # 且价格小于了上次开仓价减0.5atr，则止损
                        ret = self.getBroker().createMarketOrder(broker.Order.Action.SELL, instrument,
                                                                 abs(postion[instrument]))
                        self.openPriceAndATR.pop(instrument)
                        print('stop long')
                        print(bars.getDateTime())
                        print(instrument)
                        order.append(ret)

                elif postion.get(instrument, 0) < 0:  # 持有空仓
                    if self.openPriceAndATR[instrument][0] - 0.5 * atr > bars.getBar(instrument).getClose():
                        # 且价格超过了开仓价加0.5atr 则加空
                        ret = self.getBroker().createMarketOrder(broker.Order.Action.SELL_SHORT, instrument,
                                                                 quantity)
                        self.openPriceAndATR[instrument][0] = bars.getBar(instrument).getClose()
                        print('add short')
                        print(bars.getDateTime())
                        print(instrument)
                        order.append(ret)

                    elif self.openPriceAndATR[instrument][0] + 0.5 * atr < bars.getBar(instrument).getClose():
                        # 且价格大于了上次开仓价加0.5atr，则止损
                        ret = self.getBroker().createMarketOrder(broker.Order.Action.BUY_TO_COVER, instrument,
                                                                 abs(postion[instrument]))
                        self.openPriceAndATR.pop(instrument)
                        print('stop short')
                        print(bars.getDateTime())
                        print(instrument)
                        order.append(ret)
            # t3 = time.time()
            # print(t3 - t2)

        # t3 = time.time()
        allPos = 0
        for instrument in postion:
            allPos += round(postion[instrument] / self.getQuantity(instrument, allAtr[instrument]))
            # 看某个品种有多少个单位的持仓，按照现在的atr来计算
        if allPos >= 10:
            open_mark = False  # 达到10个单位，不再开仓
        else:
            open_mark = True

        for item in order:
            item.setGoodTillCanceled(True)
            item.setAllOrNone(True)
            action = item.getAction()
            if action == broker.Order.Action.SELL or action == broker.Order.Action.BUY_TO_COVER:  # 平仓的都可以
                self.getBroker().submitOrder(item)
            else:  # 开仓的情况
                if open_mark:
                    ins = item.getInstrument()
                    exist = round(postion.get(ins, 0) / self.getQuantity(ins, allAtr[ins]))
                    if exist <= 3:  # 如果单个品种小于3个单位的持仓，就可以开
                        self.getBroker().submitOrder(item)
                        allPos += 1
                    if allPos >= 10:
                        open_mark = False
        # self.i += 1  # 自增以移向下一个计数指标的值
        t4 = time.time()
        # print(t4 - t3)

    def getQuantity(self, instrument, atr):
        """
        计算此时可以开多少张
        :return:
        """

        quantity = self.equity
        # quantity = 1000000 测试

        KQFileName = self.context.categoryToFile[instrument]

        KQmultiplier = \
            self.generalTickInfo.loc[self.generalTickInfo['index_name'] == KQFileName, 'contract_multiplier'].iloc[0]

        # res = int(quantity / atr / 100 / KQmultiplier)  # 向下取整
        res = int(quantity / atr / 100 / 20)  # 由于目前回测系统没有考虑合约乘数，不需要除以合约乘数

        if res:
            return res
        else:
            return 1  # 至少开1手
        # 账户的1%的权益，除去atr值，再除去合约乘数，即得张数。表示一个atr的标准波动让账户的权益变动1%