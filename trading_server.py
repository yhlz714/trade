#new way to trading server
from tqsdk import TqApi,TqAccount,TargetPosTask,TqSim
import time
import os
import logging
import strategy as stg
class Yhlz_Task(TargetPosTask): #对tqsdk的task类略加补充
    def __init__(self,api, symbol, price="ACTIVE", offset_priority="今昨,开"):
        super().__init__(api, symbol, price, offset_priority)
        sel.contract=symbol
############--------------initial
logging.basicConfig(filename='log_try.txt',filemode='a',level = logging.INFO,format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
whole_stg=[]
whole_task=[]
print('This is yhlz\'s trading server,now started!\n')
try:
    #api=TqApi(TqAccount('快期模拟','284837','86888196'))
    #api=TqApi(TqAccount('simnow','133492','Yhlz0000'))
    #logging.info('success sign in! with simnow')
    api=TqApi(TqAccount('H华安期货','100909186','Yhlz0000'))
    logging.info('success sign in! with 100909186')
except Exception:
    logging.info('problem with sign in!')
    raise SystemExit
#############--------------add strategy area
account=api.get_account()   #account is a value is a object can used as account.balence etc.
position=api.get_position() #position is a dict where the key is contract,value is each contract's features 

##############-------------cross_ma
pos_SHFErb_main=Yhlz_Task(api,'SHFE.rb2001',price='PASSIVE')
kli_SHFErb_main=api.get_kline_serial("KQ.i@SHFE.rb",60)
quo_SHFErb_main=api.get_quote("KQ.i@SHFE.rb")
whole_task.append(pos_SHFErb_main)
cross_ma=stg.strategy("KQ.i@SHFE.rb",whole_task,kli_SHFErb_main,account,position,stg.cross_ma,quo_SHFErb_main,api,[108,694,0,0,0,0])  #make a cross_ma instancce for strategy
whole_stg.append(cross_ma)
##############-------------cross_ma finished

#############--------------add strategy area finished
contral=''
while True: 
    now=time.localtime(time.time())
    ############--------------run strategy
    for strategy in whole_stg:
        strategy.run()
    ############--------------execute order
    whole_stg[0].executer_order()
    if now.tm_hour==15 or now.tm_hour==23 or contral=='q':
        for strategy in whole_stg:
        strategy.run()
        whole_stg[0].target_position.to_csv('target_position.csv',index=False)  #store target postion to file
        logging.info('stop running!')
        break
api.close()