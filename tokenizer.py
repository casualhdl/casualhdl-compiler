
from log import (
    log,
    TOKENIZER,
    INFO,
    WARNING,
    ERROR,
    DEBUG,
)

import time
import json

def read_template():
    with open('vhdl.template', 'r') as f:
        template = f.read()
    return template

def read_lines(filename):
    with open(filename, 'r') as f:
        lines = f.read().split('\n')
    return lines

def get_indent(line):
    indent = -1
    for i in range(0, len(line)):
        c = line[i]
        if c != ' ':
            indent = i
            break
    return indent

def preprocess(i, line, whitespace=False):
    # remove comments and whitespace
    line = line.split('#')[0]
    if not whitespace:
        line = line.strip()
    return {'line_number': i, 'line': line}

def tokenize(filename, verbose=False):
    
    start = time.time()

    log(TOKENIZER, INFO, 'tokenizer starting')

    # read file
    lines = read_lines(filename)
    # setup response structure
    tokens = {}
    tokens['components'] = []
    tokens['ports'] = {}
    tokens['ports']['clocks'] = []
    tokens['ports']['resets'] = []
    tokens['ports']['signals'] = []
    tokens['vars'] = []
    tokens['assignments'] = []
    tokens['procedures'] = []
    # do first pass of file, and tokenize
    eof = False
    i = 0;
    while not eof:
        
        line = preprocess(i, lines[i])

        log(TOKENIZER, DEBUG, "%i  \t%s" % (i, line['line']))

        if '\t' in line:
            # todo: throw error
            pass

        if line['line'].strip() == '':
            i += 1
            if i == len(lines):
                eof = True
                log(TOKENIZER, INFO, 'reached end of file.')
                break
            continue

        parts = line['line'].split(' ')
        cmd = parts[0]
        
        if cmd == 'library':
            # library chdl.basic

            if len(parts) == 2:
                tokens['library'] = parts[1]
            else:
                # todo: throw error
                pass

            log(TOKENIZER, INFO, "found library: '%s'" % parts[1])

        elif cmd == 'entity':
            # entity counter32
            if len(parts) == 2:
                tokens['entity'] = parts[1]
            else:
                # todo: throw error
                pass

            log(TOKENIZER, INFO, "found entity: '%s'" % parts[1])

        elif cmd == 'port':
            # port pulse = bit()
            # port count_max = vector()
            # port count_max = vector(31, 0)
            if len(parts) >= 4:
                name = parts[1]
                equals = parts[2]
                rest = ' '.join(parts[3:])
                rest_parts = rest.replace(' ','').split('(')
                if rest_parts[0] == 'clock':
                    if len(rest_parts) == 1:
                        # todo: throw error
                        pass
                    elif rest_parts[1] != ')':
                        # todo: throw error
                        pass
                    else:
                        tokens['ports']['clocks'].append({
                            'name': name,
                            'vhdl': '',
                        })
                elif rest_parts[0] == 'reset':
                    if len(rest_parts) == 1:
                        # todo: throw error
                        pass
                    elif rest_parts[1] != ')':
                        # todo: throw error
                        pass
                    else:
                        tokens['ports']['resets'].append({
                            'name': name,
                            'vhdl': '',
                        })
                elif rest_parts[0] == 'bit':
                    if len(rest_parts) == 1:
                        # todo: throw error
                        pass
                    elif rest_parts[1] != ')':
                        # todo: throw error
                        pass
                    else:
                        tokens['ports']['signals'].append({
                            'name': name,
                            'type': 'std_logic',
                            'left': None,
                            'right': None,
                            'direction': None,
                            'vhdl': '',
                        })
                elif rest_parts[0] == 'vector':
                    log(TOKENIZER, DEBUG, 'port, vector found.')
                    log(TOKENIZER, DEBUG, rest_parts)
                    if len(rest_parts) == 1:
                        # todo: throw error
                        pass
                    # we do not (yet) support non-dimensioned vectors 
                    elif rest_parts[1] == ')':
                        # todo: throw error
                        pass
                    else:
                        
                        inside = rest.split('(')[1].split(')')[0]
                        left = inside.split(',')[0].strip()
                        right = inside.split(',')[1].strip()

                        tokens['ports']['signals'].append({
                            'name': name,
                            'type': 'std_logic_vector',
                            'left': left,
                            'right': right,
                            'direction': None,
                            'vhdl': '',
                        })
                else:
                    # todo: throw error
                    pass
            else:
                # todo: throw error
                pass

            log(TOKENIZER, INFO, "found port: '%s' of type '%s'" % (parts[1], rest_parts[0]) )

        elif cmd == 'component':
            # component chdl.basic.counter32 as my_counter
            if len(parts) >= 4:
                library = parts[1]
                _as = parts[2]
                name = ' '.join(parts[3:])
                tokens['components'].append({
                    'library': library,
                    'name': name,    
                })
            else:
                # todo: throw error
                pass

            log(TOKENIZER, INFO, "found component: '%s' as '%s'" % (library, name)) 

        elif cmd == 'var':
            # var counter = slv(31, 0)
            if len(parts) >= 4:
                name = parts[1]
                equals = parts[2]
                rest = ' '.join(parts[3:])
                rest_parts = rest.replace(' ','').split('(')
                if rest_parts[0] == 'bit':
                    if len(rest_parts) == 1:
                        # todo: throw error
                        pass
                    elif rest_parts[1] != ')':
                        # todo: throw error
                        pass
                    else:
                        # note: we add `_s` to the end of all signals
                        tokens['vars'].append({
                            'name': '%s_s' % name,
                            'type': 'std_logic',
                            'left': None,
                            'right': None,
                            'output_register': None,
                        })
                elif rest_parts[0] == 'vector':
                    if len(rest_parts) == 1:
                        # todo: throw error
                        pass
                    #elif rest_parts[1] != ')':
                    #    # todo: throw error
                    #    pass
                    else:
                        # test for slv()
                        if rest_parts[1] == ')':
                            left = None,
                            right = None,
                        # else, slv(left, right)
                        else:
                            inside = rest.split('(')[1].split(')')[0]
                            left = inside.split(',')[0].strip()
                            right = inside.split(',')[1].strip()
                        # note: we add `_s` to the end of all signals
                        tokens['vars'].append({
                            'name': '%s_s' % name,
                            'type': 'std_logic_vector',
                            'left': left,
                            'right': right,
                            'output_register': None,
                        })
                else:
                    # todo: throw error
                    pass
            else:
                # todo: throw error
                pass

            log(TOKENIZER, INFO, "found variable: '%s' of type '%s'" % (name, rest_parts[0])) 

        elif cmd == 'proc':
            # proc counter_decode = sync(clk, reset):
            #     if reset_count = '1' then
            #         count = zeros
            #     elsif count = count_max then
            #         count_done = '1'
            #     else
            #         count = count + '1'
            #     end if;

            # we need to get all the lines until the indent goes away
            # we're going to fix tihs at 4 spaces for indents at the moment,
            # so it's easy

            if (i+1) != len(lines):
                i += 1
                line = preprocess(i, lines[i], whitespace=True)
            else:
                # todo: throw error
                pass

            

            name = parts[1]
            equals = parts[2]
            rest = ' '.join(parts[3:])
            rest_parts = rest.replace(' ','').split('(')
            proc_type = rest_parts[0].strip()
            inside = rest.split('(')[1].split(')')[0]
            if proc_type == 'sync':
                clock = inside.split(',')[0].strip()
                reset = inside.split(',')[1].strip()
            elif proc_type == 'async':
                clock = None
                reset = inside.split(',')[0].strip()
            else:
                # todo: throw error
                pass

            proc = {}
            proc['lines'] = []
            proc['name'] = name
            proc['proc_type'] = proc_type
            proc['clock'] = clock
            proc['reset'] = {
                'name': reset,
                'assignments': [],
            }
            proc['vhdl'] = ''

            first_line = True
            while True:

                log(TOKENIZER, DEBUG, "%i  \t>%s" % (i, line['line']))

                if line['line'].strip() != '':
                    if line['line'][:4] == '    ':
                        #log(TOKENIZER, DEBUG, 'valid line. ( "%s" )' % line['line'])
                        proc['lines'].append(line)
                    else:
                        log(TOKENIZER, DEBUG, 'no indent at beginning of line. ( "%s" )' % line['line'])
                        # all done with proc
                        if first_line:
                            # todo: throw error
                            pass
                        log(TOKENIZER, DEBUG, "end of process: '%s'" % name)
                        # need to back up a line, in case this isn't the end of
                        # the file, and there is another proc below us
                        i -= 1
                        break

                if (i+1) != len(lines):
                    i += 1
                    line = preprocess(i, lines[i], whitespace=True)
                else:
                    # at end of file, must be done with proc ( hopefully )
                    break
                first_line = False

                #proc['lines'].append(line)

            tokens['procedures'].append(proc)
 
            log(TOKENIZER, INFO, "found %s process: '%s' with %i lines" % (proc_type, name, len(proc['lines'])))

        else:
            # todo: throw error
            pass
        
        i += 1

        if i == len(lines):
            eof = True
            break

    #log(TOKENIZER, DEBUG, 'tokenizing results:\n%s' % json.dumps(tokens, indent=4))

    end = time.time()

    log(TOKENIZER, INFO, 'tokenizing finished in %.6f seconds' % (end-start) )

    return tokens
        

if __name__ == '__main__':

    log(json.dumps(tokenize('counter32.chdl')), indent=4)