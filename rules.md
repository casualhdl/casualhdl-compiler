
## comments

    # this is a comment
    # everything to the right of a `#` is a comment

## top commands

    library <library_name>

    entity <entity_name>

    component <library_name>.<entity_name> as <instantiation_name>

    port <name> = <type>(<params>)

    var <name> = <type>(<params>)

    proc <name> = <type>(<parms>)


## port/var types

    clock()

    reset()

    bit()

    vector(<high>, <low>)

## process types

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

*fsm*

    fsm <name>:
        <state_0>:
            <contents>
        <state_1>:
            <contents>
        <state_2>:
            <contents>

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