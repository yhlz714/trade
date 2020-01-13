# erver
import sqlite3
import socket
import pandas as pd
import pdb
#pdb.set_trace()
address = ('0.0.0.0', 31500)
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # s = socket.socket()
s.bind(address)
while True:
    s.listen(5)
    ss, addr = s.accept()
    # print( 'got connected from',addr)
    while True:  # circle recive messige for doing things
        mes = ss.recv(512)
        mes = mes.decode()
        if mes == 'q':
            ss.close()
            break
        elif len(mes)==0: #如果客户端close了，recv会解阻塞，返回长度为0
            ss.close()
            break
        else:  # dealing with data process
            start = mes
            ss.send(bytes('r', encoding='utf-8'))
            end = ss.recv(512).decode()
            ss.send(bytes('r', encoding='utf-8'))
            contract = ss.recv(512).decode()
            conn = sqlite3.connect('future_data.db')
            # c=conn.cursor()
            file = pd.read_sql('SELECT * FROM [' + contract.replace('.', '') + ']', conn)
            file = file.loc[(file['Date Time'] > start) & (file['Date Time'] < end) , :]
            file.to_csv('temp.csv', index=False)
            ss.send(bytes('d', encoding='utf-8'))  # mean file is done let client to download it
    if mes=='q':
        break
s.close()
