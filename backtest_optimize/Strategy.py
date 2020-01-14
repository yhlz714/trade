"""
strategy file ,include all strategy nothing else
Version = 1.0
"""


from pyalgotrade import strategy
from pyalgotrade.technical import ma
from pyalgotrade.technical import cross
from pyalgotrade import broker


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
    def __init__(self, feed, instrument, atrPeriod, short, long, dictOfDataDf):
        """
        初始化
        :parm feed pyalgotrade 的feed对象，装了所有csv数据。类似于dict可以用中括号取值。
        :parm instrument 包含所有category的list，用的是简写，如‘rb’，‘ag’
        :parm atrPeriod atr的周期
        :parm short 唐奇安通道的短期
        :parm long 唐奇安通道的长期
        :parm dictOfDataDf 包含所有数据的dict，其中每一个category是一个df
        """
        super(TurtleTrade).__init__(feed)
        self.feed = feed
        self.instruments = instrument
        self.atrPeriod = atrPeriod
        self.short = short
        self.long = long
        self.dictOfDateDf = dictOfDataDf


    def onBars(self, bars):
        order = []

        for instrument in self.instruments:

            quantity = self.getQuantity()
            upper = MAX(self.feed['instrument'].getHighDataSeries())
            lowwer = MIN(self.feed['instrument'].getLowDataSeries())

            #开仓。
            if bars.getBar(instrument=instrument).getClose() > upper:
                ret = self.getBroker().createMarketOrder(broker.Order.Action.BUY, instrument, quantity)
                order.append(ret)
            elif bars.getBar(instrument=instrument).getClose() < lowwer:
                ret = self.getBroker().createMarketOrder(broker.Order.Action.SELL, instrument, quantity)
                order.append(ret)
            #TODO 平仓加仓的情况

        for item in order:
            self.getBroker().submitOrder(item)



    def getQuantity(self):
        atr = ATR()
        self.getBroker().getCash() / atr

