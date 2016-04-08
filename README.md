# casualhdl-compiler
CasualHDL compiler

CasualHDL was created to find a happy middle ground between verbosity and robustness when 
writing HDL code.  CasualHDL handles a lot of the frustrating aspects of writing VHDL code
while still producing an output product that is human readable and robust.

Here is the CasualHDL code for a simple 32 bit counter with a done and reset interface:

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
            count = 0
            done = 0
        done = 0
        if reset_count = 1:
            count = 0
        elsif count = max:
            done = 1
        else:
            count++

Here is the VHDL that it creates.  Note the derived default for `count_s`.

    library ieee;
    use ieee.std_logic_1164.all;
    use ieee.numeric_std.all;
    use ieee.std_logic_unsigned.all;

    entity chdl_basic_counter32 is
        port (
            clk_i : in std_logic;
            reset_i : in std_logic;
            reset_count_i : in std_logic;
            max_i : in std_logic_vector(31 downto 0);
            done_o : out std_logic
        );
    end chdl_basic_counter32;

    architecture behavioral of chdl_basic_counter32 is
        signal count_s : std_logic_vector(31 downto 0);
        signal done_s : std_logic;
    begin

        done_o <= done_s;
        
        counter_decode: process( clk_i )
        begin
            if ( rising_edge( clk_i ) ) then
                if ( reset_i = '1' ) then
                    count_s <= "00000000000000000000000000000000";
                    done_s <= '0';
                else
                    count_s <= count_s;
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
    
