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
cv = Canvas(root)
cv.create_line([0, 0, 100, 100], arrow='last')
cv.pack()

root.mainloop()