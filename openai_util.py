import re

def count_tokens(text):
    tokens = re.findall(r'\w+|[^\w\s]', text)
    return len(tokens)

def truncate_text_to_token_limit(text, max_tokens):
    tokens = re.findall(r'\w+|[^\w\s]', text)
    
    while len(tokens) > max_tokens:
        tokens.pop()
    
    return " ".join(tokens)  # Use " ".join() instead of "".join()
