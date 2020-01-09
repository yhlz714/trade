import pandas as pd
import sqlite3
import os

# conn = sqlite3.connect('../../data.db')
# name = pd.read_csv('../general_tiker_info.csv')
# for contract in name['contract_name']:
#     print(contract)
#     file = pd.read_sql('SELECT * FROM [' + contract + ']', conn)
#     file['datetime'] = file['datetime'] / 1000000000
#     file.to_sql(contract, conn,if_exists='replace',index=False)
# for contract in name.index_name:
#     print(contract)
#     file = pd.read_sql('SELECT * FROM [' + contract + ']', conn)
#     file['datetime'] = file['datetime'] / 1000000000
#     file.to_sql(contract, conn, if_exists='replace', index=False)
# conn.commit()
# conn.close()

conn = sqlite3.connect('../../future_data.db')
for item in os.listdir(r'../../数据/'):
    temp = pd.read_csv(r'../../数据/' + item, encoding='gbk')
    temp.columns = ['Date Time', 'Open', 'High', 'Low', 'Close', 'Volume', 'Adj Close']
    temp['Adj Close'] = 0
    temp.to_sql(item.replace('.csv', ''), conn, if_exists='fail', index=False)

conn.commit()
conn.close()