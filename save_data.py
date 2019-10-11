from tqsdk import TqApi, TqSim
import sqlite3
import pandas as pd
import os
api = TqApi(TqSim())
#os.system('cd C:\Users\yhlz\AppData\Local\Programs\Python\Python37\trade\')
os.system('rm -f data.db.bak')            #this two step is protect database not jumbled by program underneath 
os.system('cp data.db data.db.bak')   #if something wrong with program delete data.db and get bak file back
conn=sqlite3.connect('data.db') #connect to database
c=conn.cursor()
info=pd.read_csv('general_tiker_info.csv')
def process(name):
    global contract
    print('processing: '+name)
    contract[name].drop('id',axis=1,inplace=True)
    contract[name].drop('open_oi',axis=1,inplace=True)
    contract[name].drop('close_oi',axis=1,inplace=True)
    contract[name].drop('symbol',axis=1,inplace=True)
    contract[name].drop('duration',axis=1,inplace=True)
    res=c.execute('SELECT DATETIME FROM ['+name+'] ORDER BY DATETIME DESC LIMIT 1') #get lastrow
    for i in res:
    	time=i
    for i in range(len(contract[name])-1):
    	if time[0]==contract[name].iloc[len(contract[name])-i-1,0]:   #search for where is last record time
    		break
    if i==len(contract[name])-2:
    	print('Data have gaps or there is no data before!')
    contract[name].drop(list(range(len(contract[name])-i)),inplace=True)
    contract[name].to_sql(name,conn,if_exists='append',index=False)
contract={}
for name in info.index_name:
        klines=api.get_kline_serial(name,60,1200)
        contract[name]= klines.copy()
for name in info.contract_name:
        klines=api.get_kline_serial(name,60,1200)
        contract[name]= klines.copy()
for name in info.index_name:
        process(name)
for name in info.contract_name:
        process(name)
print('successed!')
conn.commit()
conn.close()
api.close()
