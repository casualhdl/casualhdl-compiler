
import datetime

NONE = 0
INFO = 1
ERROR = 2
WARNING = 4
DEBUG = 8

TOKENIZER    = 'tokenizer    '
PRE_PROCESSOR = 'pre-processor'
PROCESSOR    = 'processor    '
COMPILER     = 'compiler     '


def log_lut(level):
    lut = {
    	INFO:    'INFO   ',
       	ERROR:   'ERROR  ',
        WARNING: 'WARNING',
        DEBUG:   'DEBUG  ',
    }
    return lut[level]

def log(source, level, text):

    #if level < DEBUG:
        print('[ %s ][ %s ] %s: %s' % (datetime.datetime.now(), source, log_lut(level), text))
