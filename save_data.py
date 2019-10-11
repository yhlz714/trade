from tqsdk import TqApi, TqSim
import sqlite3
api = TqApi(TqSim())
klines = api.get_kline_serial("SHFE.rb1910",60,600)
klines.drop('id',axis=1,inplace=True)
klines.drop('open_oi',axis=1,inplace=True)
klines.drop('close_oi',axis=1,inplace=True)
klines.drop('symbol',axis=1,inplace=True)
klines.drop('duration',axis=1,inplace=True)
conn=sqlite3.connect('data.db') #connect to database
c=conn.cursor()
res=c.execute('SELECT DATETIME FROM RB13 ORDER BY DATETIME DESC LIMIT 1') #get lastrow
for i in res:
	time=i
for i in range(len(klines)-1):
	if time[0]==klines.iloc[len(klines)-i-1,0]:   #search for where is last record time
		break
if i==len(klines)-2:
	print('Data have gaps or there is no data before!')
klines.drop(list(range(len(klines)-i)),inplace=True)
klines.to_sql('RB13',conn,if_exists='append',index=False)
conn.commit()
conn.close()
