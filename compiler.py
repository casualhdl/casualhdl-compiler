
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
    HEADER = '        '
    vhdl = '    port (\n\n'
    for clock in tokens['ports']['clocks']:
        vhdl += '%s-- clock\n' % HEADER
        vhdl += '%s%s : in std_logic;\n\n' % (HEADER, clock['name'])
    for reset in tokens['ports']['resets']:
        vhdl += '%s-- reset\n' % HEADER
        vhdl += '%s%s : in std_logic;\n\n' % (HEADER, reset['name'])
    for signal in tokens['ports']['signals']:
        name = signal['name']
        signal_type = signal['type']
        if signal_type == 'std_logic':
            direction = 'inout'
            vhdl += '%s%s : %s std_logic;\n' % (HEADER, name, direction)
        elif signal_type == 'std_logic_vector':
            #direction = signal['direction']
            direction = 'inout'
            left = signal['left']
            right = signal['right']
            vhdl += "%s%s : %s std_logic_vector(%s downto %s);\n" % (HEADER, name, direction, left, right)
        else:
            # todo: throw error
            pass
    # we need to take off the last semicolon
    vhdl = '%s\n\n' % vhdl[:-2]
    vhdl += '    );'

    tokens['ports']['vhdl'] = vhdl

    return tokens

def compile_procedures(tokens):

    HEADER = '    '

    for i in range(0, len(tokens['procedures'])):
        
        clock = tokens['procedures'][i]['clock']
        reset = tokens['procedures'][i]['reset']['name']

        _vhdl = ''
        _vhdl += '%sprocess( %s )\n' % (make_indent(1), clock)
        _vhdl += '%sbegin\n' % make_indent(1)
        _vhdl += '%sif ( rising_edge( %s ) ) then\n%sif ( %s = \'1\' ) then\n' % (
            make_indent(2), clock, make_indent(3), reset,
        )

        for assignment in tokens['procedures'][i]['reset']['assignments']:
            _vhdl += '%s%s;\n' % (make_indent(4), assignment['vhdl'])

        _vhdl += '%selse\n' % make_indent(3)
        current_indent = -1 # small.
        for j in range(0, len(tokens['procedures'][i]['lines'])):
            _line = tokens['procedures'][i]['lines'][j]
            if 'vhdl' in _line:
                line = _line['line']
                #line_number = _line['line_number']
                vhdl = _line['vhdl']['vhdl']
                indent = _line['vhdl']['indent']
                is_control_structure = _line['vhdl']['is_control_structure']

                _vhdl += '%s%s\n' % (make_indent(indent+3), vhdl)

                # if this line isn't a control structure ...
                if not is_control_structure:

                    # and we're at the end of the file OR our indent is decreasing, then we
                    # need to close our control structure.
                    if j+1 == len(tokens['procedures'][i]['lines']) or current_indent > tokens['procedures'][i]['lines'][j+1]['vhdl']['indent']:

                        _vhdl += '%send if;\n' % make_indent(indent+2)

                current_indent = indent

        _vhdl += '%send if;\n' % make_indent(3);
        _vhdl += '%send if;\n' % make_indent(2);
        _vhdl += '%send process;\n\n' % make_indent(1)

        tokens['procedures'][i]['vhdl'] = _vhdl

    return tokens

def populate_template(tokens):

    HEADER = '    '

    entity_name = tokens['entity']
    ports = tokens['ports']['vhdl']
    components = ''
    signals = ''
    for signal in tokens['vars']:
        signals += '%ssignal %s\n' % (HEADER, signal['vhdl'])
    assignments = ''
    for assignment in tokens['assignments']:
        assignments = '%s%s\n' % (HEADER, assignment['vhdl'])
    instantiations = ''
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

    log(COMPILER, DEBUG, 'post-processor tokens:\n%s' % json.dumps(tokens, indent=4))

    tokens = compile_ports(tokens)

    tokens = compile_procedures(tokens)

    vhdl = populate_template(tokens)

    end = time.time()

    log(COMPILER, INFO, 'compiling finished in %.6f seconds' % (end-start) )

    return vhdl

if __name__ == '__main__':

    vhdl = do_compile('counter32.chdl')

    print(vhdl)

    with open('counter32.vhd', 'w') as f:
        f.write(vhdl)
