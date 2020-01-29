"""
strategy file ,include all strategy nothing else
Version = 1.0
"""

import time
from pyalgotrade import strategy
from pyalgotrade.technical import ma
from pyalgotrade.technical import cross
from pyalgotrade import broker
import talib
import pandas as pd
import numpy as np


class SMACrossOver(strategy.BacktestingStrategy):

    def __init__(self, feed, instrument, context, dictOfDataDf):
        super(SMACrossOver, self).__init__(feed)
        self.__instrument = instrument
        self.__position = None
        self.prices = feed[instrument].getPriceDataSeries()
        # 这个策略只有一个品种，所以pop出来必然是那个。pop后这个键值对就不存在，不能取两次
        length = len(dictOfDataDf[list(dictOfDataDf.keys())[0]])  # 拿出第一个df的长度
        self.sma = ma.SMA(self.prices, 108, maxLen=length)
        self.sma1 = ma.SMA(self.prices, 694, maxLen=length)
        self.tech = {'sma short': self.sma, 'sma long': self.sma1}

    def getSMA(self):
        return self.sma

    def onBars(self, bars):

        quantity = 100
        print('zxc')
        if cross.cross_above(self.sma, self.sma1) > 0:
            if self.getBroker().getShares(self.__instrument) != 0:
                ret = self.getBroker().createMarketOrder(broker.Order.Action.BUY_TO_COVER, self.__instrument, quantity)
                self.getBroker().submitOrder(ret)
            ret = self.getBroker().createMarketOrder(broker.Order.Action.BUY, self.__instrument, quantity)
            self.getBroker().submitOrder(ret)
            # print(bars.getDateTime())
        elif cross.cross_below(self.sma, self.sma1) > 0:
            if self.getBroker().getShares(self.__instrument) != 0:
                ret = self.getBroker().createMarketOrder(broker.Order.Action.SELL, self.__instrument, quantity)
                self.getBroker().submitOrder(ret)
            ret = self.getBroker().createMarketOrder(broker.Order.Action.SELL_SHORT, self.__instrument, quantity)
            self.getBroker().submitOrder(ret)


class TurtleTrade(strategy.BacktestingStrategy):
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
        super(TurtleTrade, self).__init__(feed)
        self.feed = feed
        if isinstance(instruments, list):  # 对于不是多个品种的情况，进行判断，如果是字符串，用list包裹在存储
            self.instruments = instruments
        else:
            self.instruments = [instruments]
        self.atrPeriod = atrPeriod
        self.short = short #* 300  # 测试
        self.long = long #* 300  # 测试
        self.dictOfDateDf = dictOfDataDf
        self.context = context
        self.generalTickInfo = pd.read_csv('../general_ticker_info.csv')
        self.openPriceAndATR = {}  # 用于记录每个品种的开仓价格与当时的atr
        self.i = 0  # 计数，用于确定计数指标的位置
        self.tech = {}
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

    def onBars(self, bars):
        print(bars.getDateTime())
        self.equity = self.getBroker().getEquity()  # TODO 此处计算的权益是股票的，要改成期货的，否则cash会过少，导致无法开仓。
        order = []
        allAtr = {}
        postion = self.getBroker().getPositions()
        for instrument in self.instruments:
            t1 = time.time()
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

            atr = self.tech[instrument]['atr'][-1]
            if np.isnan(atr):  # 为nan说明数据还不够，不做计算。
                continue
            quantity = self.getQuantity(instrument, atr)
            long_upper = self.tech[instrument]['long upper'][-2:]
            long_lower = self.tech[instrument]['long lower'][-2:]
            short_lower = self.tech[instrument]['short lower'][-2:]
            short_upper = self.tech[instrument]['short upper'][-2:]
            t2 = time.time()
            # print(t2 - t1)
            # 开仓。
            if long_upper[-1] > long_upper[-2] and postion.get(instrument, 0) == 0:  # 当期上界变高表示创新高，新低同理
                ret = self.getBroker().createMarketOrder(broker.Order.Action.BUY, instrument, quantity)
                self.openPriceAndATR[instrument] = [bars.getBar(instrument).getClose(), atr]  # 默认以收盘价开仓
                print('open long')
                print(bars.getDateTime())
                order.append(ret)

            elif long_lower[-1] < long_lower[-2] and postion.get(instrument, 0) == 0:
                ret = self.getBroker().createMarketOrder(broker.Order.Action.SELL_SHORT, instrument, quantity)
                self.openPriceAndATR[instrument] = [bars.getBar(instrument).getClose(), atr]  # 默认以收盘价开仓
                print('open short')
                print(bars.getDateTime())
                order.append(ret)
            # 平仓
            elif short_upper[-1] > short_upper[-2] and postion.get(instrument, 0) < 0:  # 平空
                ret = self.getBroker().createMarketOrder(broker.Order.Action.BUY_TO_COVER, instrument,
                                                         abs(postion[instrument]))
                print('close short')
                print(bars.getDateTime())
                order.append(ret)
                self.openPriceAndATR.pop(instrument)  # 去掉指定的持仓

            elif short_lower[-1] < short_lower[-2] and postion.get(instrument, 0) > 0:  # 平多
                ret = self.getBroker().createMarketOrder(broker.Order.Action.SELL, instrument, abs(postion[instrument]))
                print('close long')
                print(bars.getDateTime())
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
                        order.append(ret)

                    elif self.openPriceAndATR[instrument][0] - 0.5 * atr > bars.getBar(instrument).getClose():
                        # 且价格小于了上次开仓价减0.5atr，则止损
                        ret = self.getBroker().createMarketOrder(broker.Order.Action.SELL, instrument,
                                                                 abs(postion[instrument]))
                        self.openPriceAndATR.pop(instrument)
                        print('stop long')
                        print(bars.getDateTime())
                        order.append(ret)

                elif postion.get(instrument, 0) < 0:  # 持有空仓
                    if self.openPriceAndATR[instrument][0] - 0.5 * atr > bars.getBar(instrument).getClose():
                        # 且价格超过了开仓价加0.5atr 则加空
                        ret = self.getBroker().createMarketOrder(broker.Order.Action.SELL_SHORT, instrument,
                                                                 quantity)
                        self.openPriceAndATR[instrument][0] = bars.getBar(instrument).getClose()
                        print('add short')
                        print(bars.getDateTime())
                        order.append(ret)

                    elif self.openPriceAndATR[instrument][0] + 0.5 * atr < bars.getBar(instrument).getClose():
                        # 且价格大于了上次开仓价加0.5atr，则止损
                        ret = self.getBroker().createMarketOrder(broker.Order.Action.BUY_TO_COVER, instrument,
                                                                 abs(postion[instrument]))
                        self.openPriceAndATR.pop(instrument)
                        print('stop short')
                        print(bars.getDateTime())
                        order.append(ret)
            t3 = time.time()
            # print(t3 - t2)

        t3 = time.time()
        allPos = 0
        for instrument in postion:
            allPos += round(postion[instrument] / self.getQuantity(instrument, allAtr[instrument]))
            # 看某个品种有多少个单位的持仓，按照现在的atr来计算
        if allPos >= 10:
            open_mark = False  # 达到10个单位，不再开仓
        else:
            open_mark = True

        for item in order:
            action = item.getAction()
            if action == broker.Order.Action.SELL or action == broker.Order.Action.BUY_TO_COVER:  # 平仓的都可以
                self.getBroker().submitOrder(item)
            else:  # 开仓的情况
                if open_mark:
                    ins = item.getInstrument()
                    exist = round(postion.get(ins, 0) / self.getQuantity(ins, allAtr[ins]))
                    if exist <= 3:  # 如果单个品种小于3个单位的持仓，就可以开
                        self.getBroker().submitOrder(item)
        self.i += 1  # 自增以移向下一个计数指标的值
        t4 = time.time()
        # print(t4 - t3)

    def getQuantity(self, instrument, atr):
        """
        计算此时可以开多少张
        :return:
        """

        quantity = self.equity

        KQFileName = self.context.categoryToFile[instrument]

        KQmultiplier = \
            self.generalTickInfo.loc[self.generalTickInfo['index_name'] == KQFileName, 'contract_multiplier'].iloc[0]

        res = int(quantity / atr / 100 / KQmultiplier)  # 向下取整

        if res:
            return res / 10  # 测试
        else:
            return 1  # 至少开1手
        # 账户的1%的权益，除去atr值，再除去合约乘数，即得张数。表示一个atr的标准波动让账户的权益变动1%
