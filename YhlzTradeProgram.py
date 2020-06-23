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


"""----------------------------------------------��ʼ���׶�----------------------------------------------------------"""
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

    # ���峣��
    durationTransDict = {'1m': 60, '1d': 86400}

    try:
        # api=TqApi(TqAccount('����ģ��','284837','86888196'))
        api = TqApi(TqAccount('simnow', '133492', 'Yhlz0000'), web_gui=True)
        logger.info('success sign in! with simnow')
        # api = TqApi(TqAccount('H�����ڻ�', '100909186', 'Yhlz0000'))
        # Yhlz.info('success sign in! with 100909186')

    except Exception as e:
        logger.info('problem with sign in!')
        exit(1)

    f = open('strategytorun.txt')
    temp = f.readlines()
    f.close()

    '---------------------------------------------------��ʼ������------------------------------------------------------'

    strategys = {}
    allTick = {}
    allKline = RealFeed()
    # ��ʼ������
    pos = api.get_position()
    orders = api.get_order()
    broker = RealBroker(api, pos)
    allStg = []
    # �������в��ԵĻ����ԵĽ���ģʽ��
    stg.YhlzStreategy.realTrade = True
    stg.YhlzStreategy.realBroker = broker

    realAccount = pd.read_csv('currentAccount.csv')

    for item in temp:
        item = eval(item)
        # !!! ���Բ��������� ����ͬ���Բ�ͬ���������Լ̳�һ����Ȼ�󻻸����֡�
        strategys[item[0]] = item[1:]  # ��strategy to  run �еĲ��Զ�Ӧ�� ���ֺͺ�Լ��¼������
        for dataNeeded in item[1:]:
            if str(dataNeeded[0]) not in allKline:
                allKline.addDataSource(str(dataNeeded[0]),
                                       api.get_kline_serial(dataNeeded[0], durationTransDict[dataNeeded[1]],
                                                            dataNeeded[2]))
            if dataNeeded[0] not in allTick:
                allTick[dataNeeded[0]] = api.get_quote(dataNeeded[0])
                # �����ָ����Լ��ô�Ѷ�Ӧ��������ԼҲ�����ϡ�
                if 'KQ.i' in dataNeeded[0] and dataNeeded[0].replace('KQ.i', 'KQ.m') not in allTick:
                    allTick[dataNeeded[0].replace('KQ.i', 'KQ.m')] = \
                        api.get_quote(dataNeeded[0].replace('KQ.i', 'KQ.m'))
                    allTick[allTick[dataNeeded[0].replace('KQ.i', 'KQ.m')].underlying_symbol] = \
                        allTick[dataNeeded[0].replace('KQ.i', 'KQ.m')]
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
    logger.debug('��ʼʵ������')
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
                tempDict[contract] = allKline[contract].data.iloc[-1, :]  # ����һ��bar
            bars.setValue(tempDict)
            for strategy in allStg:
                broker.strategyNow = strategy
                strategy.onBars(bars)

        # һ���Ӹ���һ��

        if second != now.tm_sec:
            second = now.tm_sec
            # ÿ��һ�����һ�μ�顣
            broker.update()

        if not now.tm_min % 15 and now.tm_sec == 15:  # ��ʱ�����������15ʱ��Ҳ����ʮ���������һ��,
            logger.info(str(pos))

        # ����Ƿ�ӽ��ǵ�ͣԤ��
        for item in allTick:
            if not allTick[item].instrument_id in upList :
                if (allTick[item].upper_limit - allTick[item].last_price) / allTick[item].last_price < 0.01:
                    logger.warning(allTick[item].instrument_id + ' �ӽ���ͣ')
                    upList.append(allTick[item].instrument_id)
                    if allTick[item].upper_limit == allTick[item].last_price:
                        upperLimitList.append(allTick[item].instrument_id)

            elif not allTick[item].instrument_id in lowList:
                if (allTick[item].last_price - allTick[item].lower_limit ) / allTick[item].last_price < 0.01:
                    logger.warning(allTick[item].instrument_id + ' �ӽ���ͣ')
                    lowList.append(allTick[item].instrument_id)
                    if allTick[item].lower_limit == allTick[item].last_price:
                        lowerLimitList.append(allTick[item].instrument_id)

            elif allTick[item].instrument_id in upList:
                if (allTick[item].upper_limit - allTick[item].last_price) / allTick[item].last_price > 0.01:
                    logger.warning(allTick[item].instrument_id + ' �뿪��ͣ����')
                    upList.remove(allTick[item].instrument_id)
                    if allTick[item].instrument_id in upperLimitList and allTick[item].upper_limit != allTick[item].last_price:
                        upperLimitList.remove(allTick[item].instrument_id)

            elif allTick[item].instrument_id in lowList:
                if (allTick[item].last_price - allTick[item].lower_limit) / allTick[item].last_price > 0.01:
                    logger.warning(allTick[item].instrument_id + ' �뿪��ͣ����')
                    lowList.remove(allTick[item].instrument_id)
                    if allTick[item].instrument_id in lowerLimitList and allTick[item].upper_limit != allTick[item].last_price:
                        lowerLimitList.remove(allTick[item].instrument_id)

            # ����ǵ�ͣ��Լ�ĳֲ�
            for position in pos:
                if pos[position].instrument_id in lowerLimitList and pos[position].pos_long > 0:
                    logger.warning(pos[position].instrument_id + ' ���ڵ�ͣ�Ķ�֣�')
                elif pos[position].instrument_id in upperLimitList and pos[position].pos_short > 0:
                    logger.warning(pos[position].instrument_id + ' ������ͣ�Ŀղ֣�')

            # ����ǵ�ͣ��Լ�Ĺҵ���
            for order in orders:
                if not orders[order].is_dead:
                    if orders[order].instrument_id in lowerLimitList:
                        logger.warning(orders[order].instrument_id + ' ���ڵ�ͣ�Ĺҵ���')
                    elif orders[order].instrument_id in upperLimitList:
                        logger.warning(orders[order].instrument_id + ' ������ͣ�Ĺҵ���')


        if now.tm_hour == 15 or now.tm_hour == 23 or contral == 'q':
            broker.stop()  # ����ֲ���Ϣ�ģ�����������ֲ����д��csv
            logger.debug('stop running!')
            break

    api.close()

# except Exception as e:
#     broker.stop()
#     logger.error('���г���������������飡\n' + traceback.format_exc())
