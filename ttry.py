import logging
from logging.handlers import SMTPHandler

# logger = logging.getLogger('yhlz')
#
# f = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
#
# sh = logging.StreamHandler()
# sh.setLevel(logging.INFO)
# sh.setFormatter(f)
#
# fh = logging.FileHandler('log.txt', 'a')
# fh.setLevel(logging.ERROR)
# fh.setFormatter(f)
#
# logger.addHandler(fh)
# logger.addHandler(sh)
#
# mail_handler = SMTPHandler(
#         mailhost='smtp.qq.com',
#         fromaddr='517353631@qq.com',
#         toaddrs='517353631@qq.com',
#         subject='what erver2',
#         credentials=('517353631@qq.com', 'kyntpvjwuxfvbiag'))
# # 4. 单独设置 mail_handler 的日志级别为 ERROR
# mail_handler.setLevel(logging.WARNING)
# mail_handler.setFormatter(f)
# # 5. 将 Handler 添加到 logger 中
# logger.addHandler(mail_handler)
#
# logger.setLevel(logging.DEBUG)
#
# # logger.debug('123')
# # logger.info('456')
# # logger.error('789')
# logger.warning('second try!')

class TargetPosTaskSingleton(type):

    # def __new__(cls, class_name, class_parents, new_attr):
    #     print('012')
    #     return type(class_name, class_parents, new_attr)

    def __call__(cls):
        print(123)

    def aaa(cls):
        print(234)

class second(metaclass = TargetPosTaskSingleton):
    def __init__(self):
        self.b=123
        print(345)