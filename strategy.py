# -*- coding: utf-8 -*-
#策略编写规范 ************************* 
#1所有策略返回的值是一个list，里面按照strategy_to_run里面的标注数据的顺序，写下对应的合约的target_postion
#2这个np矩阵的是一个n行m列的矩阵，其中n为数据长度，m为需要返回值的品种个数，最后一列是时间
import sys
import numpy as np
import os
import logging

#from matplotlib.widgets import MultiCursor
#:pdb.set_trace()
if sys.version_info>=(3,3):
    vv=3
sys.dont_write_bytecode=True #for not creat pyc file ,every time change codereimport this file it will not change because directtly read from pyc file
def get_equity(rr,data,fee=0.0001):
    record=np.zeros([len(data),4])
    j=0
    for i in range(len(rr)-1):
        if rr[i,0]!=rr[i+1,0]:
            record[j,0]=(rr[i+1,0]-rr[i,0])
            record[j,1]=data[i+1,-2]
            record[j,2]=rr[i+1,1] #time
            record[j,3]=rr[i+1,0] #记录现在的净持仓应该是多少
            j=j+1
    if rr[-1,0]!=0:            
        record[j,0]=0-rr[-1,0]  #最后如果不是0，那么需要以最后的价钱平仓
        record[j,1]=data[-1,4]  #最后一根bar的收盘价
        record[j,2]=data[-1,0] #time
    record=record[0:j,:] #去掉后面预留给可能有很多笔交易的位置
    record[:,0]=(record[:,0]*record[:,1]*(1-fee))  #fees #temp用于临时记录这个当前bar的买卖值，由于当前bar有持仓，且持仓已经乘上了收盘价，所以只要减去这个序列，权益的累积曲线就不会因为-3000而突然减少，做多+3001而又突然加回来
    record[:,0]=-(np.add.accumulate(record[:,0])-record[:,1]*record[:,3]) #because return=short-long,but in calculate is use long-short,so need to plus a '-',
    #由于按照这样计算权益会出现空一手就-3000，多一手就+3000的情况，所以权益回来波动，后面的record【1】*record【3】使当前持仓不为0的头寸按当前bar的收盘价调整回来，这样，权益的累计曲线看起来就正常了
    record=np.delete(record,1,1) #因为本身record是一个n行三列的np矩阵，delete的参数第一个1表示第二值，从0开始，第二1表示y方向。也就是删除整个第二列
    return record
def ma(data,m=1000):
    '''$m$'''  #this is parameter list every parameter clamped by two $ 
    rr=np.zeros([len(data),2])
    for i in np.arange(len(data)-m):
        if data[i+m,4]>=data[i:i+m,4].mean():
            rr[i+m,0]=1
            rr[i+m,1]=data[i+m,0]  #add a time series
        else:
            rr[i+m,0]=-1
            rr[i+m,1]=data[i+m,0] #add a time series
    return rr
def bias(data,n=1000,m=2): #乖离率，n是均线周期，m是偏离的百分比数
    rr=np.zeros([len(data),2])
    m=m/1000.0
    for i in np.arange(len(data)-n):
        moving_average=data[i:i+n,4].mean()
        if data[i+n,4]>moving_average*(1+m): #该周期大于上轨。
            rr[i+n,0]=1
            rr[i+n,1]=data[i+n,0]
        elif data[i+n,4]<moving_average*(1-m): #该周期小于下轨。
            rr[i+n,0]=-1
            rr[i+n,1]=data[i+n,0]
        else:   #处于上下之间，等于前一个的值
            rr[i+n,0]=rr[i+n-1,0]
            rr[i+n,1]=data[i+n,0]
    return rr
def boll(data,n=1000,m=1000,p=200): #布林线策略，n表示均线周期，m表示标准差周期，p表示使用多少个标准差。
    rr=np.zeros([len(data),2])
    k=max(m,n)
    p=p/100.0
    for i in np.arange(len(data)-k):
        moving_average=data[i+k-n:i+k,4].mean()
        if data[i+k,4]>moving_average+p*data[i+k-m:i+k,4].std(): #该周期大于上轨。
            rr[i+k,0]=1
            rr[i+k,1]=data[i+k,0]
        elif data[i+k,4]<moving_average-p*data[i+k-m:i+k,4].std(): #该周期小于下轨。
            rr[i+k,0]=-1
            rr[i+k,1]=data[i+k,0]
        else:   #处于上下之间，等于前一个的值
            rr[i+k,0]=rr[i+k-1,0]
            rr[i+k,1]=data[i+k,0]
    return rr
def twoboll(data,n=250,m=250,p=150,n1=250,m1=250,p1=80): #双布林线策略
    rr=np.zeros([len(data),2])
    k=max(n,m,n1,m1)
    #print(n,m,p,n1,m1,p1)
    p=p/100.0
    p1=p1/100.0
    temp=k-n
    temp1=k-n1
    temp_m=k-m
    temp_m1=k-m1
    for i in np.arange(len(data)-k):
        moving_average=data[i+temp:i+k,4].mean()
        moving_average1=data[i+temp1:i+k,4].mean()
        up=moving_average+p*data[i+temp_m:i+k,4].std()
        up1=moving_average1+p1*data[i+temp_m1:i+k,4].std()
        down=moving_average-p*data[i+temp_m,4].std()
        down1=moving_average1-p1*data[i+temp_m1,4].std()
        if data[i+k,4]<up1 and data[i+k,4]>down1: #在内部布林线的内部
            rr[i+k,0]=0
            rr[i+k,1]=data[i+k,0]
        elif data[i+k,4]>up:
            rr[i+k,0]=1
            rr[i+k,1]=data[i+k,0]
        elif data[i+k,4]<down:
            rr[i+k,0]=-1
            rr[i+k,1]=data[i+k,0]
        else:
            rr[i+k,0]=rr[i+k-1,0]
            rr[i+k,1]=data[i+k,0]
        #print(up,up1,down1,down,rr[i+k,0],data[i+k,4],moving_average,moving_average1)
    return rr
def sin_ma(data,k=50,n=500,m=1000): #k 代表每次增加k分之pi ，n表示m这个均线周期最大变化多少，m表示均线的天数， 这个策略是用一个sin函数来变化ma的周期数
    rr=np.zeros([len(data),2])
    j=0
    pi=np.pi #记录下pi的值
    for i in np.arange(len(data)-m-n):
        #print(j)
        temp=int(round(n*(1-np.sin(j))))
        #print(temp)
        #os.system('pause')
        if data[i+m+n,4]>=data[i+temp:i+m+n,4].mean():
            rr[i+m+n,0]=1
            rr[i+m+n,1]=data[i+m+n,0]  #add a time series
        else:
            rr[i+m+n,0]=-1
            rr[i+m+n,1]=data[i+m+n,0] #add a time series
        j=j+pi/k
    return rr
def cross_ma(data,position,account,n=108,m=694): #本策略是双均线交叉买卖策略。
    #print(n,m)
    #print(data[-1,:])
    rr=np.zeros([len(data),2])
    if n>m:
        return rr
    for i in np.arange(len(data)-m):
        if data[i+1:i+m+1,4].mean()>data[i+m-n+1:i+m+1,4].mean(): #长期大于短期
            rr[i+m,0]=-1 
            rr[i+m,1]=data[i+m,0] #time
        else:
            rr[i+m,0]=1
            rr[i+m,1]=data[i+m,0] #time
    #print(i)
    #print(data[-1])
    logging.info(data[len(data)-n:,4].mean())
    logging.info(data[len(data)-m:,4].mean())
    #print(data[len(data)-n:,4].mean())
    #print(data[len(data)-m:,4].mean())
    if (position['SHFE.rb2001'].volume_long-position['SHFE.rb2001'].volume_short)*rr[-1,0]>0:
        #print('unchange!')
        rr[-1,0]=position['SHFE.rb2001'].volume_long-position['SHFE.rb2001'].volume_short
    else:
        rr[-1,0]=rr[-1,0]*int(account.balance/8000)
    #print(rr[-1,0])
    #logging.info(rr[-1,0])
    return rr
def ma___ma(data,n=150,m=1000): #本策略根据ma的盈利，即ma的equity的均线来确定交易，ma的equity上穿equity的均线做多，下穿做空。三个下划线表示这种建立在别的策略之上的策略，这种策略直接返回equity。所以用下划线以供sort函数识别，区别对待
    rr=ma(data,m)
    equity_ma=get_equity(rr,data)
    equity=np.zeros([len(equity_ma),2])
    #reco=np.zeros(len(equity_ma))  #用来记录看这个策略什么时候做多，什么时候做空，用来调试
    for i in range(n):
        equity[i+1,0]=equity_ma[i+1,0]-equity_ma[i,0]
        equity[i+1,1]=equity_ma[i+1,1]
    for i in range(len(equity_ma)-n-1):
        if equity_ma[i+n,0]<equity_ma[i:i+n,0].mean():
            equity[i+n+1,0]=-(equity_ma[i+n+1,0]-equity_ma[i+n,0])
            #reco[i+n+1]=equity_ma[i:i+n,0].mean() #测试用
            equity[i+n+1,1]=equity_ma[i+n+1,1]
        else:
            equity[i+n+1,0]=equity_ma[i+n+1,0]-equity_ma[i+n,0]
            #reco[i+n+1]=equity_ma[i:i+n,0].mean()# 测试用
            equity[i+n+1,1]=equity_ma[i+n+1,1]
    equity[:,0]=np.add.accumulate(equity[:,0])
    #pdb.set_trace()
    return equity
def ma___std(data,n=150,k=50,m=1000):
    rr=ma(data,m)
    equity_ma=get_equity(rr,data)
    equity=np.zeros([len(equity_ma),2])
    #reco=np.zeros(len(equity_ma))  #用来记录看这个策略什么时候做多，什么时候做空，用来调试
    for i in range(n):
        equity[i+1,0]=equity_ma[i+1,0]-equity_ma[i,0]
        equity[i+1,1]=equity_ma[i+1,1]
    for i in range(len(equity_ma)-n-1):
        if equity_ma[i+n,0]>equity_ma[i:i+n,0].mean()+equity_ma[i:i+k,0].std(): #均线加标准差，类似布林线。
            equity[i+n+1,0]=-(equity_ma[i+n+1,0]-equity_ma[i+n,0])
            #reco[i+n+1]=equity_ma[i:i+n,0].mean() #测试用
            equity[i+n+1,1]=equity_ma[i+n+1,1]
        else:
            equity[i+n+1,0]=equity_ma[i+n+1,0]-equity_ma[i+n,0]
            #reco[i+n+1]=equity_ma[i:i+n,0].mean()# 测试用
            equity[i+n+1,1]=equity_ma[i+n+1,1]
    equity[:,0]=np.add.accumulate(equity[:,0])
    #pdb.set_trace()
    return equity
def dc_chennel(data,n=200): #唐安琪通道策略，n表示n周期的最大最小值
    rr=np.zeros([len(data),2])
    for i in np.arange(len(data)-n):
        if data[i+n,4]>data[i:i+n,2].max(): #收盘价大于了n周期的最大值
            rr[i+n,0]=1
            rr[i+n,1]=data[i+n,0]
        elif data[i+n,4]<data[i:i+n,3].min(): #收盘价小于了n周期的最小值
            rr[i+n,0]=-1
            rr[i+n,1]=data[i+n,0]
        else: #在通道之间
            rr[i+n,0]=rr[i+n-1,0]
            rr[i+n,1]=data[i+n,0]
    return rr
if __name__=='__main__':
    print('strategy main program can check the new strategy is running right or not.')
    data=np.loadtxt('data.csv',dtype=np.int,delimiter=',')
    m=500
    rr=ma(data,m)
    ma500=np.zeros(len(data))
    for i in np.arange(len(data)-m):
        #print(data[i+m,4],data[i:i+m,4].mean(),rr[i])
        #if i%20==0:
        #    input('continue?')
        ma500[i+m]=data[i:i+m,4].mean()
    for i in np.arange(len(data)):
        if (data[i,4]-ma500[i])*rr[i]<0:
            print(i)
