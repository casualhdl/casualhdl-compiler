
library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use ieee.std_logic_unsigned.all;

entity counter32 is
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
end counter32;

architecture behavioral of counter32 is

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
    process( clk_i )
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