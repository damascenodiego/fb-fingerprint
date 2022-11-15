import getopt
import sys
from datetime import datetime
from aalpy.SULs.AutomataSUL import MealySUL
from aalpy.utils.FileHandler import load_automaton_from_file
from aalpy.automata import MealyMachine

from base.FFSM.FFSM import FFSM
from base.fingerprint.passive.passive import trace_fingerprinting
from base.fingerprint.passive.filehandler import read_traces
from base.fingerprint.active.active import Simulator
from base.fingerprint.active.CADS import CADS
from base.fingerprint.active.CPDS import CPDS
from base.fingerprint.active.ConfigurationDistinguishingSequence import ConfigurationDistinguishingSequence


def reset_when_sink(fsm : MealyMachine):
    for state in fsm.states:
        is_sink = True
        for out_state in state.transitions.values():
            if out_state.state_id != state.state_id:
                is_sink = False
                break
        if is_sink:
            state.transitions['RESET-SYS'] = fsm.initial_state
            state.output_fun['RESET-SYS'] = 'epsilon'




def main():
    active_mode = None
    ffsm_file = None
    file = None
    adaptive = None
    sequence_file = None
    try:
        arguments = getopt.getopt(sys.argv[1:],"p:f:a:",["passive=", "FFSM=", "active=", "preset", "adaptive", "sequence="])
        for current_arg, current_val in arguments[0]:
            if current_arg in ("-p", "--passive"):
                if active_mode == None:
                    active_mode = False
                    file = current_val
                else:
                    raise Exception("Already in active mode, please select active OR passive mode")
            elif current_arg in ("-f", "--FFSM"):
                ffsm_file = current_val
            elif current_arg in ("--adaptive"):
                adaptive = True
            elif current_arg in ("--preset"):
                adaptive = False
            elif current_arg in ("--sequence"):
                sequence_file = current_val
            elif current_arg in ("-a", "--active"):
                if active_mode == None:
                    active_mode = True
                    file = current_val
                else:
                   raise Exception("Already in passive mode, please select active OR passive mode")       
    except getopt.error as err:
        print(str(err))
        return
    if ffsm_file == None and sequence_file == None:
        print("Please give a FFSM reference model or a sequence model")
        return
    elif active_mode == False:
        ffsm = FFSM.from_file(ffsm_file)
        traces = read_traces(file)
        possible_variants = trace_fingerprinting(ffsm, traces)
        print("variant: ", possible_variants)
    elif active_mode == True and adaptive is not None:
        ds : ConfigurationDistinguishingSequence = None
        missing_alphabet : set = None
        fsm = load_automaton_from_file(file,'mealy')
        reset_when_sink(fsm)
        if ffsm_file is not None:
            ffsm = FFSM.from_file(ffsm_file)
            ffsm.reset_when_sink()

            missing_alphabet = set(ffsm.alphabet).difference(set(fsm.get_input_alphabet()))

            ffsm.make_input_complete()
            begin_time = datetime.now()
            if adaptive:
                ds = CADS(ffsm=ffsm)
            else:
                ds = CPDS(ffsm=ffsm)
            end_time = datetime.now()
            diff_time = (end_time - begin_time).total_seconds()
            print("calculation costs: ", diff_time, " seconds")
        else:
            if adaptive:
                ds = CADS.from_file(sequence_file)
            else:
                ds = CPDS.from_file(sequence_file)
            inputs = set()
            for node in ds.seperating_sequence.nodes.data():
                if ds.seperating_sequence.out_degree(node[0]) > 0:
                    inputs.add(node[1]["label"])
            missing_alphabet = inputs.difference(set(fsm.get_input_alphabet()))
                

        for a in missing_alphabet: #for the non exisiting alphabet add a self loop on the initial state, make_input_complete() will do the rest
            fsm.initial_state.transitions[a] = fsm.initial_state
            fsm.initial_state.output_fun[a] = 'epsilon'
        
        fsm.make_input_complete()

        sul_fsm = MealySUL(fsm)
        sim = Simulator(ds)
        possible_variants = sim.fingerprint_system(sul_fsm)
        print("variant: ", possible_variants)



if __name__ == "__main__":
    main()