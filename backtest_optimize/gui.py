import pandas as pd
import numpy as np
import math
from tkinter import *

# 创建窗口
root = Tk()
# 创建并添加Canvas
bigFrame = Frame(root)
frame = Frame(bigFrame)

cv = Canvas(frame, background='black', width=1800, height=800)
cv.pack(fill=BOTH, expand=YES)

def setLable(string):
    global v
    v.set(string)

frame.pack(fill=BOTH, expand=YES)
#Button(bigFrame, text='get big',command=lambda cv=cv:callback(cv)).pack(side=BOTTOM)
v = StringVar()
Label(frame, textvariable=v).pack(side=BOTTOM)
v.set('try')
hbar=Scrollbar(frame, orient=HORIZONTAL)
hbar.pack(side=BOTTOM, fill=X)
hbar.set(1,1)
frame1 = Frame(frame)


class Kline():
    def __init__(self, canvas, scrollbar, data=None):
        """
        画k线图类
        :param canvas: 画布widget
        :param scrollbar: 滚动条widget
        :param data: 包含某个品种的所有数据的df，列应该有'Datetime','Open','High','Low','Close','Adjclose'
        """
        self.canvas = canvas
        self.canvas.focus_set()
        self.canvas.width = int(self.canvas['width'])      #将固定的宽度和高度变为属性,本来是str 需要int强制转换
        self.canvas.hight = int(self.canvas['height'])      #如果发生<Configure>事件，也可以修改这两个
        self.scrollbar = scrollbar
        if not isinstance(data,pd.DataFrame):
            self.data = pd.DataFrame()
        else:
            self.addData(data)

        self.num = 200 #默认画的k线数目
        self.place = -1
        self.item = []    #装所有的create的名字
        self.crossItem = []  #croosHair 的名字
        self.showCross = False   #是否显示十字线
        self.dataTemp = pd.DataFrame() #用来装当前显示的数据
        self.delta = 2 #初始k线变动像素

    def addData(self, data):
        """
        添加或者更改总的数据
        :param data:包含某个品种的所有数据的df，列应该有'Datetime','Open','High','Low','Close','Adjclose'
        :return: None
        """
        self.data = data
        self.data['Date Time'] = pd.to_datetime(self.data['Date Time'])
        self.data.sort_values(by=['Date Time'], ascending=False)  # 降序排列

        # 检查是否按照规定顺序排列，一边后面减少计算时间
        order = ['Adj Close', 'Volume', 'Close', 'Low', 'High', 'Open', 'Date Time']
        for i in self.data.columns:
            if i != order[-1]:
                print('column name order error!')
                exit(1)
            order.pop()

    def draw(self, place=-1):
        """
        在画布上画data数据，每次发生位置变化，或者数据变化，都调用这个函数，然后设置scrollbar的位置
        :param place: 默认从最后也就是1的位置画，函数自动计算从右到左应该画多大的距离,如果place大于1，则表示为绝对位置，在总DF中
        :return: None
        """
        if place == -1: #初始值，表示最后的位置
            place = place + len(self.data)

        if self.place == -1:
            self.place = place

        if place <= self.num * 2:  #确保不会超量程，当为0的时候，place在df的最前，但是还要有两倍self.num个数据，来保证画图
            place = self.num * 2

        dataTemp = self.data.loc[place - 2 * self.num : place, :].copy()
        dataTemp.reset_index(drop=True, inplace=True)
        self.dataTemp = dataTemp.copy()
        max = dataTemp['High'].max() #获取数据最大值
        min = dataTemp['Low'].min() #获取最小值
        widthOffset = 30
        hightOffset = 10
        self.hight = self.canvas.hight - hightOffset #去掉10的用来画坐标轴空间
        self.width = self.canvas.width - widthOffset

        self.canvas.create_line((25, 0), (25, self.hight), fill='red', width=2)
        for i in range(4):
            self.canvas.create_line((25, (i+1)*self.hight/5), (32, (i+1)*self.hight/5), fill='red')  #画4条线当轴上的刻度
            text = str(round(max - (i + 1)  / 5  * (max-min) , 2))
            #print(max,min,text)
            self.canvas.create_text(13, (i+1)*self.hight/5, text=text, fill='white',anchor=W)

        self.canvas.create_line((0, self.canvas.hight - 8), (self.width, self.canvas.hight - 8), fill='red', width=2)
        xPlace = [] #记录横坐标刻度的位置
        for i in range(4):
            self.canvas.create_line(((i+1)*self.width/5, self.canvas.hight - 8),
                                    ((i+1)*self.width/5, self.canvas.hight - 15), fill='red')  #画4条线当轴上的刻度
            xPlace.append((i+1)*self.width/5)



        dataTemp['Open'] = \
            (self.hight - (dataTemp['Open']-min) * self.hight /(max - min)).astype(int)  #转换成为像素的y坐标的位置
        dataTemp['High'] = \
            (self.hight - (dataTemp['High']-min) * self.hight /(max - min)).astype(int)
        dataTemp['Low'] =\
            (self.hight - (dataTemp['Low']-min) * self.hight /(max - min)).astype(int)
        dataTemp['Close'] = \
            (self.hight - (dataTemp['Close']-min) * self.hight /(max - min)).astype(int)
        widthDelta = math.floor(self.width/self.num)
        self.widthDelta = widthDelta

        #datatemp 的列【Date Time,	Open,	High,	Low,	Close,	Volume,	Adj Close】
        j=len(dataTemp)-1
        i=self.canvas.width -widthDelta #对整个画布的宽度进行循环，从右向左画,每次取出最后1个画，一个循环的最后，删掉最后一个
        while i > widthOffset :  #默认画200个
            # 因为这里已经转换为像素了，所以收盘价大于开盘价的像素位置，其实是下跌，所以画绿色
            if dataTemp.iloc[j, 1] < dataTemp.iloc[j, 4]:
                color = 'green'
            else:
                color = 'red'
            self.canvas.create_line((i + self.delta, dataTemp.iloc[j, 2]),
                                    (i + self.delta, dataTemp.iloc[j, 3]), fill=color)
            if self.num != 800:
                if color == 'green':
                    self.canvas.create_rectangle((i, dataTemp.iloc[j, 1]),
                                                 (i + 2 * self.delta, dataTemp.iloc[j, 4]), fill=color,
                                                 outline=color)
                else:
                    self.canvas.create_rectangle((i, dataTemp.iloc[j, 4]),
                                                 (i + 2 * self.delta, dataTemp.iloc[j, 1]),
                                                 fill='black', outline=color)

            if xPlace and i-widthDelta < xPlace[-1] and i >= xPlace[-1]:
                text = str(dataTemp.iloc[j, 0])
                self.canvas.create_text(i,self.hight + 5, text=text, fill='white')
                xPlace.pop()
            i -= widthDelta
            j -= 1


    def redraw(self, *args):
        """
        根据滚动条重画,先删除原有的，再重画
        :param place: 获取开始的位置
        :return: None
        """
        #print(args)
        if len(args)==2:  #有时会有些其他的返回。
            #print(args)
            self.canvas.delete(ALL)
            self.place = round(float(args[1]) * len(self.data))
            self.draw(self.place)

        self.sendback()

    def sendback(self):
        """
        返回位置信息给滚动条
        :param scrollbar: 滚动条对象
        :return: None
        """
        #print()
        self.scrollbar.set(self.place / len(self.data), (self.place + self.num) / len(self.data)) #滑块的长度为当前显示的大小占总数据长度的比率

    def mouseMove(self, event):
        """
        bind到鼠标移动事件
        :return: None
        """
        if self.showCross:
            string = self.drawCross(self.canvas.canvasx(event.x), self.canvas.canvasy(event.y))
            setLable(string)

    def click(self, event):
        """
        bind左键到点击事件,设一个真值，如果点击了就显示十字光标，再点一次就不显示了
        :param event:
        :return: None
        """
        if self.showCross==False:
            self.showCross=True
            string = self.drawCross(self.canvas.canvasx(event.x),self.canvas.canvasy(event.y))
            setLable(string)
        else:
            self.showCross = False
            for item in self.crossItem:
                self.canvas.delete(item)   #删掉横线和竖线

    def drawCross(self, x, y):
        """
        设置label的值
        :return: str 需要显示的各种信息，比如当前坐标的价格日期等等
        """
        if self.crossItem:
            for item in self.crossItem:
                self.canvas.delete(item)   #删掉横线和竖线
        place = round( (self.canvas.width - (x-2) ) /self.widthDelta )
        string = ''
        for i in range(self.dataTemp.shape[1]):
            string += (self.dataTemp.columns[i] + ' :' + str(self.dataTemp.iloc[-place, i]) + ' ')
        self.x=x
        self.y=y
        self.crossItem.append(self.canvas.create_line(x, 0, x, self.hight, fill='white'))
        self.crossItem.append(self.canvas.create_line(0, y, self.width, y, fill='white'))
        return string

    def click2(self,event):
        self.canvas.delete(CURRENT)

    def backward(self):
        """
        向历史移动一个屏幕
        :return:
        """
        if self.place > self.num :
            self.canvas.delete(ALL)
            self.draw(self.place - self.num)
            self.place -= self.num

    def forward(self):
        """
        向未来移动一个屏幕
        :return:
        """
        if self.place < (len(self.data) - self.num):
            self.canvas.delete(ALL)
            self.draw(self.place + self.num)
            self.place += self.num

    def bigger(self,event):
        """
        显示更少的k线，使每个k线变大
        :return:
        """

        if self.num >= 50:
            self.num /= 2
            self.delta *= 2

        self.canvas.delete(ALL)
        self.draw(self.place)

    def smaller(self, event):
        """
        显示更多的k线，使每个k线变小
        :return:
        """

        if self.num <= 800:
            self.num *= 2
            self.delta /= 2

        self.canvas.delete(ALL)
        self.draw(self.place)

data = pd.read_csv('KQi@SHFErb.csv')
kline = Kline(cv, hbar, data)
cv.bind('<Button-1>', kline.click)
cv.bind('<Motion>', kline.mouseMove)
cv.bind('<Button-3>', kline.click2)
cv.bind('<KeyPress-Up>', func=kline.bigger)
cv.bind('<KeyPress-Down>', func=kline.smaller)

kline.draw()
hbar.config(command=kline.redraw)
bLeft = Button(frame1,text= 'backward',command=kline.backward)
bRight = Button(frame1,text= 'forward',command=kline.forward)
bLeft.pack(side=LEFT, fill=BOTH,expand=YES)
bRight.pack(side=RIGHT, fill=BOTH,expand=YES)
frame1.pack(side=BOTTOM,fill=X)

bigFrame.pack(fill=BOTH, expand=YES)
root.mainloop()
