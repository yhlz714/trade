"""
all backtest or optimize module in here
"""
import os
import socket
import time
import math
import platform
from tkinter import *
import sqlite3
import traceback

import paramiko
import pandas as pd
import numpy as np
from datetime import datetime

from pyalgotrade.stratanalyzer import returns
from pyalgotrade import broker
from pyalgotrade.stratanalyzer import trades
from pyalgotrade.bar import Frequency
from pyalgotrade.barfeed import csvfeed


class Yhlz_Trade(trades.Trades):
    def __init__(self):
        super(Yhlz_Trade, self).__init__()
        # 记录了所有交易，在最后直接取出就可以了
        self.all_trade = pd.DataFrame(columns=['date', 'instrument', 'action', 'price', 'volume'])
        self.__all = []
        self.__profits = []
        self.__losses = []
        self.__allReturns = []
        self.__positiveReturns = []
        self.__negativeReturns = []
        self.__allCommissions = []
        self.__profitableCommissions = []
        self.__unprofitableCommissions = []
        self.__evenCommissions = []
        self.__evenTrades = 0
        self.__posTrackers = {}
        self.action = {'1': 'BUY',
                       '2': 'BUY_TO_COVER',
                       '3': 'SELL',
                       '4': 'SELL_SHORT'}

    def __updateTrades(self, posTracker):
        price = 0  # The price doesn't matter since the position should be closed.
        assert posTracker.getPosition() == 0
        netProfit = posTracker.getPnL(price)
        netReturn = posTracker.getReturn(price)

        if netProfit > 0:
            self.__profits.append(netProfit)
            self.__positiveReturns.append(netReturn)
            self.__profitableCommissions.append(posTracker.getCommissions())
        elif netProfit < 0:
            self.__losses.append(netProfit)
            self.__negativeReturns.append(netReturn)
            self.__unprofitableCommissions.append(posTracker.getCommissions())
        else:
            self.__evenTrades += 1
            self.__evenCommissions.append(posTracker.getCommissions())

        self.__all.append(netProfit)
        self.__allReturns.append(netReturn)
        self.__allCommissions.append(posTracker.getCommissions())

        posTracker.reset()

    def __updatePosTracker(self, posTracker, price, commission, quantity):
        currentShares = posTracker.getPosition()

        if currentShares > 0:  # Current position is long
            if quantity > 0:  # Increase long position
                posTracker.buy(quantity, price, commission)
            else:
                newShares = currentShares + quantity
                if newShares == 0:  # Exit long.
                    posTracker.sell(currentShares, price, commission)
                    self.__updateTrades(posTracker)
                elif newShares > 0:  # Sell some shares.
                    posTracker.sell(quantity * -1, price, commission)
                else:  # Exit long and enter short. Use proportional commissions.
                    proportionalCommission = commission * currentShares / float(quantity * -1)
                    posTracker.sell(currentShares, price, proportionalCommission)
                    self.__updateTrades(posTracker)
                    proportionalCommission = commission * newShares / float(quantity)
                    posTracker.sell(newShares * -1, price, proportionalCommission)
        elif currentShares < 0:  # Current position is short
            if quantity < 0:  # Increase short position
                posTracker.sell(quantity * -1, price, commission)
            else:
                newShares = currentShares + quantity
                if newShares == 0:  # Exit short.
                    posTracker.buy(currentShares * -1, price, commission)
                    self.__updateTrades(posTracker)
                elif newShares < 0:  # Re-buy some shares.
                    posTracker.buy(quantity, price, commission)
                else:  # Exit short and enter long. Use proportional commissions.
                    proportionalCommission = commission * currentShares * -1 / float(quantity)
                    posTracker.buy(currentShares * -1, price, proportionalCommission)
                    self.__updateTrades(posTracker)
                    proportionalCommission = commission * newShares / float(quantity)
                    posTracker.buy(newShares, price, proportionalCommission)
        elif quantity > 0:
            posTracker.buy(quantity, price, commission)
        else:
            posTracker.sell(quantity * -1, price, commission)

    def __onOrderEvent(self, broker_, orderEvent):
        # Only interested in filled or partially filled orders.
        if orderEvent.getEventType() not in (broker.OrderEvent.Type.PARTIALLY_FILLED, broker.OrderEvent.Type.FILLED):
            return

        order = orderEvent.getOrder()
        # Get or create the tracker for this instrument.
        try:
            posTracker = self.__posTrackers[order.getInstrument()]
        except KeyError:
            posTracker = returns.PositionTracker(order.getInstrumentTraits())
            self.__posTrackers[order.getInstrument()] = posTracker

        # Update the tracker for this order.
        execInfo = orderEvent.getEventInfo()
        price = execInfo.getPrice()
        commission = execInfo.getCommission()
        action = order.getAction()
        if action in [broker.Order.Action.BUY, broker.Order.Action.BUY_TO_COVER]:
            quantity = execInfo.getQuantity()
        elif action in [broker.Order.Action.SELL, broker.Order.Action.SELL_SHORT]:
            quantity = execInfo.getQuantity() * -1
        else:  # Unknown action
            assert (False)
        self.__updatePosTracker(posTracker, price, commission, quantity)
        self.all_trade.loc[len(self.all_trade), :] = [order.getSubmitDateTime(), order.getInstrument(),
                                                      self.action[str(order.getAction())],
                                                      order.getAvgFillPrice(), order.getQuantity()]

    def attached(self, strat):
        strat.getBroker().getOrderUpdatedEvent().subscribe(self.__onOrderEvent)


class DATA:
    """
    用于从服务器获取数据
    """

    # ------------------------------SSH
    def __init__(self, context, ip='106.52.184.131', port=31500, name='ubuntu', password='86888196'):
        self.__port = port
        self.__ip = ip
        self.__username = name
        self.__password = password
        self.context = context

    def call_back(self, size1, size2):  # use to print how many already download
        print(size1, size2)

    def start_server(self, server):
        """
        启动服务器的文件服务程序
        :return:
        """
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())  # 用于确保第一次连接不会出错
            ssh.connect(self.__ip, 22, self.__username, self.__password)
            stdin, stdout, stderr = ssh.exec_command("nohup python3 " + server + " &")
            # print(stdout.read().decode('utf-8'))
        except Exception as e:
            print(e)
            ssh.close()
            return
        ssh.close()
        time.sleep(0.5)  # wait for server running
        # ------------------------------SSH finished

    # ------------------------------get csv file from server
    def get_csv(self, start_time='1970/01/01', end_time=datetime.fromtimestamp(time.time()).strftime('%Y/%m/%d %H:%M'),
                contract='KQ.i@SHFE.rb'):  # defult end is now
        '''
        下载服务器处理好的csv文件
        '''
        address = (self.__ip, self.__port)
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.connect(address)
            s.send(bytes(str(start_time), encoding='utf-8'))
            if s.recv(512) == b'r':  # mean start received
                s.send(bytes(str(end_time), encoding='utf-8'))
                if s.recv(512) == b'r':  # mean end received
                    s.send(bytes(str(contract), encoding='utf-8'))
        except Exception as e:
            print(e)
            s.close()
            return
        while True:  # wait for file ready and download it
            mes = s.recv(512)
            if mes.decode() == 'd':  # mean file is ready
                try:
                    trans = paramiko.Transport((self.__ip, 22))
                    trans.connect(username=self.__username, password=self.__password)
                    sftp = paramiko.SFTPClient.from_transport(trans)
                    sftp.get('/home/ubuntu/temp.csv', './' + str(contract).replace('.', '') + '.csv', self.call_back)
                except Exception as e:
                    print(e)
                    trans.close()
                    return
                trans.close()
                break
            time.sleep(0.5)
        s.close()

    def close_server(self):
        """
        关闭文件服务程序
        :return:
        """
        address = (self.__ip, self.__port)
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect(address)
        s.send('q'.encode())  # close server

    def checkDataUpdate(self):
        """
        用于从服务器上面检查是否有数据更新，如果有就下载然后更新到本地数据库
        :param data 一个Yhlz_Module的DATA类对象。用于用于操作数据。
        """
        if platform.system() == 'Linux':  # 不同平台ping的方法不一样，返回0就是对的
            temp = os.system('ping -c 4 106.52.184.131')
        else:
            temp = os.system('ping 106.52.184.131')

        if temp == 0:
            os.system('del future_data.db.bak')  # 备份
            os.system('copy future_data.db future_data.db.bak')
            conn = sqlite3.connect('./future_data.db')
            c = conn.cursor()
            general_tick_info = pd.read_csv('../general_ticker_info.csv')

            self.start_server('server_new.py')

            # 用于主力合约。
            # for item in general_tick_info.contract_name:
            #     a = c.execute('SELECT DATETIME FROM [' + item + '] ORDER BY DATETIME DESC LIMIT 1')
            #     for i in a:
            #         if i[0] < time.time():  # 小于当前时间
            #             start_time = i[0] * 1000000000  # 服务器上存储的比本地时间戳多9个0
            #             end_time = time.time() * 1000000000
            #             self.get_csv(start_time=str(start_time), end_time=str(end_time), contract=item)
            #             file = pd.read_csv(str(item).replace('.', '') + '.csv')
            #             file['datetime'] = file['datetime'] / 1000000000
            #             file.to_sql(item, conn, if_exists='append', index=False)
            #             os.remove(str(item).replace('.', '') + '.csv')

            for item in general_tick_info.index_name:
                a = c.execute(
                    'SELECT [DATE TIME] FROM [' + item.replace('.', '') + '] ORDER BY [DATE TIME] DESC LIMIT 1')
                for i in a:
                    start_time = pd.to_datetime(i[0]).timestamp()
                    if start_time < time.time():  # 小于当前时间
                        start_time = datetime.fromtimestamp(start_time).strftime('%Y/%m/%d %H:%M')
                        end_time = datetime.fromtimestamp(time.time()).strftime('%Y/%m/%d %H:%M')
                        self.get_csv(start_time=start_time, end_time=end_time, contract=item)
                        file = pd.read_csv(str(item).replace('.', '') + '.csv')
                        file.to_sql(item.replace('.', ''), conn, if_exists='append', index=False)
                        os.remove(str(item).replace('.', '') + '.csv')

            self.close_server()
            conn.commit()
            conn.close()
        else:
            print('network error, data not update!')

    def feed(self, day=False):  # can also use other file if exist
        '''
        通过本地数据库文件读出csv，创建创建数据源对象
        遍历context的category给所有品种读入数据
        :param day 如果为真，使用日线数据。
        '''
        conn = sqlite3.connect('./future_data.db')
        Data = {}
        res = csvfeed.GenericBarFeed(Frequency.MINUTE, maxLen=2000000)

        if day:
            res.setDateTimeFormat('%Y-%m-%d')
        else:
            res.setDateTimeFormat('%Y-%m-%d %H:%M:%S')

        for category in self.context.categorys:
            file = pd.read_sql('SELECT * FROM [' + self.context.categoryToFile[category] + '] ', conn,
                               parse_dates=['Date Time'])
            # file = file.loc[file['Date Time'] > '2018', :].reset_index(drop=True)  # 测试
            if day:
                file = self._resample(file, 'D')
            file.to_csv('temp.csv', index=False)

            res.addBarsFromCSV(category, 'temp.csv')
            Data[category] = file

        os.remove('temp.csv')
        conn.close()
        return Data, res

    def _resample(self, fileDf: pd.DataFrame(), frequency) -> pd.DataFrame():
        """
        对从数据库里面读取的数据重新采样
        :param fileDf: df
        :param frequency: str 频率
        :return:
        """
        fileDf.set_index('Date Time', inplace=True)
        tempDf = pd.DataFrame()
        tempDf['Open'] = fileDf.resample(frequency).first()['Open']
        tempDf['High'] = fileDf.resample(frequency).max()['High']
        tempDf['Low'] = fileDf.resample(frequency).min()['Low']
        tempDf['Close'] = fileDf.resample(frequency).last()['Close']
        tempDf['Volume'] = fileDf.resample(frequency).sum()['Volume']
        tempDf['Adj Close'] = 0
        tempDf.index = fileDf.resample(frequency).first().index
        tempDf = tempDf.loc[pd.notna(tempDf['Open'])]
        return tempDf.reset_index()


class Kline:

    def __init__(self, canvas, scrollbar, v, Data=None, instrument='rb'):
        """
        画k线图类
        :param canvas: 画布widget
        :param scrollbar: 滚动条widget
        :param v: label的显示字符串变量
        :param data: 包含某个品种的所有数据的df，列应该有'Datetime','Open','High','Low','Close','Adjclose'
        """
        self.v = v
        self.canvas = canvas
        self.canvas.focus_set()
        self.canvas.width = int(self.canvas['width'])  # 将固定的宽度和高度变为属性,本来是str 需要int强制转换
        self.canvas.height = int(self.canvas['height'])  # 如果发生<Configure>事件，也可以修改这两个
        self.scrollbar = scrollbar
        self.instrument = instrument  # 默认画rb的图，用来标识现在画哪个的图。
        self.Data = Data
        self.addData(Data)
        self.tech = {}

        self.num = 200  # 默认画的k线数目
        self.place = -1
        self.item = []  # 装所有的create的名字
        self.crossItem = []  # croosHair 的名字
        self.showCross = False  # 是否显示十字线
        self.dataTemp = pd.DataFrame()  # 用来装当前显示的数据
        self.delta = 2  # 初始k线变动像素
        # 记录了tk里面所有可以用英文表示的颜色。
        self.colors = ['LightPink', 'Pink', 'Crimson', 'LavenderBlush', 'PaleVioletRed', 'HotPink', 'DeepPink',
                       'MediumVioletRed', 'Orchid', 'Thistle', 'Plum', 'Violet', 'Magenta', 'Fuchsia', 'DarkMagenta',
                       'Purple', 'MediumOrchid', 'DarkViolet', 'DarkOrchid', 'Indigo', 'BlueViolet', 'MediumPurple',
                       'MediumSlateBlue', 'SlateBlue', 'DarkSlateBlue', 'Lavender', 'GhostWhite', 'Blue', 'MediumBlue',
                       'MidnightBlue', 'DarkBlue', 'Navy', 'RoyalBlue', 'CornflowerBlue', 'LightSteelBlue',
                       'LightSlateGray', 'SlateGray', 'DodgerBlue', 'AliceBlue', 'SteelBlue', 'LightSkyBlue', 'SkyBlue',
                       'DeepSkyBlue', 'LightBlue', 'PowderBlue', 'CadetBlue', 'Azure', 'LightCyan', 'PaleTurquoise',
                       'Cyan', 'Aqua', 'DarkTurquoise', 'DarkSlateGray', 'DarkCyan', 'Teal', 'MediumTurquoise',
                       'LightSeaGreen', 'Turquoise', 'Aquamarine', 'MediumAquamarine', 'MediumSpringGreen', 'MintCream',
                       'SpringGreen', 'MediumSeaGreen', 'SeaGreen', 'Honeydew', 'LightGreen', 'PaleGreen',
                       'DarkSeaGreen', 'LimeGreen', 'Lime', 'ForestGreen', 'Green', 'DarkGreen', 'Chartreuse',
                       'LawnGreen', 'GreenYellow', 'DarkOliveGreen', 'YellowGreen', 'OliveDrab', 'Beige',
                       'LightGoldenrodYellow', 'Ivory', 'LightYellow', 'Yellow', 'Olive', 'DarkKhaki', 'LemonChiffon',
                       'PaleGoldenrod', 'Khaki', 'Gold', 'Cornsilk', 'Goldenrod', 'DarkGoldenrod', 'FloralWhite',
                       'OldLace', 'Wheat', 'Moccasin', 'Orange', 'PapayaWhip', 'BlanchedAlmond', 'NavajoWhite',
                       'AntiqueWhite', 'Tan', 'BurlyWood', 'Bisque', 'DarkOrange', 'Linen', 'Peru', 'PeachPuff',
                       'SandyBrown', 'Chocolate', 'SaddleBrown', 'Seashell', 'Sienna', 'LightSalmon', 'Coral',
                       'OrangeRed', 'DarkSalmon', 'Tomato', 'MistyRose', 'Salmon', 'Snow', 'LightCoral', 'RosyBrown',
                       'IndianRed', 'Red', 'Brown', 'FireBrick', 'DarkRed', 'Maroon', 'White', 'WhiteSmoke',
                       'Gainsboro',
                       'LightGrey', 'Silver', 'DarkGray', 'Gray', 'DimGray', 'Black']
        self.techAnaly = []  # 用来存放策略所以技术指标的列名
        self.width = 0
        self.height = 0

    def configTechAnaly(self, tech):
        """
        接受所有guiDF要画的技术指标列
        :param args: 元组的列名
        :return:
        """
        self.tech = tech
        self.techAnaly = tech[self.instrument].keys()
        self.draw()

    def addData(self, Data):
        """
        添加或者更改总的数据
        :param guiDF:包含某个品种的所有数据的df，列应该有'Datetime','Open','High','Low','Close','Adjclose'
        :return: None
        """

        self.guiDF = Data[self.instrument]

        self.guiDF['Date Time'] = pd.to_datetime(self.guiDF['Date Time'])
        self.guiDF.sort_values(by=['Date Time'], ascending=False)  # 降序排列

        # 检查是否按照规定顺序排列，以便后面减少计算时间
        order = ['Date Time', 'Open', 'High', 'Low', 'Close', 'Volume', 'Adj Close']

    def draw(self, place=-1):
        """
        在画布上画data数据，每次发生位置变化，或者数据变化，都调用这个函数，然后设置scrollbar的位置
        :param place: 默认从最后也就是1的位置画，函数自动计算从右到左应该画多大的距离,如果place大于1，则表示为绝对位置，在总DF中
        :return: None
        """

        if place == -1:  # 初始值，表示最后的位置
            place = place + len(self.guiDF)

        if self.place == -1:
            self.place = place

        if place <= self.num * 2:  # 确保不会超量程，当为0的时候，place在df的最前，但是还要有两倍self.num个数据，来保证画图
            place = self.num * 2

        dataTemp = self.guiDF.loc[place - 2 * self.num: place, :].copy()
        dataTemp.reset_index(drop=True, inplace=True)
        self.dataTemp = dataTemp.copy()
        max = dataTemp['High'].max()  # 获取数据最大值
        min = dataTemp['Low'].min()  # 获取最小值
        widthOffset = 30
        heightOffset = 10
        self.height = self.canvas.height - heightOffset  # 去掉10的用来画坐标轴空间
        self.width = self.canvas.width - widthOffset

        self.canvas.create_line((25, 0), (25, self.height), fill='red', width=2)
        for i in range(4):
            self.canvas.create_line((25, (i + 1) * self.height / 5), (32, (i + 1) * self.height / 5),
                                    fill='red')  # 画4条线当轴上的刻度
            text = str(round(max - (i + 1) / 5 * (max - min), 2))
            # print(max,min,text)
            self.canvas.create_text(13, (i + 1) * self.height / 5, text=text, fill='white', anchor=W)

        self.canvas.create_line((0, self.canvas.height - 8), (self.width, self.canvas.height - 8), fill='red', width=2)
        xPlace = []  # 记录横坐标刻度的位置
        for i in range(4):
            self.canvas.create_line(((i + 1) * self.width / 5, self.canvas.height - 8),
                                    ((i + 1) * self.width / 5, self.canvas.height - 15), fill='red')  # 画4条线当轴上的刻度
            xPlace.append((i + 1) * self.width / 5)

        dataTemp['Open'] = \
            (self.height - (dataTemp['Open'] - min) * self.height / (max - min)).astype(int)  # 转换成为像素的y坐标的位置
        dataTemp['High'] = \
            (self.height - (dataTemp['High'] - min) * self.height / (max - min)).astype(int)
        dataTemp['Low'] = \
            (self.height - (dataTemp['Low'] - min) * self.height / (max - min)).astype(int)
        dataTemp['Close'] = \
            (self.height - (dataTemp['Close'] - min) * self.height / (max - min)).astype(int)

        # 调整技术指标的坐标
        if self.techAnaly:
            for tech in self.techAnaly:
                dataTemp[tech] = (self.height - (dataTemp[tech] - min) * self.height / (max - min)).astype(int)

        widthDelta = math.floor(self.width / self.num)
        self.widthDelta = widthDelta

        # datatemp 的列【Date Time,	Open,	High,	Low,	Close,	Volume,	Adj Close】
        j = len(dataTemp) - 1
        i = self.canvas.width - widthDelta  # 对整个画布的宽度进行循环，从右向左画,每次取出最后1个画，一个循环的最后，删掉最后一个
        x = []  # 存放技术指标的x坐标

        while i > widthOffset:  # 默认画200个
            # 因为这里已经转换为像素了，所以收盘价大于开盘价的像素位置，其实是下跌，所以画绿色
            if dataTemp.iloc[j, 1] < dataTemp.iloc[j, 4]:
                color = 'green'
            else:
                color = 'red'
            self.canvas.create_line((i + self.delta, dataTemp.iloc[j, 2]),
                                    (i + self.delta, dataTemp.iloc[j, 3]), fill=color)
            if self.num != 800:
                if color == 'green':
                    self.canvas.create_rectangle((i, dataTemp.iloc[j, 1]),
                                                 (i + 2 * self.delta, dataTemp.iloc[j, 4]), fill=color,
                                                 outline=color)
                else:
                    self.canvas.create_rectangle((i, dataTemp.iloc[j, 4]),
                                                 (i + 2 * self.delta, dataTemp.iloc[j, 1]),
                                                 fill='black', outline=color)
            # 给横坐标写数值
            if xPlace and i - widthDelta < xPlace[-1] <= i:
                text = str(dataTemp.iloc[j, 0])
                self.canvas.create_text(i, self.height + 5, text=text, fill='white')
                xPlace.pop()

            # 给交易结果在图上做标注
            if 'instrument' in dataTemp and 'action' in dataTemp:  # 表示此时已经有交易结果了。
                if pd.notna(dataTemp.loc[j, 'action']) and 'BUY' in dataTemp.loc[j, 'action']:
                    self.canvas.create_line((i + self.delta, 0), (i + self.delta, 10), arrow='first', fill='red')
                    # 买，在最开始画
                elif pd.notna(dataTemp.loc[j, 'action']) and 'SELL' in dataTemp.loc[j, 'action']:
                    self.canvas.create_line((i + self.delta, 0), (i + self.delta, 10), arrow='last', fill='green')
                    # 卖，在最后画
            x.append(i)
            i -= widthDelta
            j -= 1

        # 对于每一个技术指标对设置一个键值对
        allTechCord = {}
        for i in self.techAnaly:
            allTechCord[i] = []
        length = dataTemp.shape[0]

        # 给allTechCord 添加曲线坐标
        for i in range(len(x)):
            for j in self.techAnaly:
                allTechCord[j].append(x[i])
                allTechCord[j].append(dataTemp.loc[length - i - 1, j])  # 画线需要【x,y,x,y,x,y】 这样的一系列坐标

        for i in self.techAnaly:
            # 画曲线，移动平均线或其他技术指标线
            self.canvas.create_line(allTechCord[i], fill=self.colors[np.random.randint(len(self.colors))], width=2,
                                    smooth=True, splinesteps=10)

    def redraw(self, *args):
        """
        根据滚动条重画,先删除原有的，再重画
        :param place: 获取开始的位置
        :return: None
        """
        # print(args)
        if len(args) == 2:  # 有时会有些其他的返回。
            # print(args)
            self.canvas.delete(ALL)
            self.place = round(float(args[1]) * len(self.guiDF))
            self.draw(self.place)
        self.sendback()

    def sendback(self):
        """
        返回位置信息给滚动条
        :param scrollbar: 滚动条对象
        :return: None
        """
        # print()
        self.scrollbar.set(self.place / len(self.guiDF),
                           (self.place + self.num) / len(self.guiDF))  # 滑块的长度为当前显示的大小占总数据长度的比率

    def mouseMove(self, event):
        """
        bind到鼠标移动事件
        :return: None
        """
        if self.showCross:
            string = self.drawCross(self.canvas.canvasx(event.x), self.canvas.canvasy(event.y))
            self.v.set(string)

    def click(self, event):
        """
        bind左键到点击事件,设一个真值，如果点击了就显示十字光标，再点一次就不显示了
        :param event:
        :return: None
        """
        self.canvas.focus_set()  # 每次鼠标点击都设置focus，以便接受键盘命令
        if self.showCross == False:
            self.showCross = True
            string = self.drawCross(self.canvas.canvasx(event.x), self.canvas.canvasy(event.y))
            self.v.set(string)
        else:
            self.showCross = False
            for item in self.crossItem:
                self.canvas.delete(item)  # 删掉横线和竖线

    def drawCross(self, x, y):
        """
        设置label的值
        :return: str 需要显示的各种信息，比如当前坐标的价格日期等等
        """
        if self.crossItem:
            for item in self.crossItem:
                self.canvas.delete(item)  # 删掉横线和竖线
        place = round((self.canvas.width - (x - 2)) / self.widthDelta)
        string = ''
        for i in range(self.dataTemp.shape[1]):
            string += (self.dataTemp.columns[i] + ' :' + str(self.dataTemp.iloc[-place, i]) + ' ')
        self.x = x
        self.y = y
        self.crossItem.append(self.canvas.create_line(x, 0, x, self.height, fill='white'))
        self.crossItem.append(self.canvas.create_line(0, y, self.width, y, fill='white'))
        return string

    def click2(self, event):
        self.canvas.delete(CURRENT)

    def backward(self):
        """
        向历史移动一个屏幕
        :return:
        """
        if self.place > self.num:
            self.canvas.delete(ALL)
            self.draw(self.place - self.num)
            self.place -= self.num

    def forward(self):
        """
        向未来移动一个屏幕
        :return:
        """
        if self.place < (len(self.guiDF) - self.num):
            self.canvas.delete(ALL)
            self.draw(self.place + self.num)
            self.place += self.num

    def bigger(self, event):
        """
        显示更少的k线，使每个k线变大
        :return:
        """

        if self.num >= 50:
            self.num /= 2
            self.delta *= 2

        self.canvas.delete(ALL)
        self.draw(self.place)

    def smaller(self, event):
        """
        显示更多的k线，使每个k线变小
        :return:
        """

        if self.num <= 800:
            self.num *= 2
            self.delta /= 2

        self.canvas.delete(ALL)
        self.draw(self.place)

    def Eval(self, event, context, entry):
        # 可以用 self.guiDF = self.Data[] 取某个品种来控制gui画出不同时刻的品种的图
        try:
            temp = eval(entry.get())
        except Exception as e:
            temp = traceback.format_exc()
        self.v.set(temp)

    def updateConfig(self, event):
        """
        响应大小改变的事件
        :param event:
        :return:
        """
        self.canvas.width = event.width
        self.canvas.height = event.height
        self.canvas.delete(ALL)
        self.draw(self.place)

    def changeInstrument(self, instrument):
        """
        更改要显示的品种
        :return:
        """
        self.instrument = instrument
        self.addData(self.Data)  # 更改guiDf
        self.configTechAnaly(self.tech)  # 更改对应的可显示的列名，并且重画。


class RealBroker(broker.Broker):
    """
    继承pyalgotrade的基类，以实现和tqsdk交互
    """

    def __init__(self, strategy):
        """

        :param strategy: 包含所有策略名称的list
        """
        super().__init__()
        self.strategy = strategy
        self.strategyAccount = {}  # 存储一个虚拟的分策略的账户信息
        for item in strategy:
            self.strategyAccount[item] = _virtualAccountHelp()


    def getInstrumentTraits(self, instrument):
        pass

    def getCash(self, includeShort=True, strategyNmae=None):
        """
        Returns the available cash.

        :param includeShort: Include cash from short positions.
        :type includeShort: boolean.
        """
        # TODO
        pass

    def getShares(self, instrument, strategyNmae=None):
        """Returns the number of shares for an instrument."""
        pass
        # TODO

    def getPositions(self, strategyNmae=None):
        """Returns a dictionary that maps instruments to shares."""
            # TODO

    def getActiveOrders(self, instrument=None):
        """Returns a sequence with the orders that are still active.

        :param instrument: An optional instrument identifier to return only the active orders for the given instrument.
        :type instrument: string.
        """
        pass

    def submitOrder(self, order):
        """Submits an order.
        :param order: The order to submit.
        :type order: :class:`Order`.
        """
        # TODO

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

    def join(self):  # pyalgotrade 中有abstract methods 非写不可。
        pass

    def eof(self):  # pyalgotrade 中有abstract methods 非写不可。
        pass

    def dispatch(self):  # pyalgotrade 中有abstract methods 非写不可。
        pass

    def peekDateTime(self):  # pyalgotrade 中有abstract methods 非写不可。
        pass


class _virtualAccountHelp:
    """
    帮助计算不同策略的虚拟持仓
    """


if __name__ == '__main__':
    # 直接调用下载数据
    data = DATA(1)
    data.checkDataUpdate()
