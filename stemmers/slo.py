import re

_vowels = set('aeiou')
_consonants = set('bcčdfghjklmnprsštvzž')

def is_consonant(char):
    return char.lower() in _consonants

def measure(word):
    return len([i for i in range(len(word)) if is_consonant(word[i]) and (i == 0 or not is_consonant(word[i-1]))])

def apply_rules(word):
    original_length = len(word)
    
    # Rule 1: Remove -ovski, -evski, -anski
    if original_length > 8:
        for suffix in ['ovski', 'evski', 'anski']:
            if word.endswith(suffix):
                return word[:-len(suffix)]
    
    # Rule 2: Remove -stvo, -štvo
    if original_length > 7:
        for suffix in ['stvo', 'štvo']:
            if word.endswith(suffix):
                return word[:-len(suffix)]
    
    # Rule 3: Remove various suffixes
    if original_length > 6:
        suffixes = [
            'šen', 'ski', 'ček', 'ovm', 'ega', 'ovi', 'ijo', 'ija',
            'ema', 'ste', 'ejo', 'ite', 'ila', 'šče', 'ški',
            'ost', 'ast', 'len', 'ven', 'vna', 'čan', 'iti',
            'al', 'ih', 'iv', 'eg', 'ja', 'je', 'em', 'en', 'ev', 'ov', 'jo',
            'ma', 'mi', 'eh', 'ij', 'om', 'do', 'oč', 'ti', 'il', 'ec',
            'ka', 'in', 'an', 'at', 'ir'
        ]
        for suffix in suffixes:
            if word.endswith(suffix):
                return word[:-len(suffix)]
    
    # Rule 4: Remove final š, m, c, a, e, i, o, u
    if original_length > 5:
        for suffix in ['š', 'm', 'c', 'a', 'e', 'i', 'o', 'u']:
            if word.endswith(suffix):
                return word[:-len(suffix)]
    
    # Rule 5: Remove final consonant if word ends with two consonants
    if original_length > 6 and is_consonant(word[-1]) and is_consonant(word[-2]):
        return word[:-1]
    
    # Rule 6: Remove final vowel
    if original_length > 5:
        for vowel in 'aeiou':
            if word.endswith(vowel):
                return word[:-1]
    
    return word

def stem(word):
    if len(word) <= 3:
        return word

    word = word.lower()
    
    # Apply stemming rules 3 times
    for _ in range(3):
        word = apply_rules(word)
    
    # Additional rule for -ah suffix
    if word.endswith('ah'):
        word = word[:-2]
    
    return word

def stem_text(text):
    words = re.findall(r'\w+', text.lower())
    return ' '.join(stem(word) for word in words)

if __name__ == "__main__":
    # Test cases
    test_words = [
        "slovenija", "slovenski", "slovenska", "telovadbe", "telovadcem", 
        "telovadcev", "telovadi", "telovadil", "telovaditi", "telovadne", 
        "telovadni", "telovadno", "telovnik", "tem", "tema", "temacna", 
        "temacni", "temacno", "besedah", "besedam", "besedami", "besede", 
        "besedi", "besedice", "besedico", "besedila", "besedilo", "besedno"
    ]

    print("Test cases:")
    for word in test_words:
        stemmed = stem(word)
        print(f"{word} -> {stemmed}")

    # Test with a sentence
    test_sentence = "Slovenija je čudovita dežela z bogato kulturo in zgodovino."
    stemmed_sentence = stem_text(test_sentence)
    print(f"\nOriginal: {test_sentence}")
    print(f"Stemmed: {stemmed_sentence}")