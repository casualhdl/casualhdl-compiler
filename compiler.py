
import json

from tokenizer import tokenize

def read_template():
	with open('vhdl.template', 'r') as f:
		template = f.read()
	return template

def parse_procedures(tokens):
	'''
	This the meaty part of the compiler.

	We need to deturmine the direction of all of the ports used
	in the procedures in the entity.  Next, we'll need to create
	new "vars" ( signals ) for the outputs, so they're all 
	registered.
	'''

	return tokens


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

def compile(filename, verbose=False):

	# tokenize the file
	tokens = tokenize(filename, verbose)

	# generate the entity name based on the library
	entity_name_vhdl = '%s_%s' % (tokens['library'].replace('.', '_'), tokens['entity'])

	# based on the contents of the procedures in the entity,
	# we need to generate assignments and port directions.
	tokens = parse_procedures(tokens)

	# generate ports vhdl
	ports_vhdl = build_ports_vhdl(tokens['ports'])

	# generate procedures
	procedures_vhdl = build_procesure_vhdl(tokens['procedures'])

	# read in the template for replacement
	template = read_template()


	template = template.replace('<<entity_name>>', entity_name_vhdl)

	# we don't currently support generics
	template = template.replace('<<generics>>', '--    generic (\n--        \n--    );')

	template = template.replace('<<ports>>', ports_vhdl)

	return template

if __name__ == '__main__':

	#print(json.dumps(compile('counter32.chdl', verbose=True), indent=4))

	print(compile('counter32.chdl', verbose=True))