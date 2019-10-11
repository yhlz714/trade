#erver
import sqlite3
import socket
import pandas as pd
address = ('0.0.0.0', 31500)
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM) # s = socket.socket()
s.bind(address)
s.listen(5)
ss, addr = s.accept()
#print( 'got connected from',addr)
while True:  # circle recive messige for doing things
    mes = ss.recv(512)
    mes=mes.decode()
    if mes=='q':
        break
    else: # dealing with data process
        start=mes
        ss.send(bytes('r',encoding='utf-8'))
        end=ss.recv(512).decode()
        ss.send(bytes('r',encoding='utf-8'))
        contract=ss.recv(512).decode()
        conn=sqlite3.connect('data.db')
        #c=conn.cursor()
        file=pd.read_sql('SELECT * FROM ['+contract+'] where datetime >'+start+' and datetime <='+end,conn)
        file.to_csv('temp.csv')
        ss.send(bytes('d',encoding='utf-8'))  #mean file is done let client to download it 
ss.close()
s.close()

