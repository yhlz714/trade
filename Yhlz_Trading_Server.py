#tHIS is yhlz's trading program base on tqsdk.
import threading
import os
from tqsdk import TqApi,TqAccount,TargetPosTask,TqSim
import time
import datetime
import strategy as stg
import pdb
import pandas as pd
import random
import numpy as np
import logging
logging.basicConfig(filename='log.txt',filemode='a',level = logging.INFO,format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
#logging.basicConfig(level = logging.INFO,format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
#pdb.set_trace()
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
contral=''		#use for contral the whole program stop or not ,if it equal to 'q' then progam stoped
account=api.get_account()   #account is a value is a object can used as account.balence etc.
position=api.get_position() #position is a dict where the key is contract,value is each contract's features 
class Get_Input(threading.Thread):		# this thread contral wheather to stop whole program
    def run(self):
        global contral
        while True:
            contral=input('press q to quit!')
            logging.info(contral)
            logging.info(time.ctime())
            now=time.localtime(time.time())
            if now.tm_hour==15 or now.tm_hour==3 or contral=='q':
                logging.info('Ready to quit')
                return 
#######---------------------------get all data and all strategy needed ready-------------------------------------#######
f=open(r'strategytorun.txt')
strategy_list=f.readlines() #a list of strategy need to run
f.close()
data=[]
for i in range(len(strategy_list)): #remove '\n'
    strategy_list[i]=eval(strategy_list[i].replace('\n',''))
    for j in range(1,len(strategy_list[i])):   #the strategy_list[i][0]is strategy name so don't append it
        data.append(strategy_list[i][j]) #get data needed in 'data'
data=list(set(data)) # eliminate duplicates
data_var={} #because variable name can't has a '.' or '@' so this dict's key is contract name ,value is legal variable name such as {'KQ.m@SHFE.rb':'KQmSHFErb'}
for i in data:
    data_var[i]=i.replace('@','').replace('.','')
#data is a string list include all needed data,all this string is evaled and become a 
#variable. so when you need to use the kline by name a varible you can get a 'for loop',and eval(data[...]) 
for key in data_var:
    exec(data_var[key]+'=api.get_kline_serial(\''+key+'\',60,1500)')  #Get one minute kline.
'''
for key in quote_var:
    if 'KQ.i' in key:      # get quote is for underlying symbol,index contract's underlying doesn't exist
        quote_var[key]=quote_var[key].replace('i','m')
    exec(quote_var[key]+'=api.get_quote(key)')
'''
target_position=pd.read_csv('target_position.csv')
#print(dir())
#print(data_var)
#print(target_position)
#print(quote_var)
# here use 'variety' as a variable to represent all future varietys as string,then when eval ,all that string 
#become some variables even don't konw what is it so can't use it drictly, but can use it by 'eval(variety)'
#or 'target_position.keys'
#------------------temp executer initial--------------------------------------------------------

pos_SHFErb2001= TargetPosTask(api,'SHFE.rb2001',price='PASSIVE')
###-----------------------------------------------------------------------------------inital finished-----------------------------------------------------------------###


'''
class Executer():

    def __init__(self,api):      #initial Executer set for all target order task
        global target_position
        self.api = api
        self.quote_var={}       #need quote and key is same with data_var

        # initial for quote
        for i in target_position[contract]:                                                                  
            self.quote_var[i]='q_'+i.replace('@','').replace('.','')
        for key in postion.keys():
            self.quote_var[key]='q_'+key.replace('@','').replace('.','')
        for key in self.quote_var:
            if 'KQ.i' in key and key.replace('i','m') not in sel.quote_var.keys():      # get quote is for underlying symbol,index contract's underlying doesn't exist,and if not exist main contract,get 
                quote_var[key]=quote_var[key].replace('KQ.i','KQ.m')                          #main contract quote for index
            if quote_var[key] not in dir():  
                exec(quote_var[key]+'=api.get_quote(key)')
        
        # initial target task
        self.pos_task={}
        for key in target_position['contract']:
            if 'KQ.i' in key:
                self.pos_task['key']='pos_'+eval(f'{self.quote_var[key.replace(\'KQ.i\',\'KQ.m\')]}.underlying_symbol').replace('@','').replace('.','')
                exec('self.pos_task[key]=TargetPosTask(api,'+eval(f'{self.quote_var[key.replace(\'KQ.i\',\'KQ.m\')]}.underlying_symbol')+')')
            else:
                self.pos_task['key']='pos_'+eval(f'{self.quote_var[key]}.underlying_symbol').replace('@','').replace('.','')
                exec('self.pos_task[key]=TargetPosTask(api,'+eval(f'{self.quote_var[key]}.underlying_symbol')+')')
        for key in postion.keys():
            if '_' not in key:  #position obj have some defult keys,start with '_',set holding contract in target task is for swap contract use
                if key not in self.pos_task.keys():
                    self.pos_task['key']='pos_'+eval(f'{self.quote_var[key]}.underlying_symbol').replace('.','')
                    exec(f'{self.pos_task[key]}= TargetPosTask(api,'+eval(f'{self.quote_var[key]}.underlying_symbol')+')')
        
        #check main contract
        for i in range(len(target_position)):
            if 'KQ.i' in i:
                if eval('self.quote_var[target_position.iloc[i,1].replace(\'KQ.i\',\'KQ.m\')]').underlying_symbol !=target_position[i,4]:       #contract changed!
                    target_position[i,3]=True
            else:
                if eval('self.quote_var[target_position.iloc[i,1]]').underlying_symbol !=target_position[i,4]:       #contract changed!
                    target_position[i,3]=True
    
    def __set_active(self,symbol):
        eval(f'{self.pos_task[symbol]}.price=\'ACTIVE\'')
    def __get_close_time(self,symbol):
        for i in range(len(target_position)):
            if target_position.iloc[i,1]==symbol:
                time_str=target_position.iloc[i,5]
                break
        self.time_list=eval(time_str)

    def set_target(self):
        global target_position
        self.target=target_position.copy()
        finnal_target={}
        for i in range(len(self.target)):
            if 'KQ' in self.target.iloc[i,1]:
                self.target.iloc[i,1]=self.quote_var[self.target.iloc[i,1].replace('KQ.i','KQ.m')].underlying_symbol
            if self.target.iloc[i,1] not in finnal_target.keys():
                finnal_target[self.target.iloc[i,1]]=self.target.iloc[i,2]
            else:
                finnal_target[self.target.iloc[i,1]]+=self.target.iloc[i,2]
            if self.target.iloc[i,3]==True:                                 #need to change old contract target
                finnal_target[self.target.iloc[i,4]]-self.target.iloc[i,2]
                target_position.iloc[i,4]=self.target.iloc[i,1]             # change the old contract
                target_position.iloc[i,3]=False

        for key in self.pos_task:
            now=datetime.datetime.now()
            self.__get_close_time(key)
            a=datetime.datetime.now()-datetime.datetime(now.year,now.month,now.day,self.time_list[0],self.time_list[1])
            b=datetime.datetime.now()-datetime.datetime(now.year,now.month,now.day,self.time_list[2],self.time_list[3])
            if (a.days>=0 and a.seconds<130) or (b.days>=0 and b.seconds<130):
                self.__set_active(key)

'''

#get_input=Get_Input()
#get_input.setDaemon(True)
#get_input.start()
now_record=61 #record minute time
#print('now is ready to run strategy!')
when=0
#executer=Executer(api)
while True:
    api.wait_update(time.time()+1)
    #print(time.ctime())
    now=time.localtime(time.time())
    if now.tm_min==30 or now.tm_min==0:
        #pass
        time.sleep(0.5)  #avoid some exception like when updated and send order but exchange refused ,then wait 0.5s
    run=0
    for contract in data_var.values():
        #print(dir())
        #print(type(KQmSHFErb))
        if eval('api.is_changing('+contract+'.iloc[-1],\'datetime\')'): #data is change
            run=1
            #print('run strategy')
            break
    if run:
        time.sleep(0.5)
        run=0
        for i in strategy_list:
            #print(i)
            j=1
            tt=''
            while j<len(i):
                tt=tt+data_var[i[j]]+'.drop([\'id\',\'open_oi\',\'close_oi\',\'symbol\',\'duration\'],axis=1).drop(1499).to_numpy()'
                tt=tt+','
                j=j+1
            tt=i[0]+'('+tt
            rr=eval('stg.'+tt+'position,account)')
            #give all strategy data,postion and account
            #then strategy have all freedom to make every kind of strategy
            for j in range(1,len(i)):   #one strategy may have more then one target position
                for k in range(len(target_position)):
                    if i[0]==target_position.iloc[k,0] and i[j]==target_position.iloc[k,1]:
                        target_position.iloc[k,2]=int(rr[-1,j-1])  #rr[:,-1] is time                
        #executer.set_target()
        logging.info('target_position:')
        logging.info(target_position)
        logging.info(time.ctime())
#--------------------------------------temp_executer

        for key in range(len(target_position)):
            if time.time()-when>5 and position['SHFE.rb2001'].volume_long-position['SHFE.rb2001'].volume_short != target_position.iloc[0,2]:
                #print('set position')
                when=time.time()
                pos_SHFErb2001.set_target_volume(int(target_position.iloc[0,2]))
                #target_position[key]=0
        #print(time.ctime())
        logging.info('account position is: ')
        logging.info(str(position['SHFE.rb2001'].volume_long-position['SHFE.rb2001'].volume_short))
        logging.info('-----------------------------------')
#---------------------------------------end-------
    if now.tm_hour==15 or now.tm_hour==23 or contral=='q':
        target_position.to_csv('target_position.csv',index=False)  #store target postion to file
        logging.info('stop running!')
        break
#get_input.join()
api.close()
