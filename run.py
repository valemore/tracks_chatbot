import json
import os
import re
import time

from trucks_nlp import is_yes_answer, is_no_answer, sanitize_int, sanitize_float, sanitize_str, blandify_str, get_brands, find_brand

data_file = 'data.jsonl' # Where to store the collected data
brands_file = 'brands.txt' # List of brand names

# File for chat logs
current_time = time.strftime("%Y-%m-%d_%H-%M-%S")
log_file_base = f'{current_time}.log'
log_file, suffix = log_file_base, 1
while os.path.exists(log_file):
    log_file = f'{log_file_base}_{suffix}'
    suffix += 1

class TrucksInfo:
    'Holds complete information of a chat session'
    def __init__(self):
        self.name = None                # Client name                           String
        self.company = None             # Client company                        String
        self.n_trucks = None            # Total number of trucks                Integer
        self.brands_list = []           # List of brands among client's trucks  List[String]
        self.n_trucks_brand = None      # Number of trucks for that brand       List[Integer]
        self.brand_same_model = None    # Only one model for that brand?        List[Boolean]
        self.brand_models = [[]]        # List of truck models for that brand   List[String]
        self.trucks_list = []           # List of truck models and their number List[Tuple(TruckSpec, Integer)]
        self.completeness = None        # Counts number of trucks for brands    List[Integer]

    def start_over(self):
        'Starts over input after brand selection'
        self.n_trucks_brand = [None] * len(self.brands_list)
        self.brand_same_model = [None] * len(self.brands_list)
        self.brand_models = [[]] * len(self.brands_list)
        self.trucks_list = []
        self.completeness = [0] * len(self.brands_list)

    def start_over_brand(self, i_brand):
        'Starts over input for specific brand'
        brand = self.brands_list[i_brand]
        self.n_trucks_brand[i_brand] = None
        self.brand_same_model[i_brand] = None
        self.brand_models[i_brand] = []
        self.trucks_list = [t for t in self.trucks_list if t[0].brand != brand]
        self.completeness[i_brand] = 0
        
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

# BOT INPUT AND OUTPUT

def bot_input(outfile, prompt_str):
    'Wrapper around input for logging to outfile'
    with open(outfile, 'a') as f:
        f.write('BOT: ' + prompt_str + '\n')
        input_str = input(prompt_str)
        f.write('USER: ' + input_str + '\n')
    return input_str

def bot_output(outfile, output_str):
    'Wrapper around print for logging to outfile'
    print(output_str)
    with open(outfile, 'a') as f:
        f.write('BOT: ' + output_str + '\n')

# BOT DIALOGUE FUNCTIONS
# All dialogue functions save data in trucks_info
# Every dialogue function returns the function where the conversation flows next

def ask_name(trucks_info):
    'Asks for name'
    name = bot_input(log_file, "Hello, what's your name? ")
    try:
        name = sanitize_str(name)
    except ValueError:
        bot_output(log_file, "You can tell me your name, we are GDPR-compliant.")
        return ask_name

    trucks_info.name = name
    return ask_company # Next action: Ask about company

def ask_company(trucks_info):
    'Asks for company name'
    company = bot_input(log_file, f"Hi {trucks_info.name}, what's the name of your company? ")
    try:
        company = sanitize_str(company)
    except ValueError:
        bot_output(log_file, "You can tell me your company name, we are GDPR-compliant.")
        return ask_company

    trucks_info.company = company
    return ask_trucks # Next action: Ask about trucks


def ask_trucks(trucks_info):
    'Asks whether user owns trucks'
    trucks_yesno = bot_input(log_file, f"Do you own trucks? ")
    if is_yes_answer(trucks_yesno):
        return ask_how_many  # Next action: Ask about number of trucks
    elif is_no_answer(trucks_yesno):
        trucks_info.n_trucks = 0
        bot_output(log_file, "Ok, that was easy :) Bye!")
        return None          # Next action: None (We are done)
    else:
        bot_output(log_file, "I am not sure I understood you. Let's try again.")
        return ask_trucks    # Next action: Repeat this one

def ask_how_many(trucks_info):
    'Asks how many trucks the user owns.'
    answer_how_many = bot_input(log_file, f"How many trucks do you have? ")

    # Sanitize integer input (Total number of trucks)
    try:
        n_trucks = sanitize_int(answer_how_many)
    except ValueError:
        bot_output(log_file, "That does not look like a number to me. Let's try again.")
        return ask_how_many # Next action: ask again about number of trucks

    if n_trucks < 0:
        bot_output(log_file, "Nice try, but I will not fall for negative trucks!")
        return ask_how_many # Next action: ask again about number of trucks

    trucks_info.n_trucks = n_trucks

    if trucks_info.n_trucks == 0:
        bot_output(log_file, "Ok, that was easy :) Bye!")
        return None     # Next action: None (We are done)
    return ask_brands   # Next action: ask about brands

def ask_brands(trucks_info):
    'Asks about brands'
    brands_list = get_brands(brands_file)
    prompt = "What brands are they? " if trucks_info.n_trucks > 1 else "What brand is your truck? "
    answer_brands = bot_input(log_file, prompt)
    brands_matches = find_brand(answer_brands, brands_list)
    if len(brands_matches) > 0:
        if len(brands_matches) > trucks_info.n_trucks:
            bot_output(log_file, "You seem to have more brands than trucks! Let's try again!")
            return ask_how_many
            
        bot_output(log_file, 'I understand you have the following brands: ' + ', '.join(brands_matches))
        trucks_info.brands_list = brands_matches
        return ask_trucks_start # Next action: Start asking about trucks
    else:
        bot_output(log_file, "I did not recognize any brand name. Let's try again.")
        return ask_brands # Next action: Repeat this question

def check_for_correction(trucks_info, input_str):
    "If input is either 'start over' or 'correct <brand>', reset and return respective function. Otherwise return False."
    if(blandify_str(input_str) == 'start over'):
        # Reset
        trucks_info.start_over()
        return ask_trucks_start

    if(blandify_str(input_str).startswith('correct ')):
        for i, b in enumerate(trucks_info.brands_list):
            if blandify_str(input_str)[8:] == blandify_str(b):
                # Reset
                trucks_info.start_over_brand(i)
                return make_ask_brand_trucks(trucks_info, i)
        bot_output(log_file, "I did not recognize the brand you want to correct.")
        return False
    return False

def ask_trucks_start(trucks_info):
    'Starts asking about trucks'
    bot_output(log_file, f"I will now ask you about your trucks. If you want to start over from here, tell me to 'start over'")

    # (Re)set members
    trucks_info.start_over()

    return make_ask_brand_trucks(trucks_info, 0) # Next action: Ask about first truck brand

def make_ask_brand_trucks(trucks_info, i_brand):
    "Makes function for asking about i_brand-th brand"
    def ask_brand_trucks(trucks_info):
        'Asks about i_brand-th brand'
        brand = trucks_info.brands_list[i_brand]

        # (Re)set members
        trucks_info.start_over_brand(i_brand)

        bot_output(log_file, f"I will now ask you about your {brand} trucks. If you want to correct your input for your {brand} trucks, tell me 'correct {brand}'")

        if(len(trucks_info.brands_list) == 1): # We don't need to ask if we only have one brand
            if trucks_info.n_trucks > 1:
                bot_output(log_file, f"It seems that all your {trucks_info.n_trucks} trucks are {brand} trucks.")
            trucks_info.n_trucks_brand[i_brand] = trucks_info.n_trucks
        else:
            trucks_brand = bot_input(log_file, f"How many {brand} trucks do you have? ")

            # Jump back if requested
            correction_maybe = check_for_correction(trucks_info, trucks_brand)
            if correction_maybe:
                return correction_maybe

            # Sanitizing for integer input (Number of trucks per brand)
            try:
                trucks_info.n_trucks_brand[i_brand] = sanitize_int(trucks_brand)
            except ValueError:
                #trucks_info.n_trucks_brand[i_brand] = None
                bot_output(log_file, "That does not look like a number to me. Let's try again.")
                return make_ask_brand_trucks(trucks_info, i_brand) # Next action: Ask again

            if not check_consistency(trucks_info):
                trucks_info.n_trucks_brand[i_brand] = None
                bot_output(log_file, f"The numbers don't seem to add up. Let me ask you again about the {brand} trucks you have.")
                return make_ask_brand_trucks(trucks_info, i_brand) # Next action: Ask again

        return make_ask_same_model(trucks_info, i_brand) # Next action: Ask about models for that brand

    if(i_brand >= len(trucks_info.brands_list)): # We asked about all brands already
        bot_output(log_file, 'Looks like I have all the info I need. Bye!')
        return None # We are done

    if(check_completeness(trucks_info, i_brand)): # We already have info for this brand
        if not trucks_info.brand_same_model[i_brand] and len(trucks_info.brand_models[i_brand]) == 1: # Notify user and change brand_same_model if user changed his mind
            bot_output(log_file, f"Before you told me you have more than one model. No problem, it's ok to change your mind.")
            trucks_info.brand_same_model[i_brand] = True
        return make_ask_brand_trucks(trucks_info, i_brand+1)  # Next action: Ask about next brand
    
    return ask_brand_trucks

def make_ask_same_model(trucks_info, i_brand):
    'Makes function for asking about models of i_brand-th brand'
    def ask_same_model(trucks_info):
        'Asks about models for i_brand-th brand'
        brand = trucks_info.brands_list[i_brand]

        if trucks_info.n_trucks_brand[i_brand] != 1: # If there is more than one truck, ask if they are all the same model
            same_model_yes_no = bot_input(log_file, f"Are your {brand} trucks of the same model? ")

            # Jump back if requested
            correction_maybe = check_for_correction(trucks_info, same_model_yes_no)
            if correction_maybe:
                return correction_maybe

            if is_yes_answer(same_model_yes_no): # Only one model for this brand
                trucks_info.brand_same_model[i_brand] = True
                return ask_brand_models(trucks_info, i_brand) # Next action: Ask about models for that brand
            elif is_no_answer(same_model_yes_no): # More than one model for this brand
                trucks_info.brand_same_model[i_brand] = False
                return ask_brand_models(trucks_info, i_brand) # Next action: Ask about models for that brand
            else:
                bot_output(log_file, "I am not sure I understood you. Let's try again.")
                return make_ask_same_model(trucks_info, i_brand) # Next action: Try again
        else: # For this brand there is only one truck and one truck model
            trucks_info.brand_same_model[i_brand] = True
            return ask_brand_models(trucks_info, i_brand) # Next action: Ask about models for that brand
    
    return ask_same_model

def ask_brand_models(trucks_info, i_brand):
    'Asks about the model for a brand'
    brand = trucks_info.brands_list[i_brand]
    if trucks_info.brand_same_model[i_brand]: # Only one model
        next_model = bot_input(log_file, f"What is the model of your {brand} trucks? ")
        try:
            next_model = sanitize_str(next_model)
        except ValueError:
            bot_output(log_file, "The model name can't be blank!")
            return ask_brand_models(trucks_info, i_brand)

    else: # More than one model
        next_model = bot_input(log_file, f"What is model #{len(trucks_info.brand_models[i_brand])+1} among your {brand} trucks (Answer none if you have no more models)? ")
        try:
            next_model = sanitize_str(next_model)
        except ValueError:
            bot_output(log_file, "The model name can't be blank!")
            return ask_brand_models(trucks_info, i_brand)
        if next_model in trucks_info.brand_models[i_brand]: # Model was already given before
            bot_output(log_file, f"It looks like you already told me about your {brand} {next_model} model trucks! Let's try again.")
            return ask_brand_models(trucks_info, i_brand)
    
    # Jump back if requested
    correction_maybe = check_for_correction(trucks_info, next_model)
    if correction_maybe:
        return correction_maybe

    if not trucks_info.brand_same_model[i_brand] and is_no_answer(next_model): # User give 'none' answer - only allowed if more than one model
        if check_consistency(trucks_info): # Check for consistency
            if check_completeness(trucks_info, i_brand): # Check if we have all the trucks for this brand
                if len(trucks_info.brand_models[i_brand]) == 1: # We are fine, but notify user and change brand_same_model if user changed his mind
                    bot_output(log_file, f"Before you told me you have more than one model. No problem, it's ok to change your mind.")
                    trucks_info.brand_same_model[i_brand] = True
                return make_ask_brand_trucks(trucks_info, i_brand+1) # Next action: Ask about next brand
            else: # We are consistent, but there are still trucks outstanding
                bot_output(log_file, f"We are missing information for brand {trucks_info.brands_list[i_brand]}!")
        # We are inconsistent or incomplete (or both)
        bot_output(log_file, "The numbers don't add up. Let's try again.")
        return ask_brand_models(trucks_info, i_brand) # Next action: Repeat this one
    
    trucks_info.brand_models[i_brand].append(next_model)            # Add model to list of models for next prompt
    return ask_model_details(trucks_info, i_brand, next_model)      # Next action: Ask about model details

def ask_model_details(trucks_info, i_brand, model_name):
    'Asks about model details for the model named model_name of the i_brand-th brand.'
    truck_spec = TruckSpec()
    truck_spec.brand = trucks_info.brands_list[i_brand]
    truck_spec.model = model_name
    truck_spec.brand_idx = i_brand
    
    def ask_model_engine_size():
        'Asks about engine size'
        engine_size_input = bot_input(log_file, f"What is the engine size for the {model_name} model [default unit: litres]? ")

        # Jump back if requested
        correction_maybe = check_for_correction(trucks_info, engine_size_input)
        if correction_maybe:
            return correction_maybe

        # Looking for a float with optional unit - either litres or cubic centimeters
        pat = re.compile(r"^(.*?)(l|litres|liters|litre|cc|cm³)?\s*$")
        match = pat.match(engine_size_input)
        if match is None:
            bot_output(log_file, "Engine size must given as number with optional unit - either cc or litres")
            return ask_model_engine_size
        
        try:
            engine_size = sanitize_float(match.group(1))
        except ValueError:
            bot_output(log_file, "That does not look like a number to me. Let's try again.")
            return ask_model_engine_size # Next action: ask again about engine size

        # Convert if necessary
        conversion_factor = 0.001 if match.group(2) in ["cc", "cm³"] else 1
        engine_size = engine_size * conversion_factor

        if engine_size < 1 or engine_size > 20:
            bot_output(log_file, "Engine size seems to be too high or low, please check!")
            return ask_model_engine_size # Next action: ask again about engine size

        truck_spec.engine_size = engine_size
        return None # Next action: Done asking about this.

    def ask_model_axle_number():
        'Ask about number of axles'
        axle_numer_input = bot_input(log_file, f"How many axles does the {model_name} model have? ")

        # Jump back if requested
        correction_maybe = check_for_correction(trucks_info, axle_numer_input)
        if correction_maybe:
            return correction_maybe

        try:
            axle_number = sanitize_int(axle_numer_input)
        except ValueError:
            bot_output(log_file, "That does not look like a number to me. Let's try again.")
            return ask_model_axle_number # Next action: ask again about number of axles
        
        if axle_number < 1 or axle_number > 6:
            bot_output(log_file, "Number of axles seems to be too high or low, please check!")
            return ask_model_axle_number # Next action: ask again about number of axles
        else:
            truck_spec.axle_number = axle_number
            return None # Next action: Done

    def ask_model_weight():
        'Ask about weight'
        weight_input = bot_input(log_file, f"How much does the {model_name} weigh (in tons)? ")

        # Jump back if requested
        correction_maybe = check_for_correction(trucks_info, weight_input)
        if correction_maybe:
            return correction_maybe

        # Looking for a float with optional unit (tons)
        pat = re.compile(r"^(.*?)(t|ton|tons)?\s*$")
        weight_input = pat.match(weight_input).group(1)

        try:
            weight = sanitize_float(weight_input)
        except ValueError:
            bot_output(log_file, "That does not look like a number to me. Let's try again.")
            return ask_model_weight # Next action: Ask again

        if weight < 0 or weight > 80:
            bot_output(log_file, "Weight seems to be too high or low, please check!")
            return ask_model_weight # Nex action: Ask again
        else:
            truck_spec.weight = weight
            return None # Next action: Done asking about this

    def ask_model_max_load():
        'Ask about max load'
        max_load_input = bot_input(log_file, f"What is the max load for the {model_name} model (in tons)? ")

        # Jump back if requested
        correction_maybe = check_for_correction(trucks_info, max_load_input)
        if correction_maybe:
            return correction_maybe

        # Looking for a float with optional unit (tons)
        pat = re.compile(r"^(.*?)(t|ton|tons)?\s*$")
        max_load_input = pat.match(max_load_input).group(1)

        try:
            max_load = sanitize_float(max_load_input)
        except ValueError:
            bot_output(log_file, "That does not look like a number to me. Let's try again.")
            return ask_model_max_load # Next action: Ask again

        if max_load < 0 or max_load > 80:
            bot_output(log_file, "Max load seems to be too high or low, please check!")
            return ask_model_max_load # Next action: Ask again
        else:
            truck_spec.max_load = max_load
            return None # Next action: Done asking about this

    def ask_model_how_many():
        'Record number of trucks for this model'
        if trucks_info.brand_same_model[i_brand]: # If this is the only model, we already know this
            trucks_info.trucks_list.append((truck_spec, trucks_info.n_trucks_brand[i_brand]))
        else:
            model_how_many_input = bot_input(log_file, f"How many {truck_spec.brand} {model_name} trucks do you have? ")

            # Jump back if requested
            correction_maybe = check_for_correction(trucks_info, model_how_many_input)
            if correction_maybe:
                return correction_maybe

            try:
                model_how_many = sanitize_int(model_how_many_input)
            except ValueError:
                bot_output(log_file, "That does not look like a number to me. Let's try again.")
                return ask_model_how_many # Next action: Ask again

            # Check whether that number is logically too high
            if model_how_many + trucks_info.completeness[i_brand] > trucks_info.n_trucks_brand[i_brand]:
                bot_output(log_file, "That's too many, the numbers don't add up. Let's try again.")
                return ask_model_how_many # Next action: Ask again

            # Check whether number is postive
            if model_how_many <= 0:
                bot_output(log_file, "I expected a positive number of trucks. Let's try again.")
                return ask_model_how_many # Next action: Ask again

            # Check whether that number is logically too low
            if trucks_info.brand_same_model[i_brand] and model_how_many + trucks_info.completeness[i_brand] < trucks_info.n_trucks_brand[i_brand]:
                bot_output(log_file, "That's not enough, the numbers don't add up. Let's try again.")
                return ask_model_how_many # Next action: Ask again

            trucks_info.trucks_list.append((truck_spec, model_how_many))
            trucks_info.completeness[i_brand] += model_how_many

            return None # Next action: Done asking about this

    # Go through the sub-questions
    for f in [ask_model_engine_size, ask_model_axle_number, ask_model_weight, ask_model_max_load, ask_model_how_many]:
        next_action = f()
        while next_action:
            next_action = next_action()

    if trucks_info.brand_same_model[i_brand]: # If this is the only model, we can ask about the next brand
        return make_ask_brand_trucks(trucks_info, i_brand+1) # Next action: Ask about next models for next brand
    else:
        if not check_completeness(trucks_info, i_brand): # If there are still trucks left for this brand, keep asking about next model
            return ask_brand_models(trucks_info, i_brand) # Next action: Ask about next model for same brand
        else:
            # No trucks left for this brand - check whether user mistakenly specified only one model in beginning
            if not trucks_info.brand_same_model[i_brand] and len(trucks_info.brand_models[i_brand]) == 1: # Notify user and change brand_same_model if user changed his mind
                bot_output(log_file, f"Before you told me you have more than one model. No problem, it's ok to change your mind.")
                trucks_info.brand_same_model[i_brand] = True
            return make_ask_brand_trucks(trucks_info, i_brand+1) # Next action: Ask about next models for next brand

def check_consistency(trucks_info):
    'This function checks for consistency while the data is collected. As soon as an inconsistency arises during the process, this function will return False.'

    # Count whether total number of trucks matches sum of number of trucks per brand
    s = 0
    outstanding_brands = 0 # Brand for which we have no information yet
    for i_brand, n in enumerate(trucks_info.n_trucks_brand):
        if n is not None:
            if n < 1:
                bot_output(log_file, f"The number of {trucks_info.brands_list[i_brand]} trucks is zero or negative!")
                return False
            s += n
        else:
            outstanding_brands += 1
        if s > trucks_info.n_trucks - outstanding_brands:
            bot_output(log_file, "The total for the number of trucks among brands exceeds the total!")
            return False

    # Count whether we have specified enough trucks
    if outstanding_brands == 0 and s < trucks_info.n_trucks:
        bot_output(log_file, "You have specfied too low a number of trucks!")
        return False

    # Count whether number of trucks per model matches number of trucks per brand
    s = [0] * len(trucks_info.brands_list)
    for model, n in trucks_info.trucks_list:
        s[model.brand_idx] += n
        if s[model.brand_idx] > trucks_info.n_trucks_brand[model.brand_idx]:
            bot_output(log_file, f"The total for the number of {model.brand} trucks among models exceeds the total!")
            return False
    return True    

def check_completeness(trucks_info, i_brand):
    ''''
    Checks whether we have collected all the info about models for brand given by i_brand.
    This check is needed because the chatbot can go back and forth between questions, and skip unneeded questions.
    '''
    if trucks_info.completeness[i_brand] == trucks_info.n_trucks_brand[i_brand]:
        return True
    else:
        return False

# Initialize next_action (telling chatbot what to do next) and
# trucks_info (holding trucks information until we write it to disk)
next_action = ask_name
trucks_info = TrucksInfo()
while next_action:
    next_action = next_action(trucks_info)

bot_output(log_file, f"Saving data to {data_file}")
bot_output(log_file, f"Saved chat log to {log_file}")

# Write info to file
with open(data_file, 'a') as f:
    f.write(trucks_info.to_json() + '\n')

# Print summary info to console
print("\n")
trucks_info.pretty_print()
print("\n")
