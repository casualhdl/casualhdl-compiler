
from log import (
    log,
    COMPILER,
    INFO,
    ERROR,
    WARNING,
    DEBUG,
)

import json
import re
import sys
import time

from tokenizer import tokenize

def read_template():
    with open('vhdl.template', 'r') as f:
        template = f.read()
    return template

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

def make_indent(indent):
    retval = ''
    for i in range(0, indent):
        retval += '    '
    return retval

def zero_extend(value, width):

    v = ''
    for i in range(0, width):
        v += '0'
    v = v + value

    return v

def decode_assignment_value(value, signal):

    log(COMPILER, INFO, 'decoding assignment. value = "%s", signal type = "%s"' % (value, signal['type']))

    #
    # TODO: look for period, and then go find the type of the signal since
    #       we're assigning something to a component instantiation
    #

    if signal['type'] == 'std_logic_vector':
        # get total width of vector
        width = abs(int(signal['left'])) + abs(int(signal['right'])) +  1

    v = ''
    if signal['type'] == 'std_logic':
        v = "'%s'" % value 
    elif signal['type'] == 'std_logic_vector':
        # binary value
        if '"' in value:
            # we need to zero extend in the event that it isn't
            # the right widt
            v = value.replace('"','')
            v = '"%s"' % zero_extend(v, width)

        # hex
        elif '0x' in value:
            pass

        # all zeros
        if value == 'zeros':
            v = '"%s"' % zero_extend('', width)

        # decimal
        else:
            pass

    else:
        # throw error
        pass

    return v

def signal_from_name(name, ports, _vars):

    # need to make sure that the assignment is to a defined port or var
    # before we know what to do with it.
    found = False
    signal = None
    _assignment = None
    for _signal in ports['signals']:
        #log(_signal)
        if name == _signal['name']:
            log(COMPILER, INFO, 'assignment is to a port.')
            assignment_type = 'port'
            found = True
            signal = _signal
            _assignment = '%s_o <= %s_s;' % (_signal['name'], _signal['name'])
            break
        
    if not found:
        for _signal in _vars:
            #log(_signal)
            if name == _signal['name']:
                log(COMPILER, INFO, 'assignment is to a var.')
                assignment_type = 'var'
                found = True
                signal = _signal
            
    if not found:
        # throw error
        raise Exception('bad')
        pass

    return signal, assignment_type, _assignment

def process_assignment(line, ports, _vars):

    parts = line.split('=')
    name = parts[0].strip()
    value = parts[1].strip()

    log(COMPILER, DEBUG, 'decoding assignment, name: `%s`, value: `%s`' % (name, value))

    _signal = None
    _line = None

    # dummy because we're doing it below
    signal, assignment_type, _assignment = signal_from_name(name, ports, _vars)

    # it's a port.
    # we need to create a signal, and an assignment so
    # the output is registered
    if assignment_type == 'port':

        value = decode_assignment_value(value, signal)

        signal_name = '%s_s' % name
        #_signal = {
        #    'name': signal_name,
        #    'type': signal['type'],
        #}
        _signal = signal
        signal.update(
            name='%s_s' % signal['name'],
        )

        _line = '%s <= %s;' % (signal_name, value)
        
        #_assignment = '%s_o <= %s;' % (name, signal_name)

        log(COMPILER, DEBUG, 'created port assignment: `%s`' % _line)
        log(COMPILER, DEBUG, 'creating signal for port register: `%s`' % signal_name)

    # it's a var.
    # we just need to do the assignment, no need to create a output
    # register like with a port
    elif assignment_type == 'var':

        value = decode_assignment_value(value, signal)

        signal_name = '%s_s' % name
        
        _line = '%s <= %s;' % (signal_name, value)

        log(COMPILER, DEBUG, 'created var assignment: `%s`' % _line)

    else:
        # throw error
        #raise Exception('bad')
        pass

    return _signal, _line, _assignment

def merge_vhdl_structures(old, new):

    '''
    vhdl = {
        'lines': [],
        'defauls': [],
        'signals': [],
        'assignments': [],
    }
    '''

    vhdl = old

    for line in new['lines']:
        vhdl['lines'].append(line)

    # there is no way that a control structure can define a default
    #for default in new['defauls']:
    #    old['defaults'].append(defauls)
    
    for signal in new['signals']:
        vhdl['signals'].append(signal)

    for assignment in new['assignments']:
        vhdl['assignments'].append(assignment)

    return vhdl

def decode_condition(line, ports, _vars):

    condition = 'if '.join(re.sub(' +',' ',line.strip()).split('if ')[1:]).split(':')[0]

    target = condition.split(' ')[0]
    operation = condition.split(' ')[1]
    value = condition.split(' ')[2]

    signal, assignment_type, dummy = signal_from_name(target, ports, _vars)

    decoded_value = decode_assignment_value(value, signal)

    return target, operation, decoded_value

def process_lines(index, indent, lines, ports, _vars):
    '''

    1) assignments are defauls.  assignments are defined as

           <name> = <value>

    2) anything left of an `=` needs to be a defined var or port.

    3) every line is either:

       a) blank

       b) `reset:`

       c) if <condition>:
       
       d) elif <condition>:

       e) else:

       f) case <name>:

       g) fsm <name>:

       h) <state>:

       i) <name> = <value>

       j) <name>++

       k) <name>--

    4)  

    '''

    #log(COMPILER, INFO, 'starting to compile process into vhdl.')

    #log(COMPILER, DEBUG, 'Lines:\n%s' % json.dumps(lines, indent=4))

    vhdl = {
        'lines': [],
        'defauls': [],
        'assignments': [],
        'signals': [],
        'resets': [],
    }

    inside_if_control_structure = False
    inside_case_control_structure = False
    inside_fsm_control_structure = False

    line_indent = sys.maxsize # big.

    i = index
    while(True):
        _line = lines[i]
        line = _line['line']
        line_number = _line['line_number']
        last_line_indent = line_indent
        line_indent = get_indent(line)

        log(COMPILER, DEBUG, '%i (%i): %s' % (line_number, line_indent, line))

        # handle closing control structures
        if inside_if_control_structure and last_line_indent > line_indent:
            vhdl.append({
                'indent': line_indent,
                'vhdl': 'end if;',
            })

        if i == index and line.strip() != 'reset:':
            # todo: throw error
            pass

        # reset assignments
        elif i == index and line.strip() == 'reset:':
            
            log(COMPILER, INFO, 'parsing process reset assignments.')

            # inc line counter to get to first assignment
            
            reset_line_index = -1
            while(True):

                # go to next line
                i += 1

                _line = lines[i]
                line = _line['line']
                line_number = _line['line_number']
                reset_line_indent = get_indent(line)

                log(COMPILER, DEBUG, '%i (%i): %s' % (line_number, line_indent, line))

                signal, _line, assignment = process_assignment(line, ports, _vars)

                if signal:
                    vhdl['signals'].append(signal)

                if assignment:
                    vhdl['assignments'].append(assignment)

                vhdl['resets'].append(_line)

                log(COMPILER, DEBUG, 'line_indent: %i, reset_line_indent: %i' % (line_indent, reset_line_indent))

                if i+1 == len(lines):
                    # todo: throw error
                    pass

                next_indent = get_indent(lines[i+1]['line'])

                if next_indent == 0 or next_indent < reset_line_indent:
                    break;

            log(COMPILER, DEBUG, 'done with reset assignments.')

        # blank
        elif line.strip() == '':
            log(COMPILER, INFO, 'blank line.')
            pass
        
        # if control structure
        elif '    if ' in line:
            log(COMPILER, INFO, '`if` control structure found.')
            
            target, operation, decoded_value = decode_condition(line, ports, _vars)

            vhdl['lines'].append({
                'indent': line_indent,
                'vhdl': 'if ( %s %s %s ) then' % (target, operation, decoded_value),
            })

            # recusive call to self to handle contents within control structure
            i, inside_vhdl = process_lines(i, line_indent, lines, ports, _vars)

            # merge with the inside of the control structure
            vhdl = merge_vhdl_structures(vhdl, inside_vhdl)

            # this get's tricky ... we can't add this until we know that there aren't
            # any `elsif` or `else` coming ...
            
            #vhdl['lines'].append({
            #    'indent': line_indent,
            #    'vhdl': 'end if;',
            #})

            # ... so we'll set a flag, and if the indent is less, and it's not a `elsif`
            # or an `else`, then we'll tag on the end if.

            # TODO: add flag ^^^^

        # elif control structure
        elif '    elsif ' in line:
            log(COMPILER, INFO, '`elsif` control structure found.')
            
            target, operation, decoded_value = decode_condition(line, ports, _vars)

            vhdl['lines'].append({
                'indent': line_indent,
                'vhdl': 'elsif ( %s %s %s ) then' % (target, operation, decoded_value),
            })

            # recusive call to self to handle contents within control structure
            i, inside_vhdl = process_lines(i, line_indent, lines, ports, _vars)

            # merge with the inside of the control structure
            vhdl = merge_vhdl_structures(vhdl, inside_vhdl)

            # this get's tricky ... we can't add this until we know that there aren't
            # any `elsif` or `else` coming ...
            
            #vhdl['lines'].append({
            #    'indent': line_indent,
            #    'vhdl': 'end if;',
            #})

            # ... so we'll set a flag, and if the indent is less, and it's not a `elsif`
            # or an `else`, then we'll tag on the end if.

            # TODO: add flag ^^^^

        # else control structure
        elif '    else:' in line:
            log(COMPILER, INFO, '`else` control structure found.')
            
            vhdl['lines'].append({
                'indent': line_indent,
                'vhdl': 'else',
            })

            # recusive call to self to handle contents within control structure
            i, inside_vhdl = process_lines(i, line_indent, lines, ports, _vars)

            # merge with the inside of the control structure
            vhdl = merge_vhdl_structures(vhdl, inside_vhdl)

            # we can add the `end if` here, since there can't be anything after it
            vhdl['lines'].append({
                'indent': line_indent,
                'vhdl': 'end if;',
            })


        # case control structure
        elif '    case ' in line:
            log(COMPILER, INFO, '`case` control structure found.')
            pass

        # fsm control structure
        elif '    fsm ' in line:
            log(COMPILER, INFO, '`fsm` control structure found.')
            pass

        # assignment
        elif len(line.split('=')) != 1:

            #
            # TODO: Handle math and stuff
            #

            log(COMPILER, INFO, 'assignment found.')

            signal, _vhdl, assignment = process_assignment(line, ports, _vars)

            if signal:
                vhdl['signals'].append(signal)

            if assignment:
                vhdl['assignments'].append(assignment)

            #vhdl['assignments'].append(assignment)
            #vhdl['lines'].append(assignment)

            vhdl['lines'].append({
                'indent': line_indent,
                'vhdl': _vhdl,
            })

        # +1
        elif '++' in line:
            log(COMPILER, INFO, 'increment found.')
            target = line.strip().split('++')[0]

            signal, _dummy, assignment = signal_from_name(target, ports, _vars)

            if signal:
                vhdl['signals'].append(signal)

            if assignment:
                vhdl['assignments'].append(assignment)

            vhdl['lines'].append({
                'indent': line_indent,
                'vhdl': '%s_s <= %s_s + \'1\'' % (target, target),
            })

        # -1
        elif '--' in line:
            log(COMPILER, INFO, 'decrement found.')
            
            target = line.strip().split('--')[0]

            signal, _dummy, assignments = signal_from_name(target, ports, _vars)

            if signal:
                vhdl['signals'].append(signal)

            if assignment:
                vhdl['assignments'].append(assignment)

            vhdl['lines'].append({
                'indent': line_indent,
                'vhdl': '%s <= %s - \'1\'' % (target, target),
            })


        else:
            # todo: throw error
            pass
        
        if i+1 == len(lines):
            # at end of file
            break
            
        if lines[i+1]['line'].strip() != '':
            next_indent = get_indent(lines[i+1]['line'])

            # check for end of file, or unindent
            if next_indent == 0 or next_indent < line_indent:
                break;

        i += 1

    return i, vhdl

def parse_procedures(tokens):

    '''
    This the meaty part of the compiler.

    We need to deturmine the direction of all of the ports used
    in the procedures in the entity.  Next, we'll need to create
    new "vars" ( signals ) for the outputs, so they're all 
    registered.
    
    1) within a sync or async proc, anything that has an assignment 
       at an indent of 0, and does not have an assignment in any 
       control structures is a simple assignment ( register for sync, 
       just an assignment for async ).  There is no need for anything 
       else to be done, because it only ever is itself.

        chdl:
            proc my_signal_assignment = sync(clk, reset):
                reset:
                    my_signal = 0
                my_signal = input_signal

        vhdl:
            my_signal_assignment: process( clk )
               begin
                   if rising_edge( i_clk ) then
                       if ( reset = '1' ) then
                           my_signal = '0';
                       else
                           my_signal <= input_signal;
                       end if;
                   end if;
               end process;

    2) within a sync or async proc any signal that has an assignment
       with in a control structure, but not a "default" assignment 
       outside of that control structure will get itself as the default.
       Note that this occurs when there is no 'else' or 'default' 
       in the control structure.

        chdl:
            proc my_proc = sync(clk, reset)
                reset:
                    my_signal = 0
                if input_signal_a = 1:
                    my_signal = input_signal_b

        vhdl:
            my_proc: process( clk )
                begin
                if rising_edge( i_clk ) then
                       if ( reset = '1' ) then
                           my_signal = '0';
                       else
                           -- default
                           my_signal <= my_signal;

                           if ( input_signal_a = '1' ) then
                               my_signal <= input_signal_b;
                           end if;
                       end if;
                   end if;
               end process;

    3) with a sync or async proc, any signal that has an assignment
       within a control structure, as well as an 'else' or a 'default'
       statement, there is no need for a default assignment.

       note 0: this is more verbose than needed, since 2) above handles
               the automatic default assignment.

       note 1: this may be needed, if a default value of not the signals
               self is needed. 

           chdl:
               proc my_proc = sync(clk, reset):
                   reset:
                       my_signal = 0
                   if input_signal_a = 1:
                       my_signal = input_signal_b
                   else:
                       my_signal = my_signal

           vhdl:
               my_proc: process( clk )
            begin
                if rising_edge( i_clk ) then
                       if ( reset = '1' ) then
                           my_signal = '0';
                       else
                           if ( input_signal_a = '1' ) then
                               my_signal <= input_signal_b;
                           else:
                               my_signal <= my_signal;
                           end if;
                       end if;
                   end if;
               end process;

    4) if a async or sync process has a reset, the first non-empty line after
       the process declaration line must be `reset:`.

    5) reset contents must not be empty

    '''

    _ports = tokens['ports']
    _vars = tokens['vars']
    _procedures = []

    # first, pre-process all the lines in all procedures
    for procedure in tokens['procedures']:

        name = procedure['name']
        proc_type = procedure['proc_type']
        clock = procedure['clock']
        reset = procedure['reset']
        lines = []
        vhdl = ''
        signals = []
        assignments = []

        lines = procedure['lines']

        #for line in procedure['lines']:
        #
        #    # remove duplicate spaces
        #    l = re.sub(' +',' ',line)
        #    lines.append(l)

        log(COMPILER, INFO, 'process name: "%s", type: "%s"' % (name, proc_type))

        if proc_type == 'async':
            #if reset == '' or reset == None:
            #    dummy, vhdl = process_lines(0, 4, lines, _vars, _ports)
            dummy, vhdl = process_lines(0, 4, lines, _ports, _vars)

        elif proc_type == 'sync':
            #if reset == '' or reset == None:
            #    dummy, vhdl = process_lines(0, 4, lines, _vars, _ports)
            dummy, vhdl = process_lines(0, 4, lines, _ports, _vars)

        _procedures.append({
            'name': name,
            'proc_type': proc_type,
            'clock': clock,
            'reset': reset,
            'lines': lines,
            'vhdl': vhdl,
            'signals': signals,
        })

    return _procedures


def build_ports_vhdl(ports):
    HEADER = '        '
    vhdl = '    port (\n'
    for clock in ports['clocks']:
        vhdl += HEADER + clock + ' : in std_logic;\n'
    for reset in ports['resets']:
        vhdl += HEADER + reset + ' : in std_logic;\n'
    for signal in ports['signals']:
        name = signal['name']
        signal_type = signal['type']
        if signal_type == 'std_logic':
            vhdl += HEADER + name + ' : in std_logic;\n'
        elif signal_type == 'std_logic_vector':
            #direction = signal['direction']
            direction = 'inout'
            left = signal['left']
            right = signal['right']
            vhdl += "%s%s : %s std_logic_vector(%s downto %s);\n" % (HEADER, name, direction, left, right)
        else:
            # todo: throw error
            pass
    vhdl += '    );'
    return vhdl


def build_components_vhdl():
    
    vhdl = ''

    vhdl = '    --\n    -- components\n    --\n'

    return vhdl


def build_signals_vhdl(_vars, _procedures):

    vhdl = ''
    vhdl += '    --\n    -- signals\n    --\n\n'
 
    #
    # TODO: should we add the `_s` suffix here, or when we find 
    #       the var deffinition ????
    #

    _signals = []
    for var in _vars:
        if var['type'] == 'std_logic':
            _signals.append('    signal %s_s :  std_logic;\n' % var['name'])
        elif var['type'] == 'std_logic_vector':
            _signals.append('    signal %s_s : std_logic_vector(%s downto %s);\n' % (var['name'], var['left'], var['right']))
        else:
            # todo: throw error
            pass

    vhdl += '    \n'

    # build up list of all output registers ( note: there may be duplicates )
    _registers = []
    for procedure in _procedures:
        for signal in procedure['vhdl']['signals']:
            if signal['type'] == 'std_logic':
                _registers.append('    signal %s :  std_logic;\n' % signal['name'])
            elif signal['type'] == 'std_logic_vector':
                _registers.append('    signal %s : std_logic_vector(%s downto %s);\n' % (signal['name'], signal['left'], signal['right']))
            else:
                # todo: throw error
                pass

    vhdl += '    -- internal signals\n'

    # add unique registers to vhdl output
    for signal in _signals:
        vhdl += signal

    # remove duplicates
    seen = set()
    registers = []
    for register in _registers:
        print(register)
        if register not in seen and register not in _signals:
            seen.add(register)
            registers.append(register)

    vhdl += '\n    -- output register signals\n'

    # add unique registers to vhdl output
    for register in registers:
        vhdl += register

    return vhdl


def build_assignments_vhdl(_procedures):

    vhdl = ''

    vhdl = '    --\n    -- assignments\n    --\n\n'

    for procedure in _procedures:
        for assignment in procedure['vhdl']['assignments']:
            vhdl += '    %s\n' % assignment
    return vhdl


def build_instantiations_vhdl():

    vhdl = ''

    vhdl = '    --\n    -- instantiations\n    --\n'

    return vhdl



def build_procesure_vhdl(procedures, tokens):

    vhdl = '    --\n    -- processes\n    --\n'

    for procedure in procedures:

        vhdl += '    \n'
        vhdl += '    proc_%s: process( %s )\n' % (procedure['name'], procedure['clock'])
        vhdl += '    begin\n'
        vhdl += '        if ( rising_edge( %s ) ) then\n' % procedure['clock']
        vhdl += '            if ( %s = \'1\' ) then\n' % procedure['reset']
        for reset in procedure['vhdl']['resets']:
            vhdl += '                %s\n' % reset
        vhdl += '            else\n'
        for line in procedure['vhdl']['lines']:
            vhdl += '            %s%s\n' % (make_indent(line['indent']), line['vhdl'])
        vhdl += '            end if;\n'
        vhdl += '        end if;\n'
        vhdl += '    end process;\n'

    #log(COMPILER, DEBUG, 'processes `%s` vhdl:\n%s' % (procedure['name'], vhdl))

    return vhdl


def compile(filename, verbose=False):

    # tokenize the file
    tokens = tokenize(filename, verbose)

    # generate the entity name based on the library
    entity_name_vhdl = '%s_%s' % (tokens['library'].replace('.', '_'), tokens['entity'])

    # based on the contents of the procedures in the entity,
    # we need to generate assignments and port directions.
    _procedures = parse_procedures(tokens)

    # generate ports vhdl
    ports_vhdl = build_ports_vhdl(tokens['ports'])

    components_vhdl = build_components_vhdl()

    signals_vhdl = build_signals_vhdl(tokens['vars'], _procedures)

    assignments_vhdl = build_assignments_vhdl(_procedures)

    instantiations_vhdl = build_instantiations_vhdl()    

    # generate procedures
    procedures_vhdl = build_procesure_vhdl(_procedures, tokens)

    #log(COMPILER, DEBUG, 'procedures:\n%s' % json.dumps(_procedures, indent=4))

    template_lut = [
        ('<<entity_name>>',     entity_name_vhdl),
        ('<<generics>>',        '--    generic (\n--        \n--    );'),
        ('<<ports>>',           ports_vhdl),
        ('<<components>>',      components_vhdl),
        ('<<signals>>',         signals_vhdl),
        ('<<assignments>>',     assignments_vhdl),
        ('<<instantiations>>',  instantiations_vhdl),
        ('<<procedures>>',      procedures_vhdl),
    ]

    # read in the template for replacement
    template = read_template()

    for key, value in template_lut:
        template = template.replace(key, value)

    return template


if __name__ == '__main__':

    #log(json.dumps(compile('counter32.chdl', verbose=True), indent=4))

    #log(compile('pwm.chdl', verbose=True))

    #compile('pwm.chdl', verbose=True)

    start = time.time()

    vhdl = compile('counter32.chdl', verbose=True)

    end = time.time()

    log(COMPILER, INFO, 'file compiled in %.6f seconds' % (end-start) )

    log(COMPILER, INFO, 'VHDL\n%s' % vhdl)

