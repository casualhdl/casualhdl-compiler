
import json

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

def preprocess(line, whitespace=False):
    # remove comments and whitespace
    line = line.split('#')[0]
    if not whitespace:
        line = line.strip()
    return line

def tokenize(filename, verbose=False):
    # read file
    lines = read_lines(filename)
    # setup response structure
    tokens = {}
    tokens['includes'] = []
    tokens['ports'] = {}
    tokens['ports']['clocks'] = []
    tokens['ports']['resets'] = []
    tokens['ports']['signals'] = []
    tokens['vars'] = []
    tokens['procedures'] = []
    # do first pass of file, and tokenize
    eof = False
    i = 0;
    while not eof:
        
        line = preprocess(lines[i])

        if verbose:
            print("Line %i  \t%s" % (i, line))

        if '\t' in line:
            # todo: throw error
            pass

        parts = line.split(' ')
        cmd = parts[0]
        
        if cmd == 'library':
            # library chdl.basic
            if len(parts) == 2:
                tokens['library'] = parts[1]
            else:
                # todo: throw error
                pass
        elif cmd == 'entity':
            # entity counter32
            if len(parts) == 2:
                tokens['entity'] = parts[1]
            else:
                # todo: throw error
                pass
        elif cmd == 'port':
            # port pulse = logic()
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
                        tokens['ports']['clocks'].append(name)
                elif rest_parts[0] == 'reset':
                    if len(rest_parts) == 1:
                        # todo: throw error
                        pass
                    elif rest_parts[1] != ')':
                        # todo: throw error
                        pass
                    else:
                        tokens['ports']['resets'].append(name)
                elif rest_parts[0] == 'logic':
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
                            norange = True
                            left = None
                            right = None
                        # else, slv(left, right)
                        else:
                            norange = False
                            inside = rest.split('(')[1].split(')')[0]
                            left = inside.split(',')[0].strip()
                            right = inside.split(',')[1].strip()
                        tokens['ports']['signals'].append({
                            'name': name,
                            'type': 'std_logic_vector',
                            'norange': norange,
                            'left': left,
                            'right': right,
                        })
                else:
                    # todo: throw error
                    pass
            else:
                # todo: throw error
                pass
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
        elif cmd == 'var':
            # var counter = slv(31, 0)
            if len(parts) >= 4:
                name = parts[1]
                equals = parts[2]
                rest = ' '.join(parts[3:])
                rest_parts = rest.replace(' ','').split('(')
                if rest_parts[0] == 'sl':
                    if len(rest_parts) == 1:
                        # todo: throw error
                        pass
                    elif rest_parts[1] != ')':
                        # todo: throw error
                        pass
                    else:
                        tokens['vars'].append({
                            'name': name,
                            'type': 'std_logic',
                        })
                elif rest_parts[0] == 'slv':
                    if len(rest_parts) == 1:
                        # todo: throw error
                        pass
                    #elif rest_parts[1] != ')':
                    #    # todo: throw error
                    #    pass
                    else:
                        # test for slv()
                        if rest_parts[1] == ')':
                            norange = True
                            left = None,
                            right = None,
                        # else, slv(left, right)
                        else:
                            norange = False
                            inside = rest.split('(')[1].split(')')[0]
                            left = inside.split(',')[0].strip()
                            right = inside.split(',')[1].strip()
                        tokens['vars'].append({
                            'name': name,
                            'type': 'std_logic_vector',
                            'norange': norange ,
                            'left': left,
                            'right': right,
                        })
                else:
                    # todo: throw error
                    pass
            else:
                # todo: throw error
                pass
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
                line = preprocess(lines[i], whitespace=True)
            else:
                # todo: throw error
                pass

            proc = {}
            proc['lines'] = []

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
                reset = inside.split(',')[0].strip()
            else:
                # todo: throw error
                pass

            #if verbose:
            #    print("Found Process: %s" % name)

            proc['name'] = name
            proc['proc_type'] = proc_type
            proc['clock'] = clock
            proc['reset'] = reset

            first_line = True
            while True:
                if verbose:
                    print("Line %i  \t%s" % (i, line))
                #print(i, line)
                if line[:4] == '    ':
                    proc['lines'].append(line[4:])
                else:
                    # all done with proc
                    if first_line:
                        # todo: throw error
                        pass
                    break
                if (i+1) != len(lines):
                    i += 1
                    line = preprocess(lines[i], whitespace=True)
                else:
                    # at end of file, must be done with proc ( hopefully )
                    break
                first_line = False
            tokens['procedures'].append(proc)

        else:
            # todo: throw error
            pass
        
        i += 1

        if i == len(lines):
            eof = True
            break

    return tokens
        

#if __name__ == '__main__':
#
#    print(json.dumps(tokenize(read_lines('counter32.chdl'), verbose=True), indent=4))