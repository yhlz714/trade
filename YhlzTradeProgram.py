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
from RealModule import RealBroker


class Get_Input(threading.Thread):
    """this thread contral wheather to stop whole program"""

    def run(self):
        global contral
        while True:
            contral = input('press q to quit!')
            logging.info(contral)
            logging.info(time.ctime())
            now = time.localtime()
            if now.tm_hour == 15 or now.tm_hour == 3 or contral == 'q':
                logging.info('Ready to quit')
                return


"""----------------------------------------------初始化阶段----------------------------------------------------------"""
logging.basicConfig(filename='log.txt', filemode='a', level=logging.DEBUG,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logging.info('This is yhlz\'s trading server,now started!\n')

try:
    # api=TqApi(TqAccount('快期模拟','284837','86888196'))
    # api=TqApi(TqAccount('simnow','133492','Yhlz0000'))
    # logging.info('success sign in! with simnow')
    api = TqApi(TqAccount('H华安期货', '100909186', 'Yhlz0000'))
    logging.info('success sign in! with 100909186')
except Exception:
    logging.info('problem with sign in!')
    exit(1)

f = open('strategytorun.txt')
temp = f.readlines()
f.close()

#  初始化数据
durationTransDict = {'1m': 60, '1d': 86400}
strategys = {}
allKline = {}
for item in temp:
    item = eval(item)
    strategys[item[0]] = item[1:]  # 将strategy to  run 中的策略对应的 名字和合约记录下来。
    for dataNeeded in item[1]:
        if str(dataNeeded) not in allKline:
            allKline[str(dataNeeded)] = \
                api.get_kline_serial(dataNeeded[0], durationTransDict[dataNeeded[2]], dataNeeded[2])

# 初始化策略
broker = RealBroker(api)
allStg = []
for strategy in strategys:
    allStg.append(eval(strategy + '(?)'))  # TODO 看要怎么样给初始化的策略传参数

contral = ''  # use for contral the whole program stop or not ,if it equal to 'q' then progam stoped

"""----------------------------------------------开始实盘运行阶段-----------------------------------------------------"""
# get_input=Get_Input()
# get_input.setDaemon(True)
# get_input.start()
now_record = 61  # record minute time
when = 0
while True:
    api.wait_update(time.time() + 1)
    now = time.localtime()
    if now.tm_min == 30 or now.tm_min == 0:
        time.sleep(2)  # avoid some exception like when updated and send order but exchange refused ,then wait 2s
    run = 0
    for contract in allKline:  # 如果有变化了的就去运行。
        if api.is_changing(allKline[contract]):  # data is change
            run = 1
            break
    if run:
        time.sleep(0.5)
        run = 0
        for strategy in allStg:
            strategy.onBar()  # TODO 需要传入参数


    if now.tm_hour == 15 or now.tm_hour == 23 or contral == 'q':
        broker.stop()  # 处理持仓信息的，将各个虚拟持仓情况写入csv
        logging.info('stop running!')
        break

api.close()
