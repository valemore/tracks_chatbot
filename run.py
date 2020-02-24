import json
import re

from trucks_nlp import is_yes_answer, is_no_answer, sanitize_int, sanitize_float, blandify_str, get_brands, find_brand

data_file = 'data.jsonl' # Where to store the collected data
brands_file = 'brands.txt' # List of brand names

class TrucksInfo:
    'Holds complete information of a chat session'
    def __init__(self):
        self.name = None                # Client name                           String
        self.company = None             # Client company                        String
        self.n_trucks = None            # Total number of trucks                Integer
        self.brands_list = []           # List of brands among client's trucks  List[String]
        self.n_trucks_brand = None      # Number of trucks for that brand       List[Integer]
        self.brand_same_model = None    # Only one model for that brand?        List[Boolean]
        self.trucks_list = []           # List of truck models and their number List[Tuple(TruckSpec, Integer)]
        self.completeness_model_level = None
        self.completeness_brand_level = None

    def start_over(self):
        'Starts over model input after brand selection'
        self.brands_list = []
        self.n_trucks_brand = None
        self.brand_same_model = None
        self.trucks_list = []
        self.completeness_model_level = None
        self.completeness_brand_level = None

    def start_over_brand(self, i_brand):
        brand = self.brands_list[i_brand]
        self.n_trucks_brand[i_brand] = None
        self.brand_same_model[i_brand] = None
        self.trucks_list = [t in self.trucks_list if t[0].brand != brand]
        # TODO:Completeness
        
    def pretty_print(self):
        'Print out information collected in chat session'
        print("Summary of collected trucks information:")
        print("----------------------------------------")
        print(f"Name: {self.name}")
        print(f"Company: {self.company}")
        print(f"Number of trucks: {self.n_trucks}")
        print(f"Brands: {', '.join(self.brands_list)}")

        for i_brand, brand in enumerate(self.brands_list):
            print("\n")
            print(f"Information for {brand} trucks:")
            print(f"\tNumber of {brand} trucks: {self.n_trucks_brand[i_brand]}")
            print(f"\tOnly one model of {brand} trucks: {self.brand_same_model[i_brand]}")

            for t in self.trucks_list:
                if t[0].brand != brand:
                    continue
                print(f"\tInformation for {t[0].model} trucks:")
                print(f"\t\tNumber of trucks in fleet: {t[1]}")
                print(f"\t\tEngine size: {t[0].engine_size}")
                print(f"\t\tAxle Number: {t[0].axle_number}")
                print(f"\t\tWeight: {t[0].weight}")
                print(f"\t\tMax load: {t[0].max_load}")
    
    def to_json(self):
        'Serialize to json'
        trucks_list = []
        for t in self.trucks_list:
            t_dict = t[0].__dict__
            t_dict['n_trucks'] = t[1]
            trucks_list.append(t_dict)
        data_dict = {
            'name':self.name,
            'company':self.company,
            'total_trucks':self.n_trucks,
            'trucks':trucks_list
        }
        return json.dumps(data_dict)

class TruckSpec:
    'Holds specification for a truck model'
    def __init__(self):
        self.brand = None               # String
        self.brand_idx = None           # Index of brand corresponding to scheme in TrucksInfo
        self.model = None               # String
        self.engine_size = None         # Integer (Unit: litres / 1000 cm³)
        self.axle_number = None         # Integer
        self.weight = None              # Float (Unit: tons)
        self.max_load = None            # Float (Unit: tons)
    
    def __repr__(self):
        return repr(self.__dict__)

def ask_name_company(trucks_info):
    'Asks for name and company information, saves it to customer file.'
    trucks_info.name = input("Hello, what's your name? ")
    trucks_info.company = input(f"Hi {trucks_info.name}, what's the name of your company? ")

    return ask_trucks       # Next action: Ask about trucks

def ask_trucks(trucks_info):
    'Asks whether user owns trucks'
    trucks_yesno = input(f"Do you own trucks? ")
    if is_yes_answer(trucks_yesno):
        return ask_how_many  # Next action: Ask about number of trucks
    elif is_no_answer(trucks_yesno):
        trucks_info.n_trucks = 0
        print("Ok, that was easy :) Bye!")
        return None          # Next action: None (We are done)
    else:
        print("I am not sure I understood you. Let's try again.")
        return ask_trucks    # Next action: Repeat this one

def ask_how_many(trucks_info):
    'Asks how many trucks the user owns.'
    answer_how_many = input(f"How many trucks do you have? ")
    try:
        trucks_info.n_trucks = sanitize_int(answer_how_many)
        trucks_info.completeness_brand_level = 0
        if trucks_info.n_trucks == 0:
            print("Ok, that was easy :) Bye!")
            return None     # Next action: None (We are done)
        return ask_brands   # Next action: ask about brands
    except ValueError:
        print("That does not look like a number to me. Let's try again.")
        return ask_how_many # Next action: ask again about number of trucks

def ask_brands(trucks_info):
    'Asks about brands'
    brands_list = get_brands(brands_file)
    answer_brands = input(f"What brands are they? ")
    brands_matches = find_brand(answer_brands, brands_list)
    if len(brands_matches) > 0:
        print('I understand you have the following brands: ' + ', '.join(brands_matches))
        trucks_info.brands_list = brands_matches
        return ask_trucks_start # Next action: Start asking about trucks
    else:
        print("I did not recognize any brand name. Let's try again.")
        return ask_brands # Next action: Repeat this question

def ask_trucks_start(trucks_info):
    'Starts asking about trucks'
    print(f"I will now ask you about your trucks. If you want to start over from here, tell me to 'start over'")

    # Now that we know number of brands, we can initialize these
    trucks_info.n_trucks_brand = [None] * len(trucks_info.brands_list)
    trucks_info.brand_same_model = [None] * len(trucks_info.brands_list)

    return make_ask_brand_trucks(trucks_info, 0) # Next action: Ask about first truck brand

def check_for_correction(s):
    'If input s implies correction, return respective function. Otherwise return False.'
    if(blandify_str(s) == 'start over'):
        # Reset
        trucks_info.start_over()
        return ask_trucks_start

    if(blandify_str(s).startswith('correct ')):
        for i, b in enumerate(trucks_info.brands_list):
            if blandify_str(s)[8:] == b:
                # Reset
                trucks_info.start_over_brand(i)
                return make_ask_brand_trucks(trucks_info, i)
        print("I did not recognize the brand you want to correct.")
        return False
    return False

def make_ask_brand_trucks(trucks_info, i_brand):
    "Makes function for asking about i_brand-th brand"
    def ask_brand_trucks(trucks_info):
        'Asks about i_brand-th brand'
        brand = trucks_info.brands_list[i_brand]
        print(f"I will now ask you about your {brand} trucks. If you want to correct your input for your {brand} trucks, tell me 'correct {brand}'")

        trucks_brand = input(f"How many {brand} trucks do you have? ")
        # Check for correction
        if check_for_correction(trucks_brand):
            return check_for_correction(trucks_brand)

        try:
            trucks_info.n_trucks_brand[i_brand] = sanitize_int(trucks_brand)
            if not check_consistency(trucks_info):
                trucks_info.n_trucks_brand[i_brand] = None
                print(f"The numbers don't seem to add up. Let me ask you again about the {brand} trucks you have.")
                return make_ask_brand_trucks(trucks_info, i_brand) # Next action: Ask again
            else:
                return make_ask_same_model(trucks_info, i_brand) # Next action: Ask about models for that brand
        except ValueError:
            trucks_info.n_trucks_brand[i_brand] = None
            print("That does not look like a number to me. Let's try again.")
            return make_ask_brand_trucks(trucks_info, i_brand) # Next action: Ask again

    if(i_brand >= len(trucks_info.brands_list)): # We asked about all brands already
        print('Looks like I have all the info I need. Bye!')
        return None # We are done
    else:
        return ask_brand_trucks

def make_ask_same_model(trucks_info, i_brand):
    'Makes function for asking about models of i_brand-th brand'
    def ask_same_model(trucks_info):
        'Asks about models for i_brand-th brand'
        brand = trucks_info.brands_list[i_brand]

        same_model_yes_no = input(f"Are your {brand} trucks of the same model? ")
        # Check for correction
        if check_for_correction(same_model_yes_no):
            return check_for_correction(same_model_yes_no)

        if is_yes_answer(same_model_yes_no):
            trucks_info.brand_same_model[i_brand] = True
            #trucks_info.brand_n_models = 1
            #trucks_info.brand_model_list[i_brand] = [None]
            next_action = ask_brand_models(trucks_info, i_brand) # Next action: Ask about models for that brand (only 1 model)
        elif is_no_answer(same_model_yes_no):
            trucks_info.brand_same_model[i_brand] = False
            next_action = ask_brand_models(trucks_info, i_brand) # Next action: Ask about models for that brand (>1 models)
        else:
            print("I am not sure I understood you. Let's try again.")
            next_action = make_ask_same_model(trucks_info, i_brand) # Next action: Try again
        return next_action
    
    return ask_same_model

def ask_brand_models(trucks_info, i_brand):
    brand = trucks_info.brands_list[i_brand]
    if trucks_info.brand_same_model[i_brand]:
        next_model = input(f"What is the model of your {brand} trucks? ")
    else:
        next_model = input(f"What is the next model among your {brand} trucks (Answer none if you have no more models)? ")
    
    # Check for correction
    if check_for_correction(next_model):
        return check_for_correction(next_model)

    if not trucks_info.brand_same_model[i_brand] and is_no_answer(next_model):
        if check_consistency(trucks_info):
            return make_ask_brand_trucks(trucks_info, i_brand+1)        # Next action: Ask about next brand
        else:
            print("The numbers don't add up. Let's try again.")
            return ask_brand_models(trucks_info, i_brand)                # Next action: Repeat this one
    else:
        #trucks_info.brand_n_models += 1                                 # Increase counter for number of models
        return ask_model_details(trucks_info, i_brand, next_model)      # Next action: Ask about model details


def ask_model_details(trucks_info, i_brand, model_name):
    'Asks about model details for the model named model_name of the i_brand-th brand.'
    truck_spec = TruckSpec()
    truck_spec.brand = trucks_info.brands_list[i_brand]
    truck_spec.model = model_name
    
    def ask_model_engine_size():
        engine_size_input = input(f"What is the engine size for the {model_name} model [default unit: litres]? ")
        pat = re.compile(r"^\s*(\d+)\s*(l|litres|liters|litre|cc|cm³)?\s*$")
        match = pat.match(engine_size_input)
        if match is None:
            print("Engine size must given as number with optional unit - either cc or litres")
            return ask_model_engine_size
        
        try:
            engine_size = sanitize_int(match.group(1))
        except ValueError:
            print("That does not look like a number to me. Let's try again.")
            return ask_model_engine_size # Next action: ask again about number of trucks

        conversion_factor = 0.001 if match.group(2) in ["cc", "cm³"] else 1
        engine_size = engine_size * conversion_factor

        if engine_size < 1 or engine_size > 20:
            print("Engine size seems to be too high or low, please check!")
            return ask_model_engine_size

        truck_spec.engine_size = engine_size
        return None

    def ask_model_axle_number():
        try:
            axle_number = sanitize_int(input(f"How many axles does the {model_name} model have? "))
            if axle_number < 1 or axle_number > 6:
                print("Number of axles seems to be too high or low, please check!")
                return ask_model_axle_number
            else:
                truck_spec.axle_number = axle_number
                return None               # Next action: Done
        except ValueError:
            print("That does not look like a number to me. Let's try again.")
            return ask_model_axle_number # Next action: ask again about number of trucks

    def ask_model_weight():
        try:
            weight_input = input(f"How much does the {model_name} weigh (in tons)? ")
            pat = re.compile(r"^(.*)(t|tons)?\s*$")
            weight_input = pat.match(weight_input).group(1)     
            weight = sanitize_float(weight_input)
            if weight < 0 or weight > 20:
                print("Weight seems to be too high or low, please check!")
                return ask_model_weight
            else:
                truck_spec.weight = weight
                return None               # Next action: Done
        except ValueError:
            print("That does not look like a number to me. Let's try again.")
            return ask_model_weight # Next action: ask again about number of trucks

    def ask_model_max_load():
        try:
            max_load_input = input(f"What is the max load for the {model_name} model (in tons)? ")
            pat = re.compile(r"^(.*)(t|tons)?\s*$")
            max_load_input = pat.match(max_load_input).group(1)     
            max_load = sanitize_float(max_load_input)
            if max_load < 0 or max_load > 20:
                print("Max load seems to be too high or low, please check!")
                return ask_model_max_load
            else:
                truck_spec.max_load = max_load
                return None               # Next action: Done
        except ValueError:
            print("That does not look like a number to me. Let's try again.")
            return ask_model_max_load # Next action: ask again about number of trucks

    def ask_model_how_many():
        if trucks_info.brand_same_model[i_brand]:
            trucks_info.trucks_list.append((truck_spec, trucks_info.n_trucks_brand[i_brand]))
        else:
            try:
                model_how_many = sanitize_int(input(f"How many {truck_spec.brand} {model_name} trucks do you have? "))
                trucks_info.trucks_list.append((truck_spec, model_how_many))
                return None               # Next action: Done
            except ValueError:
                print("That does not look like a number to me. Let's try again.")
                return ask_model_how_many # Next action: ask again about number of trucks

    for f in [ask_model_engine_size, ask_model_axle_number, ask_model_weight, ask_model_max_load, ask_model_how_many]:
        next_action = f()
        while next_action:
            next_action = next_action()

    if trucks_info.brand_same_model[i_brand]:
        return make_ask_brand_trucks(trucks_info, i_brand+1)        # Next action: Ask about next models for next brand
    else:
        return ask_brand_models(trucks_info, i_brand)               # Next action: Ask about next model for same brand


def check_consistency(trucks_info):
    'This function checks for consistency while the data is collected. As soon as an inconsistency arises during the process, this function will return False.'

    # Count whether we have an impossible number of brands

    # Count whether we have an impossible number of models

    # Count whether total number of trucks matches sum of number of trucks per brand
    s = 0
    for i, n in enumerate(trucks_info.n_trucks_brand):
        if n is not None:
            if n < 1:
                print(f"The number of {trucks_info.brands_list[i]} trucks is zero or negative!")
                return False
            s += n
        if s > trucks_info.n_trucks:
            print("The total for the number of trucks among brands exceeds the total!")
            return False
    return True

    # Count whether number of trucks per model matches number of trucks per brand
    s = [0] * len(trucks_info.brands_list)
    for model, n in trucks_info.trucks_list:
        s[model.brand_idx] += n
        if s[model.brand_idx] > trucks_info.n_trucks_brand[model.brand_idx]:
            print(f"The total for the number of {model.brand} trucks among models exceeds the total!")
            return False
    return True    

def check_completeness_model_level(trucks_info, i_brand):
    'Checks whether we have collected all the info about models for brand given by i_brand. This check is needed because the chatbot can go back and forth between questions.'
    if trucks_info.completeness_model_level[i_brand] == trucks_info.n_trucks_brand:
        return True
    else:
        return False

def check_completeness_brand_level(trucks_info):
    'Checks whether we have collected all the info we need. This function is needed because the chatbot can go back and forth between questions.'
    if trucks_info.completeness_brand_level == trucks_info.n_trucks:
        return True
    else:
        return False

# Initialize next_action (telling chatbot what to do next) and
# trucks_info (holding trucks information until we write it to disk)
next_action = ask_name_company
trucks_info = TrucksInfo()
while next_action:
    next_action = next_action(trucks_info)

# Print info to console
trucks_info.pretty_print()

# Write info to file
with open(data_file, 'a') as f:
    f.write(trucks_info.to_json() + '\n')
