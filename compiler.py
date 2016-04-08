
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

from processor import process

dir_lut = {
    'in': 'i',
    'out': 'o',
    'inout': 'io',
}

def make_indent(indent):
    retval = ''
    for i in range(0, indent):
        retval += '    '
    return retval

def read_template():
    with open('vhdl.template', 'r') as f:
        template = f.read()
    return template

def compile_ports(tokens):

    dir_lut = {
        'in': 'i',
        'out': 'o',
        'inout': 'io',
    }

    HEADER = '        '
    vhdl = '    port (\n\n'
    for clock in tokens['ports']['clocks']:
        vhdl += '%s-- clock\n' % HEADER
        vhdl += '%s%s_i : in std_logic;\n\n' % (HEADER, clock['name'])
    for reset in tokens['ports']['resets']:
        vhdl += '%s-- reset\n' % HEADER
        vhdl += '%s%s_i : in std_logic;\n\n' % (HEADER, reset['name'])
    vhdl += '%s-- interface ports\n' % HEADER
    for signal in tokens['ports']['signals']:
        name = signal['name']
        signal_type = signal['type']
        direction = signal['direction']
        if signal_type == 'std_logic':
            vhdl += '%s%s_%s : %s std_logic;\n' % (HEADER, name, dir_lut[direction], direction)
        elif signal_type == 'std_logic_vector':
            #direction = signal['direction']
            left = signal['left']
            right = signal['right']
            vhdl += "%s%s_%s : %s std_logic_vector(%s downto %s);\n" % (HEADER, name, dir_lut[direction], direction, left, right)
        else:
            # todo: throw error
            pass
    # we need to take off the last semicolon
    vhdl = '%s\n\n' % vhdl[:-2]
    vhdl += '    );'

    tokens['ports']['vhdl'] = vhdl

    return tokens

def compile_instantiations(tokens):

    

    #print(json.dumps(tokens, indent=4))

    for i in range(0, len(tokens['components'])):
        
        _vhdl = ''

        library = tokens['components'][i]['library'].replace('.','_')
        name = '%s_%s' % (library, tokens['components'][i]['name'])
        _vhdl += '%sinst_%s: entity work.%s ( behavioral )\n' % (make_indent(1), name, library)
        _vhdl += '%sport map(\n' % make_indent(1) 
        
        _vhdl += '\n%s-- clocks\n' % make_indent(2)
        if len(tokens['components'][i]['ports']['clocks']) != 0:
            _vhdl += '%s%s_i => %s_i,\n' % (make_indent(2), tokens['components'][i]['ports']['clocks'][0]['name'], tokens['ports']['clocks'][0]['name'])
        
        _vhdl += '\n%s-- resets\n' % make_indent(2)
        if len(tokens['components'][i]['ports']['resets']) != 0:
            _vhdl += '%s%s_i => %s_i,\n' % (make_indent(2), tokens['components'][i]['ports']['resets'][0]['name'], tokens['ports']['resets'][0]['name'])
        
        _vhdl += '\n%s-- interface ports\n' % make_indent(2)
        for signal in tokens['components'][i]['ports']['signals']:
            signal_name = signal['name']
            signal_signal_name = '%s_%s_s' % (tokens['components'][i]['name'], signal['name'])
            _vhdl += '%s%s_%s => %s,\n' % (make_indent(2), signal_name, dir_lut[signal['direction']], signal_signal_name)
        # need to get ride of the last comma
        _vhdl = '%s\n' % _vhdl[:-2]
        _vhdl += '\n%s);\n\n' % make_indent(1)

        tokens['components'][i]['vhdl'] = _vhdl

    return tokens

def compile_sync_proceedure(i, tokens):

    HEADER = '    '

    name = tokens['procedures'][i]['name']
    clock = tokens['procedures'][i]['clock']
    reset = tokens['procedures'][i]['reset']['name']

    _vhdl = ''
    _vhdl += '%s%s: process( %s_i )\n' % (make_indent(1), name, clock)
    _vhdl += '%sbegin\n' % make_indent(1)
    _vhdl += '%sif ( rising_edge( %s_i ) ) then\n%sif ( %s_i = \'1\' ) then\n\n%s-- reset values\n' % (
        make_indent(2), clock, make_indent(3), reset, make_indent(4)
    )

    for assignment in tokens['procedures'][i]['reset']['assignments']:
        _vhdl += '%s%s;\n' % (make_indent(4), assignment['vhdl'])

    _vhdl += '\n%selse\n' % make_indent(3)
    _vhdl += '\n%s-- derived defaults\n' % make_indent(4)
    derived_list = []
    for derived in tokens['procedures'][i]['defaults']['derived']:
        found = False
        if not (derived['name'] in derived_list):
            #print('adding "%s" to derived list' % derived['name'])
            derived_list.append(derived['name'])
            for defined in tokens['procedures'][i]['defaults']['defined']:
                if derived['name'] == defined['name']:
                    found = True
                    break
        else:
            found = True
                    
        if not found:
            _vhdl += '%s%s\n' % (make_indent(4), derived['vhdl'])

    _vhdl += '\n'
    _vhdl += '%s-- process logic\n' % make_indent(4)
    current_indent = -1 # small.

    for j in range(0, len(tokens['procedures'][i]['lines'])):
        _line = tokens['procedures'][i]['lines'][j]
        if 'vhdl' in _line:
            line = _line['line']
            #line_number = _line['line_number']
            vhdl = _line['vhdl']['vhdl']
            indent = _line['vhdl']['indent']
            command = _line['vhdl']['command']
            is_control_structure = _line['vhdl']['is_control_structure']

            # the processor has placed endif commands after each "if", "elsif", and else
            # control structures.  we need to deturmine which ones need to be removed
            # since we're not done with the control structure tree

            if command == 'endif':
                _num_lines = len(tokens['procedures'][i]['lines'])
                _indent = current_indent
                _command = None
                #print(_num_lines, _indent, _command, len(tokens['procedures'][i]['lines']), )
                if (j+1) < len(tokens['procedures'][i]['lines']):
                    _indent = tokens['procedures'][i]['lines'][j+1]['vhdl']['indent']
                    _command = tokens['procedures'][i]['lines'][j+1]['vhdl']['command']
                    #print('inside0', _command)
                if _command == 'elsif' or _command == 'else':
                    #print('inside1')
                    pass
                else:
                    #print('inside2')
                    _vhdl += '%send if;\n' % (make_indent(indent+3))

            else:
                _vhdl += '%s%s\n' % (make_indent(indent+3), vhdl)

            
    _vhdl += '\n%send if;\n' % make_indent(3);
    _vhdl += '%send if;\n' % make_indent(2);
    _vhdl += '%send process;\n' % make_indent(1)

    tokens['procedures'][i]['vhdl'] = _vhdl

    return tokens

def compile_async_procedure(i, tokens):

    name = tokens['procedures'][i]['name']
    reset = tokens['procedures'][i]['reset']['name']

    sensitivity_list = []
    lines = []
    for j in range(0, len(tokens['procedures'][i]['lines'])):
        vhdl = tokens['procedures'][i]['lines'][j]['vhdl']['vhdl']
        lines.append('%s%s' % (make_indent(2), vhdl))
        signal_name = vhdl.split('<=')[1].replace(';','').strip()
        # todo: check to see if signal_name is actually a signal
        sensitivity_list.append(signal_name)

    _vhdl = ''
    _vhdl += '%s%s: process( %s )\n' % (make_indent(1), name, ', '.join(sensitivity_list))
    _vhdl += '%sbegin\n' % make_indent(1)
    if reset:
        # todo: handle reset in async process
        pass
    _vhdl += '%s\n' % ('\n'.join(lines))
    if reset:
        _vhdl += '%send if;\n' % make_indent(2);
    _vhdl += '%send process;\n\n' % make_indent(1)

    tokens['procedures'][i]['vhdl'] = _vhdl

    return tokens

def compile_procedures(tokens):

    for i in range(0, len(tokens['procedures'])):
        if tokens['procedures'][i]['proc_type'] == 'sync':
            tokens = compile_sync_proceedure(i, tokens)
        elif tokens['procedures'][i]['proc_type'] == 'async':
            tokens = compile_async_procedure(i, tokens)

    return tokens

def populate_template(tokens):

    HEADER = '    '

    entity_name = '%s_%s' % (tokens['library'].replace('.','_'), tokens['entity'])
    #entity_name = tokens['entity']
    ports = tokens['ports']['vhdl']
    components = ''
    signals = ''
    for signal in tokens['vars']:
        signals += '%ssignal %s\n' % (HEADER, signal['vhdl'])
    assignments = ''
    for assignment in tokens['assignments']:
        assignments = '%s%s\n' % (HEADER, assignment['vhdl'])
    instantiations = ''
    for component in tokens['components']:
        instantiations += component['vhdl']
    procedures = ''
    for procedure in tokens['procedures']:
        procedures += procedure['vhdl'] 

    template_lut = [
        ('<<entity_name>>',     entity_name),
        ('<<generics>>',        '--    generic (\n--        \n--    );'),
        ('<<ports>>',           ports),
        ('<<components>>',      components),
        ('<<signals>>',         signals),
        ('<<assignments>>',     assignments),
        ('<<instantiations>>',  instantiations),
        ('<<procedures>>',      procedures),
    ]

    # read in the template for replacement
    vhdl = read_template()

    for key, value in template_lut:
        vhdl = vhdl.replace(key, value)

    return vhdl

def do_compile(filename):

    start = time.time()

    log(COMPILER, INFO, 'processor starting')

    # get processed tokens
    tokens = process(filename)

    #log(COMPILER, DEBUG, 'post-processor tokens:\n%s' % json.dumps(tokens, indent=4))

    tokens = compile_ports(tokens)

    tokens = compile_instantiations(tokens)

    tokens = compile_procedures(tokens)

    vhdl = populate_template(tokens)

    end = time.time()

    log(COMPILER, INFO, 'compiling finished in %.6f seconds' % (end-start) )

    return vhdl

if __name__ == '__main__':

    filename = sys.argv[1]

    vhdl = do_compile(filename) #'./lib/chdl/basic/pwm.chdl')

    print(vhdl)

    with open('%s.vhd' % filename.split('.chdl')[0], 'w') as f: #'./lib/chdl/basic/pwm.vhd', 'w') as f:
        f.write(vhdl)
