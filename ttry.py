import logging

logger = logging.getLogger('yhlz')

f = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

sh = logging.StreamHandler()
sh.setLevel(logging.INFO)
sh.setFormatter(f)

fh = logging.FileHandler('log.txt','a')
fh.setLevel(logging.ERROR)
fh.setFormatter(f)

eh = logging.handlers.SMTPHandler()

logger.addHandler(fh)
logger.addHandler(sh)

mail_handler = logging.handlers.SMTPHandler(
        mailhost=('smtp.qq.com', 465),
        fromaddr='517353631@qq.com',
        toaddrs='517353631@qq.com',
        subject='what erver',
        credentials=('517353631@qq.com', '客户端授权密码'))
# 4. 单独设置 mail_handler 的日志级别为 ERROR
mail_handler.setLevel(logging.WARNING)
mail_handler.setFormatter(f)
# 5. 将 Handler 添加到 logger 中
logger.addHandler(mail_handler)

logger.setLevel(logging.DEBUG)

logger.debug('123')
logger.info('456')
logger.error('789')
logger.warning('101112')