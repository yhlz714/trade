# coding: gbk
# This is yhlz's trading program base on tqsdk.
# Main running progrem.

"""
Author: Yhlz 2020-03-06
"""

import threading
import os
import time
import logging
from logging.handlers import SMTPHandler
import traceback

import pandas as pd
import numpy as np
from tqsdk import TqApi, TqAccount, TargetPosTask, TqSim

import backtest_optimize.Strategy as stg
from RealModule import RealBroker, RealFeed, RealBars


class Get_Input(threading.Thread):
    """this thread contral wheather to stop whole program"""

    def run(self):
        global contral
        while True:
            contral = input('press q to quit!')
            logger.debug(contral)
            logger.debug(time.ctime())
            now = time.localtime()
            if now.tm_hour == 15 or now.tm_hour == 3 or contral == 'q':
                logger.debug('Ready to quit')
                return


"""----------------------------------------------初始化阶段----------------------------------------------------------"""
logger = logging.getLogger('Yhlz')
# logger.setLevel(logging.DEBUG)
fm = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

fh = logging.FileHandler('log.txt', mode='a')
fh.setFormatter(fm)
fh.setLevel(logging.DEBUG)

mail_handler = SMTPHandler(
        mailhost='smtp.qq.com',
        fromaddr='517353631@qq.com',
        toaddrs='517353631@qq.com',
        subject='running info! simnow',
        credentials=('517353631@qq.com', 'kyntpvjwuxfvbiag'))
mail_handler.setLevel(logging.INFO)
mail_handler.setFormatter(fm)

# logger.addHandler(mail_handler)
logger.setLevel(logging.DEBUG)
logger.addHandler(fh)
logger.propagate = False

# try:
if __name__ == '__main__':
    logger.debug('This is yhlz\'s trading server,now started!\n')

    # 定义常量
    durationTransDict = {'1m': 60, '1d': 86400}

    try:
        # api=TqApi(TqAccount('快期模拟','284837','86888196'))
        api = TqApi(TqAccount('simnow', '133492', 'Yhlz0000'), web_gui=True)
        logger.info('success sign in! with simnow')
        # api = TqApi(TqAccount('H华安期货', '100909186', 'Yhlz0000'))
        # Yhlz.info('success sign in! with 100909186')

    except Exception as e:
        logger.info('problem with sign in!')
        exit(1)

    f = open('strategytorun.txt')
    temp = f.readlines()
    f.close()

    '---------------------------------------------------初始化数据------------------------------------------------------'

    strategys = {}
    allTick = {}
    allKline = RealFeed()
    # 初始化策略
    pos = api.get_position()
    orders = api.get_order()
    broker = RealBroker(api, pos)
    allStg = []
    # 设置所有策略的基策略的交易模式。
    stg.YhlzStreategy.realTrade = True
    stg.YhlzStreategy.realBroker = broker

    realAccount = pd.read_csv('currentAccount.csv')

    for item in temp:
        item = eval(item)
        # !!! 策略不可重名， 如需同策略不同参数，可以继承一个，然后换个名字。
        strategys[item[0]] = item[1:]  # 将strategy to  run 中的策略对应的 名字和合约记录下来。
        for dataNeeded in item[1:]:
            if str(dataNeeded[0]) not in allKline:
                allKline.addDataSource(str(dataNeeded[0]),
                                       api.get_kline_serial(dataNeeded[0], durationTransDict[dataNeeded[1]],
                                                            dataNeeded[2]))
            if dataNeeded[0] not in allTick:
                allTick[dataNeeded[0]] = api.get_quote(dataNeeded[0])
                # 如果是指数合约那么把对应的主力合约也订阅上。
                if 'KQ.i' in dataNeeded[0] and dataNeeded[0].replace('KQ.i', 'KQ.m') not in allTick:
                    allTick[dataNeeded[0].replace('KQ.i', 'KQ.m')] = \
                        api.get_quote(dataNeeded[0].replace('KQ.i', 'KQ.m'))
                    allTick[allTick[dataNeeded[0].replace('KQ.i', 'KQ.m')].underlying_symbol] = \
                        allTick[dataNeeded[0].replace('KQ.i', 'KQ.m')]
        allStg.append(eval('stg.' + item[0] + '(allKline, str(item[1][0]), \'\', {})'))
        # 给策略传递参数，后面两个必须参数先传空字符， 默认参数不传，因为策略不会重名，所以每个策略的默认参数就是运行参数。

    """----------------------------------------------开始实盘运行阶段-----------------------------------------------------"""
    contral = ''  # use for contral the whole program stop or not ,if it equal to 'q' then progam stoped
    # get_input=Get_Input()
    # get_input.setDaemon(True)
    # get_input.start()
    now_record = 61  # record minute time
    when = 0
    bars = RealBars()
    logger.debug('开始实盘运行')
    second = 0
    upList = []
    lowList = []
    upperLimitList = []
    lowerLimitList = []

    while True:
        api.wait_update(time.time() + 1)
        now = time.localtime()
        if now.tm_min == 30 or now.tm_min == 0:
            time.sleep(2)  # avoid some exception like when updated and send order but exchange refused ,then wait 2s
        run = 0
        for contract in allKline.keys():  # 如果有变化了的就去运行。
            if api.is_changing(allKline[contract].data.iloc[-1], 'datetime'):  # have a new bar
                run = 1
                break
        if run:
            logger.debug('running!')
            # time.sleep(0.5)
            run = 0

            # 准备这个周期的bars
            tempDict = {}
            for contract in allKline:
                tempDict[contract] = allKline[contract].data.iloc[-1, :]  # 最新一个bar
            bars.setValue(tempDict)
            for strategy in allStg:
                broker.strategyNow = strategy
                strategy.onBars(bars)

        # 一秒钟更新一次

        if second != now.tm_sec:
            second = now.tm_sec
            # 每隔一秒进行一次检查。
            broker.update()

        if not now.tm_min % 15 and now.tm_sec == 15:  # 当时间分钟数整除15时，也就是十五分钟运行一次,
            logger.info(str(pos))

        # 检测是否接近涨跌停预警
        for item in allTick:
            if not allTick[item].instrument_id in upList :
                if (allTick[item].upper_limit - allTick[item].last_price) / allTick[item].last_price < 0.01:
                    logger.warning(allTick[item].instrument_id + ' 接近涨停')
                    upList.append(allTick[item].instrument_id)
                    if allTick[item].upper_limit == allTick[item].last_price:
                        upperLimitList.append(allTick[item].instrument_id)

            elif not allTick[item].instrument_id in lowList:
                if (allTick[item].last_price - allTick[item].lower_limit ) / allTick[item].last_price < 0.01:
                    logger.warning(allTick[item].instrument_id + ' 接近跌停')
                    lowList.append(allTick[item].instrument_id)
                    if allTick[item].lower_limit == allTick[item].last_price:
                        lowerLimitList.append(allTick[item].instrument_id)

            elif allTick[item].instrument_id in upList:
                if (allTick[item].upper_limit - allTick[item].last_price) / allTick[item].last_price > 0.01:
                    logger.warning(allTick[item].instrument_id + ' 离开涨停附近')
                    upList.remove(allTick[item].instrument_id)
                    if allTick[item].instrument_id in upperLimitList and allTick[item].upper_limit != allTick[item].last_price:
                        upperLimitList.remove(allTick[item].instrument_id)

            elif allTick[item].instrument_id in lowList:
                if (allTick[item].last_price - allTick[item].lower_limit) / allTick[item].last_price > 0.01:
                    logger.warning(allTick[item].instrument_id + ' 离开跌停附近')
                    lowList.remove(allTick[item].instrument_id)
                    if allTick[item].instrument_id in lowerLimitList and allTick[item].upper_limit != allTick[item].last_price:
                        lowerLimitList.remove(allTick[item].instrument_id)

            # 检查涨跌停合约的持仓
            for position in pos:
                if pos[position].instrument_id in lowerLimitList and pos[position].pos_long > 0:
                    logger.warning(pos[position].instrument_id + ' 有在跌停的多仓！')
                elif pos[position].instrument_id in upperLimitList and pos[position].pos_short > 0:
                    logger.warning(pos[position].instrument_id + ' 有在涨停的空仓！')

            # 检查涨跌停合约的挂单。
            for order in orders:
                if not orders[order].is_dead:
                    if orders[order].instrument_id in lowerLimitList:
                        logger.warning(orders[order].instrument_id + ' 有在跌停的挂单！')
                    elif orders[order].instrument_id in upperLimitList:
                        logger.warning(orders[order].instrument_id + ' 有在涨停的挂单！')


        if now.tm_hour == 15 or now.tm_hour == 23 or contral == 'q':
            broker.stop()  # 处理持仓信息的，将各个虚拟持仓情况写入csv
            logger.debug('stop running!')
            break

    api.close()

# except Exception as e:
#     broker.stop()
#     logger.error('运行出现问题请立即检查！\n' + traceback.format_exc())
