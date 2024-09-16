from whoosh.analysis import RegexTokenizer, LowercaseFilter, CharsetFilter, Token
from whoosh.analysis.morph import StemFilter
from whoosh.lang.porter import stem as english_stem
from whoosh.analysis.tokenizers import default_pattern
from whoosh.analysis.filters import StopFilter, STOP_WORDS
from stemmers.slo import stem as slovenian_stem

class MultiLingualStemFilter(StemFilter):
    def __init__(self, stemfn=None, ignore=None, cachesize=10000):
        self.stemfn = stemfn or self.stem
        self.ignore = frozenset(ignore) if ignore else frozenset()
        self.cachesize = cachesize
        self.cache = {}

    def stem(self, token):
        text = token.text
        lang = token.lang if hasattr(token, 'lang') else 'unknown'
        
        if lang == 'en':
            return english_stem(text)
        else:  # Default to Slovenian stemming for unknown languages
            return slovenian_stem(text)

    def __call__(self, tokens):
        # Ensure cache exists
        if not hasattr(self, 'cache'):
            self.cache = {}
        
        for t in tokens:
            text = t.text
            if text in self.ignore:
                yield t
            elif text in self.cache:
                t.text = self.cache[text]
                yield t
            else:
                stemmed = self.stemfn(t)
                if stemmed != text:
                    t.text = stemmed
                    if len(self.cache) < self.cachesize:
                        self.cache[text] = stemmed
                yield t

class LanguageAwareTokenizer(RegexTokenizer):
    def __init__(self, expression=default_pattern, gaps=False):
        super().__init__(expression, gaps)
        self.language = 'unknown'

    def __call__(self, value, positions=False, chars=False, keeporiginal=False, removestops=True, start_pos=0, start_char=0, mode='', **kwargs):
        t = Token(positions, chars, removestops=removestops, mode=mode, **kwargs)
        for pos, match in enumerate(self.expression.finditer(value)):
            t.text = match.group()
            t.lang = self.language
            if keeporiginal:
                t.original = t.text
            t.stopped = False
            if positions:
                t.pos = start_pos + pos
            if chars:
                t.startchar = start_char + match.start()
                t.endchar = start_char + match.end()
            yield t

def MultiLingualAnalyzer(
    expression=r'\w+|\d+|[^\w\s]+',
    stoplist=STOP_WORDS,
    minsize=2,
    maxsize=None,
    gaps=False,
    ignore=None,
    cachesize=50000,
):
    ret = LanguageAwareTokenizer(expression=expression, gaps=gaps)
    chain = ret | LowercaseFilter()
    if stoplist is not None:
        chain = chain | StopFilter(stoplist=stoplist, minsize=minsize, maxsize=maxsize)
    return chain | MultiLingualStemFilter(ignore=ignore, cachesize=cachesize)