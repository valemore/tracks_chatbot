# This file does some basic language stuff

import inflect

# Some alternatives for yes/no answers
yes_answers = ["yes", "y", "yep", "yup", "ya", "ja", "sure"]
no_answers = ["no", "n", "none", "nope", "nein", "zero", "no more"]

def is_yes_answer(s):
    if s.lower() in yes_answers:
        return True
    return False

def is_no_answer(s):
    if s.lower() in no_answers:
        return True
    return False

# We are able to deal with some number words
p = inflect.engine()
number_words_dict = {
    p.number_to_words(i):i for i in range(21)
}

def sanitize_int(n_str):
    'Try to interpret n_str as an int'
    n_str_stripped = n_str.strip()
    try:
        n = int(n_str_stripped)
    except ValueError:
        try:
            n = number_words_dict[n_str_stripped]
        except KeyError:
            raise ValueError # Raise ValueError for our chatbot to catch
    return n

def sanitize_float(x_str):
    'Try to interpret n_str as an int'
    # Could also add ability to deal with German-style floats
    x_str_stripped = x_str.strip()
    try:
        x = float(x_str_stripped)
    except ValueError:
        try:
            x = number_words_dict[x_str_stripped]
        except KeyError:
            raise ValueError # Raise ValueError for our chatbot to catch
    return x

def sanitize_str(s_str):
    'Make sure string is not empty.'
    s_str = s_str.strip()
    if s_str == '':
        raise ValueError # Raise ValueError for our chatbot to catch
    # Could also add ability to deal with German-style floats
    return s_str

def blandify_str(s):
    'Convert a string to lowercase and replace special characters.'
    special_chars = '-,_.;:!"\'$%^&*()=+[]{}\\/?<>|'
    replacement_dict = {
        'ä':'a',
        'ö':'o',
        'ü':'u',
        'ë':'e',
        'š':'s',
    }
    # Convert to lower case
    s = s.lower()
    # Replace special characters
    for c in special_chars:
        s = s.replace(c, ' ')
    for k, v in replacement_dict.items():
        s = s.replace(k, v)
    # Get rid of extra whitespace
    return ' '.join(s.split()).strip()

def get_brands(brands_file):
    'Reads all known brands from a file, returns a list'
    with open(brands_file, 'r') as f:
        brands_list = [ l.rstrip('\n') for l in f ]
    return brands_list

def find_brand(s, brands_list):
    'Looks which brands in string s are found in brands_list.'

    # To get around capitalization and special character issues, all comparisons are made on lowercase ascii
    s = blandify_str(s)
    brands_list_bland = [ blandify_str(b) for b in brands_list ]

    # Tokenize
    s_tokenized = s.split()

    def find_brand_iter(tokens):
        # We look for largest possible group of tokens first
        for i in range(len(tokens)):
            for j in reversed(range(i+1, len(tokens)+1)):
                for idx_brand, b in enumerate(brands_list_bland):
                    if ' '.join(tokens[i:j]) == b:
                        # If we find a brand, continue searching recursively on remaining tokens
                        return [brands_list[idx_brand]] + find_brand_iter(tokens[:i] + tokens[j:])
    
        # Return empty list if no match was found
        return []
    
    result = find_brand_iter(s_tokenized)
    return list(set(result))

