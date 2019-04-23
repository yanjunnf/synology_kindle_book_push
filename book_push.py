# -*- coding: utf-8 -*-

import time
import shutil
import os.path
import smtplib
import hashlib
import logging
from email.header import Header
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# The maxinum file size 20MB
max_file_size = 20
# Checking interval: 30 mins
check_interval = 60 * 30
debug = False
# Book directory
if debug:
    filepath = "D:\\books\\"
    scriptpath = 'd:\\Workspace\\python\\yrd_test\\'
else:
    filepath = "/var/services/homes/yanjunnf/Baidu/Book/"
    scriptpath = '/volume1/homes/yanjunnf/Projects/'
    # filepath = "D:\\Tools\\"

HOST = 'smtp.126.com'
SUBJECT = 'Book'
FROM = 'yanjunnf@126.com'
PASS = 'Your_Secret_Password'
# To = 'yanjunnf@kindle.cn'
log_file = 'book_sender.log'
# Create logger object
logger = logging.getLogger('BOOkSENDER')
logger.setLevel(logging.DEBUG)

fh = logging.FileHandler(scriptpath + 'send_book.log')
fh.setLevel(logging.DEBUG)

#Define output text format
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
fh.setFormatter(formatter)
logger.addHandler(fh)
retry_times = 3

# Define users
if debug:
    users = {
        'ruby': {
            'dir': 'D:\\books\\',
            'mailto': 'chenguoqunbj@kindle.cn'
        }
    }
else:
    users = {
        'yanjun': {
            'dir': '/var/services/homes/yanjunnf/Baidu/Book/yanjun',
            'mailto': 'yanjunnf@kindle.cn',
        },
        'ruby': {
            'dir': '/var/services/homes/yanjunnf/Baidu/Book/ruby',
            'mailto': 'chenguoqunbj@kindle.cn',
        }
    }



def send_book(filepath, filename, mailto):
    success = False
    for i in range(0, retry_times):
        try:
            # 创建要发送的邮件正文及附件对象
            # related 使用邮件内嵌资源，可以把附件中的图片等附件嵌入到正文中
            msg = MIMEMultipart('related')
            msg.attach(MIMEText('Sent from yanjun nas', 'plain', 'utf-8'))

            fullname = filepath + filename
            # 创建MIMEText对象，保存mobi文件
            attach = MIMEText(open(u'%s' % fullname, 'rb').read(), 'base64', 'utf-8')
            # 指定当前文件格式类型
            attach['Content-type'] = 'application/octet-stream'
            # 配置附件显示的文件名称,当点击下载附件时，默认使用的保存文件的名称
            # gb18030 qq邮箱中使用的是gb18030编码，防止出现中文乱码
            attach['Content-Disposition'] = 'attachment;filename="%s"' % filename
            # 把附件添加到msg中
            msg.attach(attach)
            # 设置必要请求头信息
            msg['From'] = FROM
            msg['To'] = mailto
            msg['Subject'] = Header(SUBJECT, 'utf-8')

            # 发送邮件
            smtp_server = smtplib.SMTP()
            smtp_server.connect(HOST)
            smtp_server.starttls()
            smtp_server.login(FROM, PASS)
            smtp_server.sendmail(FROM, mailto, msg.as_string())
            smtp_server.quit()
            success = True
            break
        except Exception as e:
            print(str(e))
            time.sleep(5)
    return success

def start():
    current_timestamp = time.time()
    for key in users.keys():
        user = users.get(key)
        filepath = user.get('dir')
        if not os.path.exists(filepath):
            continue

        history_info = dict()
        history_file = os.path.join(scriptpath, key + '.history')

        if os.path.exists(history_file):
            fh = open(history_file, 'r', encoding='utf8', errors='surrogateescape')
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                items = line.split('\t')
                history_info[items[0]] = {'times': int(items[1]), 'success': True if items[2].lower() == 'true' else False,
                                          'time': items[3]}
            fh.close()

        flist = os.listdir(filepath)
        ischanged = False
        for filename in flist:
            m = hashlib.md5()
            m.update(filename.encode('utf-8', 'surrogateescape'))
            filename_md5 = m.hexdigest()
            path = os.path.join(filepath, filename)
            if os.path.isfile(path) and path.endswith('mobi'):
                fsize = os.path.getsize(path)
                fsize = fsize / float(1024 * 1024)
                if fsize > 20:
                    continue
                # If retry times over the threshold, we will ignore the book
                if filename_md5 in history_info:
                    if history_info[filename_md5]['success']:
                        logger.info('Book already sent. Book=%s' % filename_md5)
                        continue
                    elif not history_info[filename_md5]['success'] and history_info[filename_md5]['times'] >= retry_times:
                        logger.info('Book already sent. Book=%s' % filename_md5)
                        continue
                book_created_time = os.path.getctime(path)
                if current_timestamp - book_created_time < check_interval:
                    dest_file = '%d.mobi' % int(time.time())
                    shutil.copy(path, scriptpath + dest_file)
                    success = send_book(scriptpath, dest_file, user.get('mailto'))
                    # success = True
                    logger.info('Sended book. Book=%s, Success=%s' % (filename_md5, success))
                    if filename_md5 in history_info:
                        history_info[filename_md5]['times'] += 1
                        history_info[filename_md5]['success'] = success
                        history_info[filename_md5]['time'] = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time()))
                    else:
                        history_info[filename_md5] = {'times': 1, 'success': success,
                                                      'time': time.strftime("%Y-%m-%d %H:%M:%S",
                                                                            time.localtime(time.time()))}
                    os.remove(scriptpath + dest_file)
                    ischanged = True

        if ischanged:
            fh = open(history_file, 'w', encoding='utf-8', errors='surrogateescape')
            for k, v in history_info.items():
                fh.write('%s\t%d\t%s\t%s\n' % (k, v['times'], v['success'], v['time']))
            fh.close()


if __name__ == '__main__':
    logger.info('Start')
    start()
    logger.info('End')