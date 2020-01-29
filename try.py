import global_var
import threading
import time

def tt():
    while True:
        print('123')
        time.sleep(2)

if __name__ == '__main__':
    t = threading.Thread(target=tt)
    t.start()
    t.join()