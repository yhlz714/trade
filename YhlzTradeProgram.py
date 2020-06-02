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
            logger.info(contral)
            logger.info(time.ctime())
            now = time.localtime()
            if now.tm_hour == 15 or now.tm_hour == 3 or contral == 'q':
                logger.info('Ready to quit')
                return


"""----------------------------------------------初始化阶段----------------------------------------------------------"""
logger = logging.getLogger('Yhlz')
logger.setLevel(logging.DEBUG)
fm =logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
fh = logging.FileHandler('log.txt', mode='a')
fh.setFormatter(fm)
fh.setLevel(logging.DEBUG)
logger.addHandler(fh)
logger.propagate = False

# logging.basicConfig(filename='log.txt', filemode='a', level=logging.DEBUG,
#                     format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger.info('This is yhlz\'s trading server,now started!\n')

# 定义常量
durationTransDict = {'1m': 60, '1d': 86400}


try:
    # api=TqApi(TqAccount('快期模拟','284837','86888196'))
    api=TqApi(TqAccount('simnow','133492','Yhlz0000'), web_gui=True)
    logger.info('success sign in! with simnow')
    # api = TqApi(TqAccount('H华安期货', '100909186', 'Yhlz0000'))
    # Yhlz.info('success sign in! with 100909186')
except Exception:
    logger.info('problem with sign in!')
    exit(1)

f = open('strategytorun.txt')
temp = f.readlines()
f.close()

#  初始化数据

strategys = {}
allKline = RealFeed()
# 初始化策略
broker = RealBroker(api)
allStg = []
stg.YhlzStreategy.realTrade = True
stg.YhlzStreategy.realBroker = broker

for item in temp:
    item = eval(item)
    for dataNeeded in item[1:]:
        if str(dataNeeded[0]) not in allKline:
            allKline.addDataSource(str(dataNeeded[0]),
                                   api.get_kline_serial(dataNeeded[0], durationTransDict[dataNeeded[1]], dataNeeded[2]))
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
logger.info('开始实盘运行')
second = 0
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
            tempDict[contract] = allKline[contract].data.iloc[-1, :]   # 最新一个bar
        bars.setValue(tempDict)
        for strategy in allStg:
            broker.strategyNow = strategy
            strategy.onBars(bars)

    # 一秒钟更新一次

    if second!= now.tm_sec:
        second=now.tm_sec
        # 每隔一秒进行一次检查。
        broker.update()

    if now.tm_hour == 15 or now.tm_hour == 23 or contral == 'q':
        broker.stop()  # 处理持仓信息的，将各个虚拟持仓情况写入csv
        logger.info('stop running!')
        break

api.close()
