import socket
import paramiko
import pyalgotrade
import time
import pandas as pd
class DATA():
    #------------------------------SSH
    def __init__(self,ip='106.52.184.131',port=31500,name='ubuntu',password='86888196'):
        self.__port=port
        self.__ip=ip
        self.__username=name
        self.__password=password
    def call_back(self,size1,size2):
        print(size1,size2)
    def start_server(self):
        try:
            ssh=paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy()) #if this is first connect make it ok!
            ssh.connect(self.__ip,22,self.__username,self.__password)
            stdin,stdout,stderr = ssh.exec_command("nohup python3 data_server.py &")
            #print(stdout.read().decode('utf-8'))
        except Exception as e:
            print(e)
            ssh.close()
            return
        ssh.close()
        time.sleep(0.5) #wait for server running
        #------------------------------SSH finished    
    #------------------------------get csv file from server
    def get_csv(self,start_time='0',end_time=str(int(time.time()*1000000000)),contract='KQ.i@SHFE.rb'):  #defult end is now
        address = (self.__ip,self.__port)
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.connect(address)
            s.send(bytes(str(start_time),encoding='utf-8'))
            if s.recv(512)==b'r': #mean start received
                s.send(bytes(str(end_time),encoding='utf-8'))
                if s.recv(512)==b'r': #mean end received 
                    s.send(bytes(str(contract),encoding='utf-8'))
        except Exception as e:
            print(e)
            s.close()
            return
        while True: #wait for file ready and download it 
            mes=s.recv(512)
            if mes.decode()=='d':     #mean file is ready
                try: 
                    trans=paramiko.Transport((self.__ip,22))
                    trans.connect(username=self.__username,password=self.__password)
                    sftp = paramiko.SFTPClient.from_transport(trans)
                    sftp.get('/home/ubuntu/temp.csv','D:\\python3\\trade\\backtest_optimize\\'+str(contract).replace('.','')+'.csv',self.call_back)
                except Exception as e:
                    print(e)
                    trans.close()
                    return
                trans.close()
                break
            time.sleep(0.5)
        s.send(bytes('q',encoding='utf-8')) #close server
        s.close()
    def feed(contract='KQ.i@SHFE.rb'):
        feed=pyalgotrade.barfeed.csvfeed.GenericBarFeed('Frequency.MINUTE')
        feed.addBarsFromCSV('KQ.i@SHFE.rb','D:\\python3\\trade\\backtest_optimize\\'+str(contract).replace('.','')+'.csv')
        return feed