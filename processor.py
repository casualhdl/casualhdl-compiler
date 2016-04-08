
from log import (
    log,
    PROCESSOR,
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

from pre_processor import pre_process

dir_lut = {
    'in': 'i',
    'out': 'o',
    'inout': 'io',
}


def zero_extend(value, width):

    v = ''
    for i in range(0, width-len(value)):
        v += '0'
    v = v + value

    return v

def one_extend(value, width):

    v = ''
    for i in range(0, width):
        v += '1'
    v = v + value

    return v

def get_indent(line):
    i = 0
    for c in line:
        if c != ' ':
            break
        i += 1 
    if i % 4 != 0:
        # throw error
        pass
    indent = i / 4
    return indent

def filename_from_component(component):

    name = component['name']
    library = component['library']
    parts = library.split('.')

    filename = os.path.join(parts[0], parts[1], '%s.chdl' % parts[2])

    return filename

def parse_reset_assignment(line, tokens):

    # todo: error checking

    # pre-process line
    line = line.strip()
    line = re.sub(' +', ' ', line)
    #line = ''.join(line.split(':')[:-1])

    # break into parts
    parts = line.split(' = ')
    subject = parts[0]
    value = parts[1] 

    # the subject could be a component port
    if '.' in subject:
        parts = subject.split('.')
        subject = '%s_%s' % (parts[0], parts[1])

    # the value could be a component port
    if '.' in value:
        parts = value.split('.')
        value = '%s_%s' % (parts[0], parts[1])        

    decoded_value = decode_value(value, subject, tokens)

    if not decoded_value:
        decoded_value = value

    return subject, decoded_value

def parse_assignment(line, tokens):

    line = line.strip()
    line = re.sub(' +', ' ', line)
    
    subject = line.split('=')[0].strip()

    log(PROCESSOR, DEBUG, 'assignment: %s' % subject)

    # the subject could be a component port
    if '.' in subject:
        parts = subject.split('.')
        subject = '%s_%s' % (parts[0], parts[1])

    log(PROCESSOR, DEBUG, '\tsubject: %s' % subject)

    _values = line.split('=')[1].strip().split(' ')

    ops = ('-','+', '*', '/')

    vhdl = ''
    for value in _values:
        decoded_value = decode_value(value, subject, tokens)
        
        log(PROCESSOR, DEBUG, '\t\tvalue:         %s' % value)
        log(PROCESSOR, DEBUG, '\t\tdecoded_value: %s' % decoded_value)
        log(PROCESSOR, DEBUG, '\t\t')

        port_signal = get_port_signal_from_name(value, tokens)
        if port_signal:
            _value = port_signal
        else:
            _value = '%s_s' % value

        # math operation
        if value in ops:
            vhdl += '%s ' % value

        # constant
        elif decoded_value:
            vhdl += '%s ' % decoded_value

        # indexed signal
        elif '[' in _value and ']' in _value:
            signal_name = '%s_s' % _value.split('[')[0]
            left = _value.split('[')[1].split(':')[0].strip()
            right = _value.split('[')[1].split(':')[1].strip()
            if '.' in _value.split('[')[0]:
                parts = _value.split('[')[0].split('.')
                signal_name = '%s_%s ' % (parts[0], parts[1])
            vhdl += '%s_s(%s downto %s) ' % (signal_name, left, right)

        # signal
        else:
            log(PROCESSOR, DEBUG, '\t\t\tvalue is signal or port')
            signal_name = _value
            if '.' in value:
                parts = _value.split('.')
                signal_name = '%s_%s ' % (parts[0], parts[1])
            
        
            vhdl += '%s ' % signal_name

    # remove last space, and put semi colon at end of line
    vhdl = '%s_s <= %s;' % (subject, vhdl[:-1])

    log(PROCESSOR, DEBUG, 'assignment: %s' % subject)
    log(PROCESSOR, DEBUG, '\tchdl: %s' % line)
    log(PROCESSOR, DEBUG, '\tvhdl: %s' % vhdl)

    return subject, vhdl

def parse_conditional(cmd, line, tokens):

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

    decoded_value = decode_value(value, subject, tokens)

    # it may not be a constant, may be a signal
    if not decoded_value:
        found = False
        port_signal = get_port_signal_from_name(value, tokens)
        
        # in or inout port?
        if port_signal:
            found = True
            decoded_value = port_signal

        # signal
        else:
            decoded_value = '%s_s' % value

    port_signal = get_port_signal_from_name(subject, tokens)

    subject = '%s_s' % subject
    if port_signal:
        subject = port_signal

    vhdl = '%s ( %s %s %s ) then' % (cmd, subject, op, decoded_value)

    log(PROCESSOR, DEBUG, 'conditional: %s' % subject)
    log(PROCESSOR, DEBUG, '\tchdl: %s' % line)
    log(PROCESSOR, DEBUG, '\tvhdl: %s' % vhdl)

    return subject, vhdl

def get_port_signal_from_name(name, tokens):

    signal_name = None
    for port_signal in tokens['ports']['signals']:
        if port_signal['name'] == name:
            signal_name = '%s_%s' % (name, dir_lut[port_signal['direction']])
            break

    return signal_name

def decode_value(value, name, tokens):

    signal = None
    
    log(PROCESSOR, DEBUG, 'decoding value: %s, name: %s' % (value, name))

    # port?
    for port_signal in tokens['ports']['signals']:
        if port_signal['name'] == name:
            log(PROCESSOR, DEBUG, '\tassignment decoded as port')
            signal = port_signal
            break

    # var?
    if not signal:
        log(PROCESSOR, DEBUG, '\tassignment is not a port')
        for var in tokens['vars']:
            if var['name'] == name:
                log(PROCESSOR, DEBUG, '\tassignment decoded as var')
                signal = var
                break

    if not signal:
        log(PROCESSOR, DEBUG, '\tvalue could not be decoded')
        log(PROCESSOR, DEBUG, '\tvars: %s' % json.dumps(tokens['vars'], indent=4))
        return None

    #if not signal:
    #    signal = get_port_from_name(name, tokens)
    #    if not signal:
    #        # it's possible it's a signal or an input
    #        return None

    if signal['type'] == 'std_logic_vector':
        # get total width of vector
        width = abs(int(signal['left'])) + abs(int(signal['right'])) +  1
        #print('width: %i' % width)

    val = ''
    if signal['type'] == 'std_logic':
        val = "'%s'" % value 
        #raise Exception('logic')
    elif signal['type'] == 'std_logic_vector':

        # binary value
        if value[:2] == '0b':
            # we need to zero extend in the event that it isn't
            # the right widt
            v = bin(int(value))[2:]
            val = value.replace('"','')
            val = '"%s"' % zero_extend(v, width)

        # hex
        elif value[:2] == '0x':

            # todo: truncate or convert to binary if needed due to incorrect width

            val = 'X"%s"' % value.split('0x')[1]
            pass

        # all zeros
        elif value == 'zeros' or value == '0':
            val = '"%s"' % zero_extend('', width)
            #val = '(others => \'0\')';

        # all zeros
        elif value == 'ones':
            val = '"%s"' % one_extend('', width)

        # decimal
        else:

            try:
            #if True:
                v = bin(int(value))[2:]
                val = '"%s"' % zero_extend(v, width)

                #print(value)
                #print(int(value))
                #print(bin(int(value)))
                #print(bin(int(value))[2:])
                #print(val)
                #print(json.dumps(signal, indent=4))

            except Exception as ex:
                val = None
                pass
            
    else:
        # throw error
        pass

    log(PROCESSOR, DEBUG, '\tdecoded value: %s' % val)

    return val

def process_lines(index, indent, procedure_index, tokens):

    log(PROCESSOR, DEBUG, 'processing lines at indent: %i' % indent)

    vhdl = ''
    line_indent = sys.maxsize # big.

    

    i = index
    while(True):

        # get the line we're supposed to be working on
        lines = tokens['procedures'][procedure_index]['lines']
        _line = lines[i]
        line = _line['line']
        line_number = _line['line_number']
        proc_type = tokens['procedures'][procedure_index]['proc_type']


        #log(PROCESSOR, DEBUG, '----------------')
        log(PROCESSOR, DEBUG, 'Line: "%s"' % line)
        #log(PROCESSOR, DEBUG, '%s' % line)
        #log(PROCESSOR, DEBUG, '')
        # process indents
        last_line_indent = line_indent
        line_indent = get_indent(line)

        #log(PROCESSOR, DEBUG, '%i (%i): %s' % (line_number, line_indent, line))

        #if proc_type == 'sync' and i == index and line.strip() != 'reset:':
        #    log(PROCESSOR, INFO, 'missing reset inside of sync procedure')
        #    # todo: throw error
        #    pass

        # reset assignments
        if i == index and line.strip() == 'reset:':
            
            log(PROCESSOR, INFO, 'parsing process reset assignments')

            # inc line counter to get to first assignment
            
            reset_line_index = -1
            while(True):

                # go to next line
                i += 1

                _line = lines[i]
                line = _line['line']
                line_number = _line['line_number']
                reset_line_indent = get_indent(line)

                subject, value = parse_reset_assignment(line, tokens)

                #decoded_value = get_port_signal_from_name(subject, tokens)
                #if not decoded_value:
                #    decoded_value = decode_value(value, subject, tokens)

                tokens['procedures'][procedure_index]['reset']['assignments'].append({
                    'vhdl': '%s_s <= %s' % (subject, value),
                })

                if i+1 == len(lines):
                    # todo: throw error
                    pass

                next_indent = get_indent(lines[i+1]['line'])

                if next_indent == 0 or next_indent < reset_line_indent:
                    break;

            log(PROCESSOR, DEBUG, 'done with reset assignments')

        # blank
        elif line.strip() == '':
            pass

        # if control structure
        elif '    if ' in line:

            log(PROCESSOR, INFO, '"if" control structure found')

            subject, _vhdl = parse_conditional('if', line, tokens)

            tokens['procedures'][procedure_index]['lines'][i]['vhdl'] = {
                'command': 'if',
                'indent': line_indent,
                'is_control_structure': True,
                'vhdl': _vhdl,
            }

            i, tokens = process_lines(i+1, line_indent+1, procedure_index, tokens)

            # insert a bogus end if so we can track it later on
            tokens['procedures'][procedure_index]['lines'].insert(i+1, {
                'line_number': -1,
                'line': '',
                'vhdl': {
                    'command': 'endif',
                    'indent': line_indent,
                    'is_control_structure': True,
                    'vhdl': 'end if;'
                }
            })

            i += 1 

        # elif control structure
        elif '    elsif ' in line:

            log(PROCESSOR, INFO, '"elsif" control structure found')

            subject, _vhdl = parse_conditional('elsif', line, tokens)

            tokens['procedures'][procedure_index]['lines'][i]['vhdl'] = {
                'command': 'elsif',
                'indent': line_indent,
                'is_control_structure': True,
                'vhdl': _vhdl,
            }

            i, tokens = process_lines(i+1, line_indent+1, procedure_index, tokens)

            # insert a bogus end if so we can track it later on
            tokens['procedures'][procedure_index]['lines'].insert(i+1, {
                'line_number': -1,
                'line': '',
                'vhdl': {
                    'command': 'endif',
                    'indent': line_indent,
                    'is_control_structure': True,
                    'vhdl': 'end if;'
                }
            })

            i += 1 

        # else control structure
        elif '    else:' in line:

            log(PROCESSOR, INFO, '"else" control structure found')

            _vhdl = 'else'

            tokens['procedures'][procedure_index]['lines'][i]['vhdl'] = {
                'command': 'else',
                'indent': line_indent,
                'is_control_structure': True,
                'vhdl': _vhdl,
            }

            i, tokens = process_lines(i+1, line_indent+1, procedure_index, tokens)

            # insert a bogus end if so we can track it later on
            tokens['procedures'][procedure_index]['lines'].insert(i+1, {
                'line_number': -1,
                'line': '',
                'vhdl': {
                    'command': 'endif',
                    'indent': line_indent,
                    'is_control_structure': True,
                    'vhdl': 'end if;'
                }
            })

            i += 1 

        # case control structure
        elif '    case ' in line:
            log(PROCESSOR, INFO, '"case" control structure found')
            pass

        # fsm control structure
        elif '    fsm ' in line:
            log(PROCESSOR, INFO, '"fsm" control structure found')
            pass

        # assignment
        elif len(line.split(' = ')) != 1:

            log(PROCESSOR, INFO, 'assignment found')

            subject, _vhdl = parse_assignment(line, tokens)

            tokens['procedures'][procedure_index]['lines'][i]['vhdl'] = {
                'command': 'assignment',
                'indent': line_indent,
                'is_control_structure': False,
                'vhdl': _vhdl,
            }

            # check if this is a default assignment
            if line_indent == 1:

                # it's a default assignment.  we'll save that to the list
                # of defined defaults so the compiler knows not to generate
                # a derived default

                tokens['procedures'][procedure_index]['defaults']['defined'].append({
                    'name': subject,
                    'vhdl': _vhdl,
                })

            else:

                # this is not a default assignment.  we need to add a default to 
                # our derived list.  the compiler will choose to use it or not.

                # default to its self so a register is born
                _vhdl = '%s_s <= %s_s;' % (subject, subject)

                tokens['procedures'][procedure_index]['defaults']['derived'].append({
                    'name': subject,
                    'vhdl': _vhdl,
                })

        # +1
        elif '++' in line:

            log(PROCESSOR, INFO, 'increment found.')

            name = '%s' % line.strip().split('++')[0]         
            
            tokens['procedures'][procedure_index]['lines'][i]['vhdl'] = {
                'command': 'increment',
                'indent': line_indent,
                'is_control_structure': False,
                'vhdl': '%s_s <= %s_s + \'1\';' % (name, name),
            }

        # -1
        elif '--' in line:

            log(PROCESSOR, INFO, 'increment found.')

            name = '%s' % line.strip().split('++')[0]         
            
            tokens['procedures'][procedure_index]['lines'][i]['vhdl'] = {
                'command': 'decrement',
                'indent': line_indent,
                'is_control_structure': False,
                'vhdl': '%s_s <= %s_s - \'1\';' % (name, name),
            }

        if i+1 == len(lines):
            # at end of file
            break
            
        if lines[i+1]['line'].strip() != '':
            next_indent = get_indent(lines[i+1]['line'])

            # check for end of file, or unindent
            if next_indent == 0 or next_indent < line_indent:
                #log(PROCESSOR, DEBUG, 'done with processing lines at indent: %i' % line_indent)
                break;

        i += 1

    log(PROCESSOR, DEBUG, 'done with processing lines at indent: %i' % line_indent)

    return i, tokens

def process_procedures(tokens):

    for i in range(0, len(tokens['procedures'])):

        name = tokens['procedures'][i]['name']
        proc_type = tokens['procedures'][i]['proc_type']

        log(PROCESSOR, INFO, 'processing procedure "%s"' % name)
        
        if proc_type == 'async':
            _i, tokens = process_lines(0, 1, i, tokens)
        elif proc_type == 'sync':
            _i, tokens = process_lines(0, 1, i, tokens)

        log(PROCESSOR, INFO, 'done processing procedure "%s"' % name)

    return tokens

def process_assignments(tokens):

    for i in range(0, len(tokens['vars'])):
        name = tokens['vars'][i]['name']
        port_name = tokens['vars'][i]['output_register']
        if port_name:
            log(PROCESSOR, INFO, 'output register found in vars list: "%s"' % port_name)
            for port_signal in tokens['ports']['signals']:
                if port_signal['name'] == port_name:
                    tokens['assignments'].append({
                        'name': name,
                        'port': port_name,
                        'vhdl': '%s_%s <= %s_s;' % (port_name, dir_lut[port_signal['direction']], name)
                    })

    return tokens

def process_vars(tokens):

    #tokens = pre_process_ports(tokens)
    
    for i in range(0, len(tokens['vars'])):
        name = tokens['vars'][i]['name']
        type_ = tokens['vars'][i]['type']
        left = tokens['vars'][i]['left']
        right = tokens['vars'][i]['right']
        if type_ == 'std_logic':
            tokens['vars'][i]['vhdl'] = '%s_s : std_logic;' % name
        elif type_ == 'std_logic_vector':
            tokens['vars'][i]['vhdl'] = "%s_s : std_logic_vector(%s downto %s);" % (name, left, right)
        else:
            # todo: throw error
            pass

    return tokens

def process_components(tokens, lib_dirs):

    '''
    casualhdl will go and process all of the components that are used in
    the file.
    '''   

    components = []

    for i in range(0, len(tokens['components'])):
        component = tokens['components'][i]
        filename = filename_from_component(component)

        for lib_dir in lib_dirs:
            full_filename = '%s/%s' % (lib_dir, filename)
            if os.path.isfile(full_filename):

                _tokens = process(full_filename)       

                components.append({
                    'name': component['name'],
                    'entity': _tokens['entity'],
                    'library': _tokens['library'],
                    'ports': _tokens['ports'],
                })

                tokens['components'][i]['ports'] = _tokens['ports']


    for component in components:

        #
        # todo: support multiple resets and clocks
        #

        for signal in component['ports']['signals']:
            #signal_name = '_'.join(signal['name'].split('_')[:-1])
            tokens['vars'].append({
                'name': '%s_%s' % (component['name'], signal['name']),
                'type': signal['type'], 
                'left': signal['left'],
                'right': signal['right'],
                'output_register': None, 
                'vhdl': '',
            })

    #print(json.dumps(components, indent=4))

    #print(json.dumps(tokens, indent=4))

    #if len(components) != 0:
    #    raise Exception('debug')

    return tokens

def process(filename):

    start = time.time()

    log(PROCESSOR, INFO, 'processor starting.  working on file: "%s"' % filename)

    lib_dirs = [
        './lib',
    ]

    tokens = pre_process(filename)

    tokens = process_components(tokens, lib_dirs)

    tokens = process_vars(tokens)

    tokens = process_procedures(tokens)

    tokens = process_assignments(tokens)

    end = time.time()

    log(PROCESSOR, INFO, 'processing finished in %.6f seconds' % (end-start) )

    #log(PROCESSOR, DEBUG, 'tokens:\n%s'  % json.dumps(tokens, indent=4))

    return tokens

if __name__ == '__main__':

    filename = sys.argv[1]    

    tokens = process(filename)

    print(json.dumps(tokens, indent=4))