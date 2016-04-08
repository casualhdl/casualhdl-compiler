# Example file

Below is an eample `.chdl` file.  It is an 8 bit counter with a 
configurable max, counter reset, and done assertion.

    library chdl.basic
    entity counter16

    port clk = clock()
    port reset = reset()    
    port reset_count = logic()
    port max = vector(7, 0)
    port done = logic()

    var count = vector(7, 0)

    proc counter_decode = sync(clk, reset):
        reset:
            count = zeros
            done = 0

        done = 0

        if reset_count = 1:
            count = zeros
        elsif count = max:
            done = 1
        else:
            count++

# Casual HDL rules


## comments

    # this is a comment
    # everything to the right of a `#` is a comment


## top commands

This is a list of the top commands that are supported by Casual HDL:

    library <library_name>

    entity <entity_name>

    component <library_name>.<entity_name> as <instantiation_name>

    port <name> = <type>(<params>)

    var <name> = <type>(<params>)

    proc <name> = <type>(<parms>)


## Library and Entity

Each Casual HDL file must include a library and an entity command.

The library command defines what library the file should be included
in.  This is now, however, the VHDL library.  All files will be included
in the `work` library within the VHDL enviornment.

The library helps define the unique name and file name of the entity.

The entity name is the name of the Casual HDL entity, and will be used
in conjunction with the library name when using the `component` command
in other Casual HDL files.

The entity name becomes `'%s_%s' % (library, entity_name)` when compiled
into VHDL.


## port/var types

Ports are not defined as `in`, `out`, or `inout`, but just as `port`.
The pre-processor does an initiall pass of the code, and deturmins the
direction of each port.

Note: `clock()` and `reset()` ports are always inputs.

    clock()

    reset()

    logic()

    vector(<high>, <low>)


## process types

There are two different types of processes, each with two different
configurations.

A process can be syncronous ( evaluated on a clock edge ), or asyncronous
( evaluated continuously ).  Both types can take in a reset or not, with 
the syncronous type requiring a clock.

    proc <name> = async(<reset_port_name>):
        reset:
            <reset_assignments>
        <contents>

    proc <name> = async():
        <contents>

    proc <name> = sync(<clock_port_name>, <reset_port_name>):
        reset:
            <reset_assignments>
        <contents>

    proc <name> = sync(<clock_port_name>):
        <contents>


## control structure

###If, Elsif, Else statements

note: only one subject/value condition can exist within a conditional. this
means that if you need to do this ...

    c_s <= '0';
    if ( a_i = '1' and b_1 = '1' ) then 
        c_s <= '1'
    end if;

... you'll need to implement that as this within Casual HDL:

    c = 0
    if a = 1:
        if b = 1:
            c = 1

This limitation is due to the Casual HDL processor, and will more than likely 
be changed in the future.  Note that the nested if statements produce the same
RTL and synthesis result out of the Xilinx Vivado tools.  So although being 
more verbose, does not change the output product.

*if*

    if <condition>:
        <contents>

    if <condition>:
        <contents>
    else:
        <contents>

    if <condition>:
        <contents>
    elsif <condition>:
        <contents>
    else:
        <contents>


###Finite State Machines

Finite State Machines (FSM) in VHDL are defined as such ...

    architecture behavioral of <thing> is

        type state_type is (
            idle, 
            wait_for_thing,
            do_thing,
            clean_up_thing,
            finished
        );
        signal state : state_type := idle;

    begin

        process( clk_i )
        begin
            if ( rising_edge( clk_i ) ) then
                if ( reset_i = '1' ) then
                    state <= idle;
                else
                    state <= state;

                    case state is
                        when idle =>
                            --
                        when wait_for_thing =>
                            --
                        when do_thing =>
                            --
                        when clean_up_thing =>
                            --
                        when finished =>
                            --
                        when others => 
                            null;
                    end case;
                end if;
            end if;
        end process;

    end behavioral;

with casual HDL, there is no need to define the states beforehand. The
same state machine as above looks like ...

    proc state_machine = sync(clk, reset):
        reset:
            state = idle
        fsm:
            idle:
                #
            wait_for_thing:
                #
            do_thing:
                #
            clean_up_thing:
                #
            finished:
                #

This **greatly** reduces the amount of code that is needed, and keeps things
simple and concise

*fsm*

    fsm <name>:
        <state_0>:
            <contents>
        <state_1>:
            <contents>
        <state_2>:
            <contents>

### Case Statement

A case statement is a more eligant version of the `if, elsif, else` control 
structure.

*case*

    case <name>:
        <value_0>:
            <contents>
        <value_1>:
            <contents>
        <value_2>:
            <contents>
        others:
            <contents>