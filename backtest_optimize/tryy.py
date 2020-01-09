from tkinter import *

root = Tk()
label = Label(root)
label.pack()
def yyy(event):
    print('success')
    root.event_generate('<<try>>')


def bbb(event):
    print('ok')
root.bind('<<try>>',bbb)
root.bind('<Button-1>',yyy)

root.mainloop()