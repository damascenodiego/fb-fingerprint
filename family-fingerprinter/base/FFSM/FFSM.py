import networkx as nx

def unify_features(current_variants : set[str], new_variants : set[str]) -> set[str]:
    if current_variants == set():
        return new_variants
    elif new_variants == set():
        return current_variants
    
    equal_variants = current_variants.intersection(new_variants)
    return equal_variants

class ConditionalState():
    
    def __init__(self, state_id : str, features : set[str]):
        self.state_id = state_id
        self.features = features

    def __eq__(self, other) -> bool:
        if isinstance(other,ConditionalState):
            return self.state_id == other.state_id
        return False
    
    def __str__(self) -> str:
        return "(" + self.state_id + ", " + self.features.__str__() + ")"

class ConditionalTransition():

    def __init__(self, from_state: ConditionalState, to_state: ConditionalState, input : str, output : str, features : set[str]):
        self.from_state = from_state
        self.to_state = to_state
        self.input = input
        self.output = output
        self.features = features
    
    def __str__(self) -> str:
        return "(" + self.from_state.__str__() + ", " + self.to_state.__str__() + ", " + self.input + "/" + self.output + ", " + self.features.__str__() + ")"
        

class FFSM():
    
    def __init__(self, transitions: list[ConditionalTransition], initial_state: ConditionalState, features : set[str]):
        self.transitions = transitions
        self.initial_state = initial_state
        
        self.states : list[ConditionalState] = []
        self.features = features
        self.alphabet = set()
        for transition in self.transitions:
            if transition.from_state not in self.states:
                self.states.append(transition.from_state)
            if transition.to_state not in self.states:
                self.states.append(transition.to_state)  
            self.alphabet.add(transition.input)
        self.reset_to_initial_state()      

    @classmethod
    def from_file(self, file: str) -> 'FFSM':
        ffsm = nx.drawing.nx_agraph.read_dot(file)

        all_features = set(ffsm.graph["configurations"].split("|"))

        states = {}
        for state in ffsm.nodes.data():
            features = state[1]["feature"].split("|")
            if features[0] == "True":
                features = all_features
            states[state[0]] = ConditionalState(state[0],set(features))
 
        initial_state = None
        transitions = []
        for transition in ffsm.edges.data():
            if transition[0] == "__start0":
                initial_state = states[transition[1]]
                continue
            in_output = transition[2]["label"].split("/")
            features = set(transition[2]["feature"].split("|"))
            transitions.append(ConditionalTransition(states[transition[0]], states[transition[1]], in_output[0].replace(" ", ""), in_output[1].replace(" ", ""),features))
        
        
        
        return FFSM(transitions, initial_state, all_features)
        
    def __str__(self) -> str:
        output = ""
        for transition in self.transitions:
            output = output + transition.__str__()
        return output

    def step(self, input : str, features_in : set[str] = set()) -> list[(str, set[str])]:
        new_current_states = []
        outputs = []
        for current_state, feature_config in self.current_states:
            features = unify_features(feature_config, features_in)
            if len(features) > 0 or (features == [] and feature_config == []):
                transitions = self.outgoing_transitions_of(current_state)
                for transition in transitions:
                    feature_config_transition = unify_features(features,transition.features)
                    if transition.input == input and len(feature_config_transition) > 0:
                        new_current_states.append((transition.to_state, feature_config_transition))
                        outputs.append((transition.output, feature_config_transition))
        if new_current_states == []:
            raise Exception("Invalid input: ", input, " given the features: ", features)
        else:
            self.current_states = new_current_states
        return outputs

    def make_input_complete(self) -> None:
        for state in self.states:
            input_dict = {}
            for input in self.alphabet:
                input_dict[input] = set()
            for edge in self.outgoing_transitions_of(state):
                input_dict[edge.input] = input_dict[edge.input].union(edge.features)
            
            for input, features in input_dict.items():
                feature_diff = state.features.difference(features)
                if len(feature_diff) > 0:
                    self.transitions.append(ConditionalTransition(state,state,input,'epsilon',feature_diff))

    def reset_when_sink(self):
        for feature in self.features:
            for state in self.states:
                if feature in state.features:
                    is_sink = True
                    for edge in self.outgoing_transitions_of(state):
                        if feature in edge.features and edge.to_state != state:
                            is_sink = False
                            break
                    if is_sink:
                        self.alphabet.add('RESET-SYS')
                        self.transitions.append(ConditionalTransition(state,self.initial_state, 'RESET-SYS', 'epsilon', {feature}))



    def reset_to_initial_state(self) -> None:
        self.current_states = [(self.initial_state, self.features)]

    def incoming_transitions_of(self, state : ConditionalState) -> list[ConditionalTransition]:
        incoming_transitions = []
        for transition in self.transitions:
            if transition.to_state == state:
                incoming_transitions.append(transition)
        return incoming_transitions

    def outgoing_transitions_of(self, state : ConditionalState) -> list[ConditionalTransition]:
        outgoing_transitions = []
        for transition in self.transitions:
            if transition.from_state == state:
                outgoing_transitions.append(transition)
        return outgoing_transitions