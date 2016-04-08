
from log import (
    log,
    PRE_PROCESSOR,
    INFO,
    ERROR,
    WARNING,
    DEBUG,
)

import os
import json
import re
import sys
import time

from tokenizer import tokenize

def is_port(name, tokens):

    retval = False
    for port_signal in tokens['ports']['signals']:
        if name == port_signal['name']:
            retval = True
            break

    return retval

def is_signal(name, tokens):

    retval = False
    for signal in tokens['vars']:
        if name == signal['name']:
            retval = True
            break

    return retval    

def parse_conditional(line):

    # todo: error checking

    # pre-process line
    line = line.strip()
    line = re.sub(' +', ' ', line)
    line = ''.join(line.split(':')[:-1])
        
    # break into parts
    parts = line.split(' ')
    subject = parts[1]
    value = parts[3]
    op = parts[2]    

    # the subject could be a component port
    if '.' in subject:
        parts = subject.split('.')
        subject = '%s_%s' % (parts[0], parts[1])

    # the value could be a component port
    if '.' in value:
        parts = value.split('.')
        value = '%s_%s' % (parts[0], parts[1])        

    return subject, value

def parse_assignment(line):

    line = line.strip()
    line = re.sub(' +', ' ', line)
    
    subject = line.split('=')[0].strip()
    _values = line.split('=')[1].strip().split(' ')

    ops = ('-','+')

    # need to throw out ops, and clean up values to only be 
    # signals and ports
    values = []
    for value in _values:
        if value[0] != '0' and not value in ops:
            signal_name = value.split('[')[0]
            if '.' in signal_name:
                parts = signal_name.split('.')
                signal_name = '%s_%s' % (parts[0], parts[1])
            values.append(signal_name)

    return subject, values

def update_port_direction(name, direction, tokens):

    found = False
    for i in range(0, len(tokens['ports']['signals'])):
        if name == tokens['ports']['signals'][i]['name']:
            found = True
            if tokens['ports']['signals'][i]['direction'] != None and ( \
                    (tokens['ports']['signals'][i]['direction'] == 'in' and \
                    direction == 'out') or \
                    (   tokens['ports']['signals'][i]['direction'] == 'out' and \
                    direction == 'in') ):

                # we've already set our direction to "in" or "out", and we're 
                # trying to set it to the oposite.
                tokens['ports']['signals'][i]['direction'] = 'inout'

            else:

                # there is no direction set, or we've already set it to what
                # we're trying to set it to.
                tokens['ports']['signals'][i]['direction'] = direction

            break

    if not found:
        # todo: throw error
        pass

    return tokens

def port_from_name(name, tokens):

    signal = None
    for port_signal in tokens['ports']['signals']:
        if port_signal['name'] == name:
            signal = port_signal
    return signal

def add_output_signal(name, tokens):

    signal = port_from_name(name, tokens)

    if not signal:
        # value is not a port
        return tokens

    for var in tokens['vars']:
        if var['name'] == signal['name']:
            return tokens

    tokens['vars'].append({
        'name': signal['name'],
        'type': signal['type'],
        'left': signal['left'],
        'right': signal['right'],
        'output_register': signal['name'],
    })

    return tokens

def pre_process_ports(tokens):

    for procedures in tokens['procedures']:
        for i in range(0, len(procedures['lines'])):

            line = procedures['lines'][i]['line']
            line_number = procedures['lines'][i]['line_number']

            # only a subject and a value are allowed in conditionals
            if '    if ' in line or '    elsif ' in line:
                log(PRE_PROCESSOR, DEBUG, 'found conditional: "%s"' % line)
                subject, value = parse_conditional(line)
                log(PRE_PROCESSOR, DEBUG, '\t: subject: "%s", value: "%s"' % (subject, value))
                if is_port(subject, tokens):
                    # update the port as an input ( left side of conditional )
                    tokens = update_port_direction(subject, 'in', tokens)
                elif is_port(value, tokens):
                    # update the port as an output ( right side of conditional )
                    tokens = update_port_direction(value, 'in', tokens)
                    #tokens = add_output_signal(subject, tokens)

            elif ' = ' in line:
                log(PRE_PROCESSOR, DEBUG, 'found assignment: "%s"' % line)
                subject, values = parse_assignment(line)
                log(PRE_PROCESSOR, DEBUG, '\t: subject: "%s", values: "%s"' % (subject, ', '.join(values)))
                if is_port(subject, tokens):
                    # update the port as an output ( left side of conditional )
                    tokens = update_port_direction(subject, 'out', tokens)
                    tokens = add_output_signal(subject, tokens)
                for value in values:
                    if is_port(value, tokens):
                        # update the port as an output ( right side of conditional)
                        tokens = update_port_direction(value, 'in', tokens)

    return tokens

def pre_process(filename):

    start = time.time()

    # get the tokenized verion of the file
    tokens = tokenize(filename)

    tokens = pre_process_ports(tokens)

    end = time.time()

    #log(PRE_PROCESSOR, INFO, 'processing finished in %.6f seconds' % (end-start) )

    return tokens

if __name__ == '__main__':

    filename = sys.argv[1]    

    tokens = pre_process(filename)

    print(json.dumps(tokens, indent=4))

