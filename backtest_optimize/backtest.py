"""
YHLZ的回测系统基于pyalgotrade
Version = 2.0
"""


import threading

from pyalgotrade.stratanalyzer import sharpe
from pyalgotrade.stratanalyzer import drawdown

from backtest_optimize.Yhlz_Module import *
from backtest_optimize.Strategy import *


def delay_deal():
    """
    延迟处理函数
    """
    global context
    if context.backtectDone:
        context.root.event_generate('<<finished>>')
    else:
        context.root.after(1000, delay_deal)


def Backtest():
    """
    回测函数

    :return:
    """

    global context, Data, feed
    # ???怎么搞定策略不同传入参数的问题
    context.myStrategy = context.stg(feed, "rb", context, Data)

    retAnalyzer = returns.Returns(maxLen=1000000)
    context.myStrategy.attachAnalyzer(retAnalyzer)
    sharpeRatioAnalyzer = sharpe.SharpeRatio()
    context.myStrategy.attachAnalyzer(sharpeRatioAnalyzer)
    drawDownAnalyzer = drawdown.DrawDown()
    context.myStrategy.attachAnalyzer(drawDownAnalyzer)
    tradeAnalyzer = Yhlz_Trade()
    # tradeAnalyzer=trades.Trades()
    context.myStrategy.attachAnalyzer(tradeAnalyzer)

    # print(myStrategy.getBroker().getCommission())
    print(time.ctime())
    context.myStrategy.run()
    for item in context.myStrategy.tech:
        for key in Data.keys():  # 此处如果key有多个，那么策略也需要按照key的顺序多个写。也就是多品种的情况
            Data[key][item] = context.myStrategy.tech[item]  # 将技术指标写入画图的df中

    time_compare = pd.DataFrame()
    time_compare['Time'] = retAnalyzer.getCumulativeReturns().getDateTimes()
    time_compare['Pnl'] = list(retAnalyzer.getCumulativeReturns())
    time_compare.set_index('Time', drop=True, inplace=True)
    # print((time_compare.resample('M').last()+1) / (time_compare.resample('M').first()+1))  #按月的情况
    print((time_compare.resample('A').last() + 1) / (time_compare.resample('A').first() + 1))  # 按年的情况
    print("Final portfolio value: $%.2f" % context.myStrategy.getResult())
    print("Cumulative returns: %.2f %%" % (retAnalyzer.getCumulativeReturns()[-1] * 100))

    # 画图
    # fig, ax1 = plt.subplots()
    # temp = feed.getDataSeries().getCloseDataSeries().getDateTimes()
    # ax1.plot(temp, feed.getDataSeries().getCloseDataSeries())
    # ax2 = ax1.twinx()
    # ax2.plot(temp, list(retAnalyzer.getCumulativeReturns()), color='r')
    # plt.show()

    print("Sharpe ratio: %.2f" % (sharpeRatioAnalyzer.getSharpeRatio(0.05)))
    print("Max. drawdown: %.2f %%" % (drawDownAnalyzer.getMaxDrawDown() * 100))
    print("Longest drawdown duration: %s" % (drawDownAnalyzer.getLongestDrawDownDuration()))
    # print(tradeAnalyzer.all_trade)

    for key in Data.keys():
        Data[key]['volume'] = np.nan
        Data[key]['instrument'] = np.nan
        Data[key]['action'] = np.nan
        Data[key]['price'] = np.nan

    # 将所有交易数据写入各个品种的数据DF中去。
    for i in range(tradeAnalyzer.all_trade.shape[0]):
        tempList = tradeAnalyzer.all_trade.loc[i, ['instrument', 'action', 'price', 'volume']].to_list()  # 要写入的数据
        tempDF = Data[tradeAnalyzer.all_trade.loc[i, 'instrument']]  # 找到数据对应的df
        # 写数据
        tempDF.loc[tempDF['Date Time'] == tradeAnalyzer.all_trade.loc[i, 'date'],
                   ['instrument', 'action', 'price', 'volume']] = tempList
        # 重新写回dict
        Data[tradeAnalyzer.all_trade.loc[i, 'instrument']] = tempDF
    context.backtectDone = True


def optimize():
    """
    pyalgotrade 有优化组件，可以直接抄
    :return:
    """
    pass


class Context:
    pass


if __name__ == '__main__':
    context = Context()
    context.categorys = ['rb']  # 给定所有要回测的品种
    context.categoryToFile = {'rb': 'KQi@SHFErb'}  # 品种和文件名转换dict
    context.stg = SMACrossOver
    context.backtectDone = False
    print(time.ctime())

    # 读取以及处理数据
    data = DATA(context)
    Data, feed = data.feed()

    # 或许可以读取csv文件然后，直接一次性导入各种设置。这里也有，可用于修改少数，这里的优先级高于csv文件。
    context.root = Tk()

    # 创建并添加Canvas
    bigFrame = Frame(context.root)
    frame = Frame(bigFrame)

    cv = Canvas(frame, background='black')#, width=1800, height=400)
    cv.pack(fill=BOTH, expand=YES)

    v = StringVar()

    Label(frame, textvariable=v).pack(side=BOTTOM,fill=BOTH)
    v.set('try')
    entry = Entry(frame)
    entry.pack(side=BOTTOM, fill=BOTH)
    hbar = Scrollbar(frame, orient=HORIZONTAL)
    hbar.pack(side=BOTTOM, fill=BOTH)
    hbar.set(1, 1)
    frame1 = Frame(frame)
    kline = Kline(cv, hbar, v, Data)
    # kline.configTechAnaly([i for i in context.stg.tech])  # 设置要画的计算指标
    #
    # # 对于输入框输入的命令在当前环境下执行
    #
    entry.bind('<Button-1>', lambda x, e=entry: e.focus_set())
    entry.bind('<Return>', lambda x, e=entry: kline.Eval(x, e))
    cv.bind('<Button-1>', kline.click)
    cv.bind('<Motion>', kline.mouseMove)
    cv.bind('<Button-3>', kline.click2)
    cv.bind('<KeyPress-Up>', func=kline.bigger)
    cv.bind('<KeyPress-Down>', func=kline.smaller)
    cv.bind('<Configure>', kline.updateConfig)
    context.root.bind('<<finished>>', lambda ev: kline.configTechAnaly([i for i in context.myStrategy.tech]))

    hbar.config(command=kline.redraw)
    bLeft = Button(frame1, text='backward', command=kline.backward)
    bRight = Button(frame1, text='forward', command=kline.forward)
    bLeft.pack(side=LEFT, fill=BOTH)
    bRight.pack(side=RIGHT, fill=BOTH)
    frame1.pack(side=BOTTOM, fill=BOTH)

    frame.pack(fill=BOTH, expand=YES)
    bigFrame.pack(fill=BOTH, expand=YES)

    kline.draw()
    # 创建窗口
    backtest = threading.Thread(target=Backtest, name='backtest')
    # backtest.start()

    # delay_deal()
    context.root.mainloop()
    # backtest.join()
