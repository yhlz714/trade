"""
strategy file ,include all strategy nothing else
Version = 1.0
"""


from pyalgotrade import strategy
from pyalgotrade.technical import ma
from pyalgotrade.technical import cross
from pyalgotrade import broker
import talib
import pandas as pd


class SMACrossOver(strategy.BacktestingStrategy):

    def __init__(self, feed, instrument, smaPeriod, dictOfDataDf):
        super(SMACrossOver, self).__init__(feed)
        self.__instrument = instrument
        self.__position = None
        self.prices = feed[instrument].getPriceDataSeries()
        # 这个策略只有一个品种，所以pop出来必然是那个。pop后这个键值对就不存在，不能取两次
        length = len(dictOfDataDf[list(dictOfDataDf.keys())[0]])  #拿出第一个df的长度
        self.sma = ma.SMA(self.prices, 108, maxLen=length)
        self.sma1 = ma.SMA(self.prices, 694, maxLen=length)
        self.tech = {'sma short':self.sma,'sma long':self.sma1}


    def getSMA(self):
        return self.sma


    def onBars(self, bars):


        quantity=100
        if cross.cross_above( self.sma, self.sma1) > 0:
            if self.getBroker().getShares(self.__instrument)!=0:
                ret=self.getBroker().createMarketOrder(broker.Order.Action.BUY_TO_COVER,self.__instrument,quantity)
                self.getBroker().submitOrder(ret)
            ret=self.getBroker().createMarketOrder(broker.Order.Action.BUY, self.__instrument,quantity)
            self.getBroker().submitOrder(ret)
            #print(bars.getDateTime())
        elif cross.cross_below(self.sma, self.sma1) > 0:
            if self.getBroker().getShares(self.__instrument)!=0:
                ret=self.getBroker().createMarketOrder(broker.Order.Action.SELL, self.__instrument,quantity)
                self.getBroker().submitOrder(ret)
            ret=self.getBroker().createMarketOrder(broker.Order.Action.SELL_SHORT, self.__instrument,quantity)
            self.getBroker().submitOrder(ret)


class TurtleTrade(strategy.BacktestingStrategy):
    """
    海龟交易策略
    """
    def __init__(self, feed, instruments, context, dictOfDataDf,  atrPeriod=20, short=20, long=55):
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
        super(TurtleTrade).__init__(feed)
        self.feed = feed
        self.instruments = instruments
        self.atrPeriod = atrPeriod
        self.short = short
        self.long = long
        self.dictOfDateDf = dictOfDataDf
        self.context = context
        self.generalTickInfo = pd.read('../general_tiker_info.csv')


    def onBars(self, bars):
        order = []

        for instrument in self.instruments:

            quantity = self.getQuantity()
            long_upper = talib.MAX(self.feed[instrument].getHighDataSeries(), self.long)
            long_lowwer = talib.MIN(self.feed[instrument].getLowDataSeries(), self.long)
            short_upper = talib.MAX(self.feed[instrument].getHighDataSeries(), self.short)
            short_lower = talib.MAX(self.feed[instrument].getLowDataSeries(), self.short)

            high = self.feed[instrument].getHighDataSeries()
            low = self.feed[instrument].getLowDataSeries()

            # 开仓。
            if long_upper[-1] > long_upper[-2] and 'no position':  #当期上届变高表示创新高，新低同理
                ret = self.getBroker().createMarketOrder(broker.Order.Action.BUY, instrument, quantity)
                order.append(ret)
            elif long_lowwer[-1] < long_lowwer[-2] and 'no position' :
                ret = self.getBroker().createMarketOrder(broker.Order.Action.SELL_SHORT, instrument, quantity)
                order.append(ret)
            # 平仓
            elif short_upper[-1] > short_upper[-2] and 'have short':  #平空
                ret = self.getBroker().createMarketOrder(broker.Order.Action.BUY_TO_COVER, instrument, quantity)
            elif short_lower[-1] < short_lower[-2] and 'have long':  #平多
                ret = self.getBroker().createMarketOrder(broker.Order.Action.SELL, instrument, quantity)

        # TODO 此处还需要根据此时的持仓情况判断单是否可以发
        for item in order:
            self.getBroker().submitOrder(item)


    def getQuantity(self, instrument):
        """
        计算此时可以开多少张
        :return:
        """
        quantity = '获取账户资产'
        atr = talib.ATR(self.feed[instrument].getHighDataSeries(), self.feed[instrument].getLowDataSeries(),
                  self.feed[instrument].getCloseDataSeries(), self.atrPeriod)
        KQname = self.context.categoryToFile[instrument]
        for i in range(self.generalTickInfo.shap[0]):
            if self.generalTickInfo.loc[i, 'index_name'].replace('.', '') == KQname:
                KQmultiplier = self.generalTickInfo.loc[i, 'contract_multiplier']
        return quantity / atr[-1] / 100 * KQmultiplier #账户的1%的权益，除去atr值，再除去合约乘数，即得张数。

