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


"""----------------------------------------------��ʼ���׶�----------------------------------------------------------"""
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

# ���峣��
durationTransDict = {'1m': 60, '1d': 86400}


try:
    # api=TqApi(TqAccount('����ģ��','284837','86888196'))
    api=TqApi(TqAccount('simnow','133492','Yhlz0000'), web_gui=True)
    logger.info('success sign in! with simnow')
    # api = TqApi(TqAccount('H�����ڻ�', '100909186', 'Yhlz0000'))
    # Yhlz.info('success sign in! with 100909186')
except Exception:
    logger.info('problem with sign in!')
    exit(1)

f = open('strategytorun.txt')
temp = f.readlines()
f.close()

#  ��ʼ������

strategys = {}
allKline = RealFeed()
# ��ʼ������
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
    # �����Դ��ݲ���������������������ȴ����ַ��� Ĭ�ϲ�����������Ϊ���Բ�������������ÿ�����Ե�Ĭ�ϲ����������в�����


"""----------------------------------------------��ʼʵ�����н׶�-----------------------------------------------------"""
contral = ''  # use for contral the whole program stop or not ,if it equal to 'q' then progam stoped
# get_input=Get_Input()
# get_input.setDaemon(True)
# get_input.start()
now_record = 61  # record minute time
when = 0
bars = RealBars()
logger.info('��ʼʵ������')
second = 0
while True:
    api.wait_update(time.time() + 1)
    now = time.localtime()
    if now.tm_min == 30 or now.tm_min == 0:
        time.sleep(2)  # avoid some exception like when updated and send order but exchange refused ,then wait 2s
    run = 0
    for contract in allKline.keys():  # ����б仯�˵ľ�ȥ���С�
        if api.is_changing(allKline[contract].data.iloc[-1], 'datetime'):  # have a new bar
            run = 1
            break
    if run:
        logger.debug('running!')
        # time.sleep(0.5)
        run = 0

        # ׼��������ڵ�bars
        tempDict = {}
        for contract in allKline:
            tempDict[contract] = allKline[contract].data.iloc[-1, :]   # ����һ��bar
        bars.setValue(tempDict)
        for strategy in allStg:
            broker.strategyNow = strategy
            strategy.onBars(bars)

    # һ���Ӹ���һ��

    if second!= now.tm_sec:
        second=now.tm_sec
        # ÿ��һ�����һ�μ�顣
        broker.update()

    if now.tm_hour == 15 or now.tm_hour == 23 or contral == 'q':
        broker.stop()  # ����ֲ���Ϣ�ģ�����������ֲ����д��csv
        logger.info('stop running!')
        break

api.close()
