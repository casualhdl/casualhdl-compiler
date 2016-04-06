
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

from tokenizer import tokenize

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

def decode_value(value, name, tokens):


    signal = get_var_from_name(name, tokens)
    if not signal:
        signal = get_port_from_name(name, tokens)
        if not signal:
            # it's possible it's a signal or an input
            return None

    if signal['type'] == 'std_logic_vector':
        # get total width of vector
        width = abs(int(signal['left'])) + abs(int(signal['right'])) +  1
        #print('width: %i' % width)

    val = ''
    if signal['type'] == 'std_logic':
        val = "'%s'" % value 
        #raise Exception('bit')
    elif signal['type'] == 'std_logic_vector':

        # binary value
        if '"' in value:
            # we need to zero extend in the event that it isn't
            # the right widt
            val = value.replace('"','')
            val = '"%s"' % zero_extend(v, width)

        # hex
        elif '0x' in value:

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

                v = bin(int(value))[2:]
                val = '"%s"' % zero_extend(v, width)

                #print(value)
                #print(int(value))
                #print(bin(int(value)))
                #print(bin(int(value))[2:])
                #print(val)
                #print(json.dumps(signal, indent=4))

            except:
                val = None
                pass
            
    else:
        # throw error
        pass

    return val

def parse_conditional(line):

    # todo: error checking

    # pre-process line
    line = line.strip()
    line = re.sub(' +', ' ', line)
    line = ''.join(line.split(':')[:-1])
    
    # break into parts
    parts = line.split(' ')

    subject = parts[1]
    operation = parts[2]
    value = parts[3]

    if '.' in subject:
        parts = subject.split('.')
        subject = '%s_%s' % (parts[0], parts[1])

    return subject, operation, value

def parse_assignment(line, tokens):

    # todo: error checking

    # pre-process line
    line = line.strip()
    line = re.sub(' +', ' ', line)

    # break into parts
    parts = line.split(' = ')

    subject = parts[0]
    value = parts[1]

    print('start:')
    print(subject, value)

    tokens = update_port_direction(subject, 'out', tokens)

    # the value may be a math operation and have multiple parts.
    ops = ('+', '-', '*', '/')
    if any( op in value for op in ops ):

        print('math!')

        # each of the parts needs to be decoded
        things = value.split(' ')
        print('things:', things)
        _value = ''
        for thing in things:

            print('thing:', thing)
            #print(thing)
            print('get_port_from_name', get_port_from_name('%s_i' % thing, tokens))

            # math operator
            if any( op == thing for op in ops ):
                _value += '%s ' % thing
            
                print(_value)                

            #
            # todo: need to figure out how to handle _i vs _io, because we don't know
            #       the direction of the ports yet ..
            #

            # port (i or io)
            elif not thing.isdigit() and ( get_port_from_name('%s' % thing, tokens) or get_port_from_name('%s_i' % thing, tokens) ):
                print('port thing:', thing)
                
                _value += '%s_i ' % thing

                print(_value)

                tokens = update_port_direction(thing, 'in', tokens)

                #print(json.dumps(tokens, indent=4))

                #raise Exception('debug')

            #elif not thing.isdigit() and get_port_from_name('%s_io' % thing, tokens):
            #    _value += '%s_io ' % thing
            
            # var
            elif not thing.isdigit() and ( get_var_from_name('%s' % thing, tokens) or get_var_from_name('%s_s' % thing, tokens) ):
                
                print('var thing:', thing)

                _value += '%s_s ' % thing

                print(_value)
            
            # a constant
            else:

                print('else thing:', thing)

                name = decode_value(thing, subject, tokens)
                name_s = decode_value(thing, '%s_s' % subject, tokens)

                _value += '%s ' % name if name != None else name_s

                print(_value)

        #print(_value)

        value = _value.strip()

    else:
    
        # test to see if this is an assignment to a internal or port signal
        # or if it is going to a component
        if '.' in subject:
            parts = subject.split('.')
            subject = '%s_%s' % (parts[0], parts[1])

    print('final:')
    print(subject, value)

    #raise Exception('debug')

    return subject, value, tokens

def get_type_from_name(name, tokens):

    found = False
    assignment_type = None
    for _signal in tokens['ports']['signals']:
        if name == _signal['name']:
            assignment_type = 'port'
            found = True
            break
        
    if not found:
        for _signal in tokens['vars']:
            if name == _signal['name']:
                assignment_type = 'var'
                found = True
                break

    return assignment_type

def get_var_from_name(name, tokens):

    found = False
    signal = None
    for _signal in tokens['vars']:
        if name == _signal['name']:
            signal = _signal
            found = True
            break

    if not found:
        # todo: throw error
        pass

    return signal

def get_port_from_name(name, tokens):

    found = False
    signal = None
    for _signal in tokens['ports']['signals']:
        #print(_signal['name'], name)
        if name == _signal['name']:
            signal = _signal
            found = True
            break

    if not found:
        # todo: throw error
        pass

    return signal

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

                # we've already set our direction to `in` or `out`, and we're 
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

def filename_from_component(component):

    name = component['name']
    library = component['library']
    parts = library.split('.')

    filename = os.path.join(parts[0], parts[1], '%s.chdl' % parts[2])

    return filename

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
        '''
        for clock in component['ports']['clocks']:
            clock_name = '_'.join(clock['name'].split('_')[:-1])
            tokens['vars'].append({
                'name': '%s_%s_s' % (component['name'], clock_name),
                'type': 'std_logic', 
                'left': None,
                'right': None,
                'output_register': None, 
                'vhdl': '',
            })
        for reset in component['ports']['resets']:
            reset_name = '_'.join(reset['name'].split('_')[:-1])
            tokens['vars'].append({
                'name': '%s_%s_s' % (component['name'], reset_name),
                'type': 'std_logic', 
                'left': None,
                'right': None,
                'output_register': None, 
                'vhdl': '',
            })
        '''
        for signal in component['ports']['signals']:
            signal_name = '_'.join(signal['name'].split('_')[:-1])
            tokens['vars'].append({
                'name': '%s_%s_s' % (component['name'], signal_name),
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

def pre_process_ports(tokens):

    '''
    Do a first pass through all of the lines of each of the procedures to 
    figure out what direction each port needs to be.
    '''

    for procedure in tokens['procedures']:
        for _line in procedure['lines']:

            # pull apart the line
            line_number = _line['line_number']
            line = _line['line']

            # the line is a control structure with a condition
            if '    if ' in line or '    elsif ' in line:

                # parse the line
                subject, operation, value = parse_conditional(line)

                # check to see if the subject is a port ( in )
                if get_type_from_name(subject, tokens) == 'port':
                    tokens = update_port_direction(subject, 'in', tokens)

                # check to see if the value is a port ( in )
                if get_type_from_name(value, tokens) == 'port':
                    tokens = update_port_direction(value, 'in', tokens)                


            # the line is a case control structure
            elif '    case ' in line:
                
                # todo: parse case line

                pass

            # there is an assignment
            elif ' = ' in line:

                # parse the line
                subject, value, tokens = parse_assignment(line, tokens)

                # check to see if the subject is a port ( out )
                if get_type_from_name(subject, tokens) == 'port':
                    tokens = update_port_direction(subject, 'out', tokens)

                # check to see if the value is a port ( in )
                if get_type_from_name(value, tokens) == 'port':
                    tokens = update_port_direction(value, 'in', tokens)

            # the line does not involve a port
            else:
                # nothing to do
                pass

    # now that we have the directions, we can update the names of the ports to reflect
    # the names they'll have in VHDL.
    #
    # additionally, all outputs will get a registering signal for later assignments

    dir_lut = {
        'in': 'i',
        'out': 'o',
        'inout': 'io',
    }

    #print(json.dumps(tokens, indent=4))

    for i in range(0, len(tokens['ports']['signals'])):
        name = tokens['ports']['signals'][i]['name']
        direction = tokens['ports']['signals'][i]['direction']
        type_ = tokens['ports']['signals'][i]['type']
        left = tokens['ports']['signals'][i]['left']
        right = tokens['ports']['signals'][i]['right']
        tokens['ports']['signals'][i]['name'] = '%s_%s' % (name, dir_lut[direction])

        if direction == 'out':
            tokens['vars'].append({
                'name': '%s_s' % name,
                'type': type_,
                'left': left,
                'right': right,
                'output_register': '%s_o' % name,
            })

    return tokens

def process_ports(tokens):

    tokens = pre_process_ports(tokens)
    
    for i in range(0, len(tokens['ports']['clocks'])):
        tokens['ports']['clocks'][i]['vhdl'] = '%s : in std_logic;' % tokens['ports']['clocks'][i]['name']
        
    for i in range(0, len(tokens['ports']['resets'])):
        tokens['ports']['resets'][i]['vhdl'] = '%s : in std_logic;' % tokens['ports']['resets'][i]['name']

    for i in range(0, len(tokens['ports']['signals'])):
        name = tokens['ports']['signals'][i]['name']
        type_ = tokens['ports']['signals'][i]['type']
        direction = tokens['ports']['signals'][i]['direction']
        left = tokens['ports']['signals'][i]['left']
        right = tokens['ports']['signals'][i]['right']
        if type_ == 'std_logic':
            tokens['ports']['signals'][i]['vhdl'] = '%s : %s std_logic;' % (name, direction)
        elif type_ == 'std_logic_vector':
            tokens['ports']['signals'][i]['vhdl'] = "%s : %s std_logic_vector(%s downto %s);" % (name, direction, left, right)
        else:
            # todo: throw error
            pass

    return tokens

def process_vars(tokens):

    #tokens = pre_process_ports(tokens)
    
    for i in range(0, len(tokens['vars'])):
        name = tokens['vars'][i]['name']
        type_ = tokens['vars'][i]['type']
        left = tokens['vars'][i]['left']
        right = tokens['vars'][i]['right']
        if type_ == 'std_logic':
            tokens['vars'][i]['vhdl'] = '%s : std_logic;' % name
        elif type_ == 'std_logic_vector':
            tokens['vars'][i]['vhdl'] = "%s : std_logic_vector(%s downto %s);" % (name, left, right)
        else:
            # todo: throw error
            pass

    return tokens

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
        log(PROCESSOR, DEBUG, 'Line: `%s`' % line)
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

                subject, value, tokens = parse_assignment(line, tokens)

                # we can only ever assign a value to a signal, so we can make this
                # assumption here.
                name = '%s_s' % subject

                # the value could be a hard coded value, or it could be a signal or port
                if get_port_from_name('%s_i' % value, tokens):
                    decoded_value = '%s_i' % value
                elif get_port_from_name('%s_io' % value, tokens):
                    decoded_value = '%s_io' % value
                elif get_var_from_name('%s_s' % value, tokens):
                    decoded_value = '%s_s' % value
                else:
                    # it's a hard value, not a signal or port
                    decoded_value = decode_value(value, name, tokens)

                tokens['procedures'][procedure_index]['reset']['assignments'].append({
                    'vhdl': '%s_s <= %s' % (subject, decoded_value),
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

            log(PROCESSOR, INFO, '`if` control structure found')

            # todo: handle just the name of the signal for true/false

            # parse the line
            subject, operation, value = parse_conditional(line)

            # this could be a signal or an `in` or `inout` port.  we'll test if it's an input
            # port first
            if get_port_from_name('%s_i' % subject, tokens):
                name = '%s_i' % subject
            elif get_port_from_name('%s_io' % subject, tokens):
                name = '%s_io' % subject
            else:
                # it's a signal, not a port
                name = '%s_s' % subject

            # the value could be a hard coded value, or it could be a signal or port
            if get_port_from_name('%s_i' % value, tokens):
                decoded_value = '%s_i' % value
            elif get_port_from_name('%s_io' % value, tokens):
                decoded_value = '%s_io' % value
            elif get_var_from_name('%s_s' % value, tokens):
                decoded_value = '%s_s' % value
            else:
                # it's a hard value, not a signal or port
                decoded_value = decode_value(value, name, tokens)

            _vhdl = 'if ( %s %s %s ) then' % (name, operation, decoded_value)

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
                    'vhdl': 'end if;' # -- %s' % _vhdl,
                }
            })

            i += 1 

        # elif control structure
        elif '    elsif ' in line:

            log(PROCESSOR, INFO, '`elsif` control structure found')

            # parse the line
            subject, operation, value = parse_conditional(line)

            # this could be a signal or an `in` or `inout` port.  we'll test if it's an input
            # port first
            if get_port_from_name('%s_i' % subject, tokens):
                name = '%s_i' % subject
            elif get_port_from_name('%s_io' % subject, tokens):
                name = '%s_io' % subject
            else:
                # it's a signal, not a port
                name = '%s_s' % subject

            # the value could be a hard coded value, or it could be a signal or port
            if get_port_from_name('%s_i' % value, tokens):
                decoded_value = '%s_i' % value
            elif get_port_from_name('%s_io' % value, tokens):
                decoded_value = '%s_io' % value
            elif get_var_from_name('%s_s' % value, tokens):
                decoded_value = '%s_s' % value
            else:
                # it's a hard value, not a signal or port
                decoded_value = decode_value(value, name, tokens)

            _vhdl = 'elsif ( %s %s %s ) then' % (name, operation, decoded_value)

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
                    'vhdl': 'end if;', # -- %s' % _vhdl,
                }
            })

            i += 1 

        # else control structure
        elif '    else:' in line:

            log(PROCESSOR, INFO, '`else` control structure found')

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
                    'vhdl': 'end if;' # -- %s' % _vhdl,
                }
            })

            i += 1 

        # case control structure
        elif '    case ' in line:
            log(PROCESSOR, INFO, '`case` control structure found')
            pass

        # fsm control structure
        elif '    fsm ' in line:
            log(PROCESSOR, INFO, '`fsm` control structure found')
            pass

        # assignment
        elif len(line.split('=')) != 1:

            log(PROCESSOR, INFO, 'assignment found')

            subject, value, tokens = parse_assignment(line, tokens)

            # we can only ever assign a value to a signal, so we can make this
            # assumption here.
            name = '%s_s' % subject

            decoded_value = decode_value(value, name, tokens)

            # the value could be a hard coded value, or it could be a signal or port
            if get_port_from_name('%s_i' % value, tokens):
                decoded_value = '%s_i' % value
            elif get_port_from_name('%s_io' % value, tokens):
                decoded_value = '%s_io' % value
            elif get_var_from_name('%s_s' % value, tokens):
                decoded_value = '%s_s' % value
            else:
                if decoded_value != None:
                    # it's a hard value, not a signal or port
                    #decoded_value = decode_value(value, name, tokens)
                    pass
                else:
                    # has math in it
                    decoded_value = value
            _vhdl = '%s <= %s;' % (name, decoded_value)

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
                    'name': name,
                    'vhdl': _vhdl,
                })

            else:

                # this is not a default assignment.  we need to add a default to 
                # our derived list.  the compiler will choose to use it or not.

                # default to its self so a register is born
                _vhdl = _vhdl = '%s <= %s;' % (name, name)

                tokens['procedures'][procedure_index]['defaults']['derived'].append({
                    'name': name,
                    'vhdl': _vhdl,
                })

        # +1
        elif '++' in line:

            log(PROCESSOR, INFO, 'increment found.')

            name = '%s_s' % line.strip().split('++')[0]         
            
            tokens['procedures'][procedure_index]['lines'][i]['vhdl'] = {
                'command': 'increment',
                'indent': line_indent,
                'is_control_structure': False,
                'vhdl': '%s <= %s + \'1\';' % (name, name),
            }

        # -1
        elif '--' in line:

            log(PROCESSOR, INFO, 'increment found.')

            name = '%s_s' % line.strip().split('++')[0]         
            
            tokens['procedures'][procedure_index]['lines'][i]['vhdl'] = {
                'command': 'decrement',
                'indent': line_indent,
                'is_control_structure': False,
                'vhdl': '%s <= %s - \'1\';' % (name, name),
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
        clock = tokens['procedures'][i]['clock']
        reset = tokens['procedures'][i]['reset']

        log(PROCESSOR, INFO, 'processing procedure `%s`' % name)

        if proc_type == 'async':

            # process_lines(index, indent, procedure_index, tokens)

            _i, tokens = process_lines(0, 1, i, tokens)

        elif proc_type == 'sync':

            # process_lines(index, indent, procedure_index, tokens)

            _i, tokens = process_lines(0, 1, i, tokens)

        log(PROCESSOR, INFO, 'done processing procedure `%s`' % name)

    return tokens



def process_assignments(tokens):

    '''
    generate all the port forwards for output registers
    '''

    for i in range(0, len(tokens['vars'])):
        name = tokens['vars'][i]['name']
        port = tokens['vars'][i]['output_register']
        if port:
            tokens['assignments'].append({
                'name': name,
                'port': port,
                'vhdl': '%s <= %s;' % (port, name)
            })

    return tokens

def process(filename):

    start = time.time()

    log(PROCESSOR, INFO, 'processor starting.  working on file: "%s"' % filename)

    lib_dirs = [
        './lib',
    ]

    # get the tokenized verion of the file
    tokens = tokenize(filename)

    tokens = process_components(tokens, lib_dirs)

    tokens = process_ports(tokens)

    tokens = process_vars(tokens)

    tokens = process_procedures(tokens)

    tokens = process_assignments(tokens)

    end = time.time()

    #log(PROCESSOR, DEBUG, 'tokens:\n%s' % json.dumps(tokens, indent=4))

    log(PROCESSOR, INFO, 'processing finished in %.6f seconds' % (end-start) )

    return tokens

if __name__ == '__main__':

    tokens = process('counter32.chdl')

    print(json.dumps(tokens, indent=4))