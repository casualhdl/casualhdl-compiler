# casualhdl-compiler
CasualHDL compiler

To run the compiler, you'll need python3.  From the promt try:

    > python3 compiler.py ./lib/chdl/basic/counter32.chdl
    
Here is an example cadual hdl file:

    library chdl.basic
    entity counter32

    port clk = clock()
    port reset = reset()    
    port reset_count = bit()
    port max = vector(31, 0)
    port done = bit()

    var count = vector(31, 0)

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
            
Here is what the output looks like:

    library ieee;
    use ieee.std_logic_1164.all;
    use ieee.numeric_std.all;
    use ieee.std_logic_unsigned.all;

    entity chdl_basic_counter32 is
    --    generic (
    --        
    --    );
        port (

            -- clock
            clk_i : in std_logic;

            -- reset
            reset_i : in std_logic;

            -- interface ports
            reset_count_i : in std_logic;
            max_i : in std_logic_vector(31 downto 0);
            done_o : out std_logic

        );
    end chdl_basic_counter32;

    architecture behavioral of chdl_basic_counter32 is

        -- components


        -- signals
        signal count_s : std_logic_vector(31 downto 0);
        signal done_s : std_logic;


    begin

        --
        -- output port assignments
        --
        
        done_o <= done_s;


        --
        -- instantiations
        --



        --
        -- procedures
        --

        counter_decode: process( clk_i )
        begin
            if ( rising_edge( clk_i ) ) then
                if ( reset_i = '1' ) then

                    -- reset values
                    count_s <= "00000000000000000000000000000000";
                    done_s <= '0';

                else

                    -- derived defaults
                    count_s <= count_s;

                    -- process logic
                    done_s <= '0';
                    if ( reset_count_i = '1' ) then
                        count_s <= "00000000000000000000000000000000";
                    elsif ( count_s = max_i ) then
                        done_s <= '1';
                    else
                        count_s <= count_s + '1';
                    end if;

                end if;
            end if;
        end process;

    end behavioral; 
    
Check out more of the casual hdl files available in the default library in the ./libs/chdl folder.
