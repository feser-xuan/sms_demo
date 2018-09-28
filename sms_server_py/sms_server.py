#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os,sys,ConfigParser,logging,datetime,logging.handlers,json,thread,struct,Queue
from bottle import route, run, template, static_file, error, get, post, request, redirect, response,ResourceManager,install
from functools import wraps
from serial import *
from smspdu import SMS_SUBMIT

reload(sys)
sys.setdefaultencoding('utf-8')

app_path = sys.path[0]+os.path.sep
os.chdir(app_path)

config = ConfigParser.ConfigParser()
config.read('conf/config.ini')
port = config.get('web', 'port')
serial_port = config.get('web', 'serial_port')
baud_rate = config.getint('web', 'baud_rate')

all_msg = Queue.Queue()

def create_log():
    logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)-20s | %(levelname)-8s | %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')
    logger = logging.getLogger("")
    console = logging.StreamHandler()
    console.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)-20s | %(levelname)-8s | %(message)s')
    formatter.datefmt='%Y-%m-%d %H:%M:%S'
    console.setFormatter(formatter)
    fileHandler = logging.handlers.TimedRotatingFileHandler('logs/run.log','D',1,30)
    #fileHandler.suffix="%Y-%m-%d %H.%M"
    fileHandler.setFormatter(formatter)
    logger.addHandler(fileHandler)
    return logger

log = create_log()

def get_serial():
    log.info('open serial:%s@%s'%(serial_port,baud_rate))
    ser = Serial(
    port=serial_port,              # number of device, numbering starts at
    # zero. if everything fails, the user
    # can specify a device string, note
    # that this isn't portable anymore
    # if no port is specified an unconfigured
    # an closed serial port object is created
    baudrate=baud_rate,          # baud rate
    bytesize=EIGHTBITS,     # number of databits
    parity=PARITY_NONE,     # enable parity checking
    stopbits=STOPBITS_ONE,  # number of stopbits
    timeout=2000,              # set a timeout value, None for waiting forever
    xonxoff=0,              # enable software flow control
    rtscts=0,               # enable RTS/CTS flow control
    interCharTimeout=None   # Inter-character timeout, None to disable
    )
    return ser

sms_port = get_serial()

def log_to_logger(fn):
    '''
    Wrap a Bottle request so that a log line is emitted after it's handled.
    (This decorator can be extended to take the desired logger as a param.)
    '''
    @wraps(fn)
    def _log_to_logger(*args, **kwargs):
        request_time = datetime.datetime.now()
        actual_response = fn(*args, **kwargs)
        # modify this to log exactly what you need:
        log.info('%s %s %s %s' % (request.remote_addr,
                                        request.method,
                                        request.url,
                                        response.status))
        return actual_response
    return _log_to_logger

def send_serial(content):
    # log.info('Serial > %s'%content)
    # sms_port.write(content)
    all_msg.put(content)

    # n = sms_port.inWaiting()
    # time.sleep(1)
    # lines = sms_port.readline()
    # log.info('Serial < %s'%lines)
    #for line in lines:
    #    log.info('Serial < %s'%(line))

def read_serial():
   while True:
        try:
            data = sms_port.readline()
            if len(data)>0:
                log.info("Serial <<== %s"%(data.strip()))
        except:
            log.exception('------ exception ------')

def create_pdu(header,phone,content):
    phone = bi_revert_sting(phone)
    tpdu = []
    pdu = SMS_SUBMIT.create('', phone, content)
    tpdu.append(header)
    tpdu.append(phone)
    tpdu.append('0008A7')
    #短信内容长度接短信内容unicode编码
    length = pdu.tp_udl
    tpdu.append('%02X' %length)
    tpdu.append(''.join(['%02X' % ord(c) for c in pdu.tp_ud]))
    data = ''.join(tpdu)
    return (length,data)

def create_empty_pdu(header,phone,tail):
    phone = bi_revert_sting(phone)
    tpdu = []
    pdu = SMS_SUBMIT.create('', phone, '')
    tpdu.append(header)
    tpdu.append(phone)
    tpdu.append(tail)
    #短信内容长度接短信内容unicode编码
    length = pdu.tp_udl
    tpdu.append('%02X' %length)
    tpdu.append(''.join(['%02X' % ord(c) for c in pdu.tp_ud]))
    data = ''.join(tpdu)
    return (length,data)

def th_process_msg():
    while True:
        try:
            msg = all_msg.get()
            log.info('Serial ==>> %s'%msg.strip())
            sms_port.write(msg)
            all_msg.task_done()
        except:
            log.exception('--------- exception ---------')

def send_sms(phone,content):
    send_serial('AT+CSCS="UCS2"\r')
    time.sleep(0.5)
    send_serial('AT+CMGF=0\r')
    time.sleep(0.5)
    (length,data) = create_pdu('0031000B81',phone,content)
    send_serial('AT+CMGS=%s\r'%((len(data)/2-1)))
    time.sleep(0.5)
    send_serial(data+struct.pack('>B',26))

def send_sms_ack(phone,content):
    send_serial('AT+CNMI=2,1,0,2,1\r')
    time.sleep(0.5)
    send_serial('AT+CMGF=0\r')
    time.sleep(0.5)
    (length,data) = create_pdu('00B1000B81',phone,content)
    send_serial('AT+CMGS=%s\r'%((len(data)/2-1)))
    time.sleep(0.5)
    send_serial(data+struct.pack('>B',26))

def send_empty_sms(phone):
    send_serial('AT+CNMI=2,1,0,2,1\r')
    time.sleep(0.5)
    (length,data) = create_empty_pdu('B1000B81',phone,'40C0')
    send_serial('AT+CMGS=%s\r'%((len(data)/2)))
    time.sleep(0.5)
    send_serial(data+struct.pack('>B',26))

@post('/send_sms')
@get('/send_sms')
def do_send_sms():
    try:
        phone = request.params['phone']
        content = request.params['content'].decode('utf-8')
        log.info('send sms phone:%s,content:%s'%(phone,content))
        send_sms(phone,content)
        return json.dumps({'result':True})
    except:
        log.exception('---------exception--------------')
        return json.dumps({'result':False,'msg':'exception'})
    return json.dumps({'result':False,'msg':'unknow error'})

@post('/send_sms_ack')
@get('/send_sms_ack')
def do_send_sms_ack():
    try:
        phone = request.params['phone']
        content = request.params['content'].decode('utf-8')
        log.info('send sms phone:%s,content:%s'%(phone,content))
        send_sms_ack(phone,content)
        return json.dumps({'result':True})
    except:
        log.exception('---------exception--------------')
        return json.dumps({'result':False,'msg':'exception'})
    return json.dumps({'result':False,'msg':'unknow error'})

@post('/cmd')
@get('/cmd')
def do_send_cmd():
    try:
        content = request.params['cmd'].decode('utf-8')
        log.info('send sms cmd content:%s'%(content))
        send_serial('%s\r'%content.encode('utf-8'))
        return json.dumps({'result':True})
    except:
        log.exception('---------exception--------------')
        return json.dumps({'result':False,'msg':'exception'})
    return json.dumps({'result':False,'msg':'unknow error'})

@post('/send_empty_sms')
@get('/send_empty_sms')
def do_send_empty_sms():
    try:
        phone = request.params['phone']
        log.info('send empty sms phone:%s'%(phone))
        send_empty_sms(phone)
        return json.dumps({'result':True})
    except:
        log.exception('---------exception--------------')
        return json.dumps({'result':False,'msg':'exception'})
    return json.dumps({'result':False,'msg':'unknow error'})

def bi_revert_sting(s):
    x,y = s[::2],s[1:][::2]
    ret = ''
    z = min(len(x),len(y))
    for i in range (z):
        ret += y[i]
        ret += x[i]
    if len(x)>len(y):
        ret += 'F'
        ret += x[-1]
    return ret

thread.start_new_thread(read_serial,())
thread.start_new_thread(th_process_msg,())
install(log_to_logger)
run(host='0.0.0.0', port=port, debug=False, reloader=False,server='paste')
