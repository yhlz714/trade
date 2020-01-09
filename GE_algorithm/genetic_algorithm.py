#初级的遗传编程，使用brainfuck语言即+.,[]><所组成的图灵完备语言
#用0-6代表这几个字符串，随机生成一个700位长的整形np数组，来代表
#个体的基因，也就是所编的程序，用rb指数的收盘减开盘，作为数据，1为
#涨，0为跌，用之前的所有数据去预测未来的100个，优化为胜率较高的方
#向为避免死循环问题，如果该程序输出足够100即终止该程序的运行，若直
#到最后也不足一百，则默认余下的全部为0，
#       +.,[]><对应0，1，2，3，4，5，6
import pdb
import numpy as np
import pandas as pd
#p=0.1 #变异概率
pdb.set_trace()
f=open('data.csv','r')
data=f.readlines()
f.close()
for i in list(range(len(data))):
    data[i]=bool(int(data[i].replace('\n',''))) #去掉换行符
data=np.array(data) #转换成numpy的数组
result=np.zeros(100,dtype=np.bool_) #存储所有个体的返回结果
memory=np.zeros(1000,dtype=np.bool_) #个体的读写空间
community=np.random.randint(0,7,(100,701)) #存储所有个体顺便初始化为0-6之间的随机数最后一行记胜率
#######--------数据循环，模拟现实中的时间变化---------###########
for i in list(range(1000,len(data)-100)): #让最开始有1000个数据可以获取
    #a=a[a[:,2].argsort()]  对某列进行排序，然后其他列跟着变的写法，array是a，变化的列是第三列即[:,2]
    for j in list(range(100)): #100个个体都在community里面计算每个个体适应度的循环
        #print('j value is:',j)
        k=0
        count1=0    #用来避免死循环，超过10w次自动退出
        pointer=0 #指针，用来指定这个个体读写与改变的值在memory中的位置
        pointer_res=0 #输出到 result的指针
        pointer_data=1 #提取数据的指针
        while k<700: #没有运行到结束运行个体程序,下面可以看作是brainfuck语言的解释器
            #print('k value is:',k)
            #print('count1 value is:',count1)
            if community[j,k]==0:   #改变当前单元格内容
                memory[pointer]=not memory[pointer] #取反
                count1=count1+1
            elif  community[j,k]==1: #输出内容
                result[pointer_res]=memory[pointer]
                pointer_res=pointer_res+1
                count1=count1+1
                if pointer_res==100: #写满100次，自动退出
                    break
            elif  community[j,k]==2:
                memory[pointer]=data[i-pointer_data]
                pointer_data=pointer_data+1
                if pointer_data==i:  #如果取数据超过已有数据则重新轮回再来一次
                    pointer_data=1
                count1=count1+1
            elif  community[j,k]==3:
                if memory[pointer]==False:
                    time=0 #计算需要找到多少个对应的反括号
                    while True:  #要找到对应的括号
                        k=k+1
                        if community[j,k]==3:
                            time=time+1
                        if community[j,k]==4:
                            if time==0:  #跳出了这个循环
                                break
                            else:
                                time=time-1 #否则time减1
                        if k>699:  #找到最后还没找到，说明，括号不匹配，致死，这个个体未输出的值，全部是0
                            break
                count1=count1+1
            elif  community[j,k]==4:
                if k==0: #当k在这个个体上第一次为0时memory是不会为真的，这种情况只有运行到后面正括号不匹配，
                    break #而第一个位置又正好是反括号，当k=k-1以后就直接变-1无法退出，所以此处多一次判断，直接致死
                if memory[pointer]==True:
                    time=0
                    while True:
                        k=k-1
                        if community[j,k]==4:
                            time=time+1
                        if community[j,k]==3:
                            if time==0:
                                k=k-1 #因为大循环会默认k+1所以这里需要多减一次
                                break
                            else:
                                time=time-1
                        if k==0: #找到开头还没找到，把开头当成循环的起始位置
                            k=-1 #因为此时当前内存的数值为真所以直接从头开始继续运行
                            break
                count1=count1+1
            elif  community[j,k]==5:
                if pointer!=999:
                    pointer=pointer+1
                else: #超过1000回到0
                    pointer=0
                count1=count1+1
            elif  community[j,k]==6:
                if pointer!=0:
                    pointer=pointer-1
                else:
                    pointer=999
                count1=count1+1
            if count1>10000: #有死循环嫌疑。
                #print('break!: ',i)
                break
            k=k+1 #每执行一次，代码指针向后移
        memory=np.zeros(1000,dtype=np.bool_) #重新初始化
        count=0 #统计正确个数
        l=0
        while l<100:   #每行都是一个个体的返回值
            if result[l]==data[i+l]:  #这里用i+l是因为设定默认第i个数据测试的时候是无法获取的。
                count=count+1
            l=l+1
        result=np.zeros(100,dtype=np.bool_)
        community[j,-1]=count #将结果赋值到这个策略的最后一个位置
        #print('count times:',count)
    community=community[community[:,-1].argsort()] #根据胜率排序排好为升序
    #最优的四十个个体交配产生二十个新个体，替换最差的20个
    cross_position=np.random.randint(1,700,20) #1到700之间产生20个随机数（这样的写法1可以取，第701个不会，也就是说交叉点不会出现在基因的两端，因为这样就等于完全复制了，交叉点的值使用后面那个个体的）
    #####--------------------重组--------------------------##############
    j=1
    while j<=40:
        community[int((j-1)/2),:]=np.append(community[-j,0:cross_position[int((j-1)/2)]],community[-j-1,cross_position[int((j-1)/2)]:701]) #把后面两个个体交配形成的个体放在前面
        j=j+2
    #####-------------------变异--------------------------###############
    j=0
    while j<700:
        change_position=np.random.randint(0,100) #变异的位置
        change_value=np.random.randint(0,7) #变异的结果值
        community[change_position,j]=change_value #变异
        j=j+1
    print('第',i,'轮的平均值是',community[:,700].mean()) #看下结果

