
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

def build_procesure_vhdl(tokens):

	return ''

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
	procedures_vhdl = build_procesure_vhdl(tokens)

	# read in the template for replacement
	template = read_template()


	template = template.replace('<<entity_name>>', entity_name_vhdl)

	# we don't currently support generics
	template = template.replace('<<generics>>', '--    generic (\n--        \n--    );')

	template = template.replace('<<ports>>', ports_vhdl)

	return template

if __name__ == '__main__':

	#print(json.dumps(compile('counter32.chdl', verbose=True), indent=4))

	print(compile('pwm.chdl', verbose=True))