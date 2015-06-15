"""
# The grammarlang notated in itself:
file =>
    statement
    concat(file statement): file newline statement

statement =>
    single_rule(symbol rule):    symbol arrow:"=>" rule
    multiple_rule(symbol block): symbol arrow:"=>" indent block dedent
    empty_list:                  special

block =>
    first: rule
    append(block rule): block newline rule

rule =>
    implicit_pass_rule:
        rhs
    labelled_rule(symbol rhs):
        symbol colon:":" rhs
    labelled_mapped_rule(symbol arguments rhs): 
        symbol lp:"(" arguments rp:")" colon:":" rhs

rhs =>
    empty_list:
    items

items =>
    first: item
    append: items item

item =>
    named_item(symbol item): symbol equals:"=" item
    symbolic_item:           symbol
    special
    call(symbol arguments):  symbol lp:"(" arguments rp:")"

arguments =>
    empty_list:
    append_arg_str: arguments symbol
    append_arg_str: arguments string
    append_arg_int: arguments int

special => special(symbol string): symbol colon:":" string
"""
from parser import Parser, Rule
import sys

symboltab = {
        '=': 'equals',
        '=>': 'arrow',
        ':': 'colon',
        '(': 'lp',
        ')': 'rp',
}

grammar = [
    # statement level syntax
    Rule('file', ['statement'],
        'pass'),
    Rule('file', ['file', 'newline', 'statement'],
        'concat', [0, 2]),

    Rule('statement', ['symbol', 'arrow', 'rule'],
        'single_rule', [0, 2]),
    Rule('statement', ['symbol', 'arrow', 'indent', 'block', 'dedent'],
        'multiple_rule', [0, 3]),
    Rule('statement', ['special'],
        'empty_list', []),

    Rule('block', ['rule'],
        'first'),
    Rule('block', ['block', 'newline', 'rule'], 
        'append', [0, 2]),

    Rule('rule', ['rhs'],
        'implicit_pass_rule'),
    Rule('rule', ['symbol', 'colon', 'rhs'],
        'labelled_rule', [0, 2]),
    Rule('rule', ['symbol', 'lp', 'arguments', 'rp', 'colon', 'rhs'],
        'labelled_mapped_rule', [0, 2, 5]),

    Rule('rhs', [],        'empty_list'),
    Rule('rhs', ['items'], 'pass'),

    Rule('items', ['item'],          'first'),
    Rule('items', ['items', 'item'], 'append'),
    # Item definitions
    Rule('item', ['symbol', 'equals', 'item'], 'named_item', [0, 2]),
    Rule('item', ['symbol'], 'symbolic_item'),
    Rule('item', ['special'], 'pass'),
    Rule('item', ['symbol', 'lp', 'arguments', 'rp'], 'call', [0, 2]),

    Rule('special', ['symbol', 'colon', 'string'],
        "special", [0, 2]),

    Rule('arguments', [], 'empty_list'),
    Rule('arguments', ['arguments', 'symbol'], 'append_arg_str'),
    Rule('arguments', ['arguments', 'string'], 'append_arg_str'),
    Rule('arguments', ['arguments', 'int'],    'append_arg_int'),
]

def post_append(env, seq, item):
    seq.append(item)
    return seq

def post_concat(env, seq1, seq2):
    seq1.extend(seq2)
    return seq1

def post_empty_list(env):
    return []

def post_first(env, item):
    return [item]

def post_single_rule(env, lhs, (rhs, attribute, mapping)):
    return [Rule(lhs.value, rhs, attribute, mapping)]

def post_multiple_rule(env, lhs, block):
    seq = []
    for rhs, attribute, mapping in block:
        seq.append(Rule(lhs.value, rhs, attribute, mapping))
    return seq

def post_implicit_pass_rule(env, items):
    attribute = 'pass' if len(items) == 1 else 'tuple'
    return [cell for name, cell in items], attribute, None

def post_labelled_rule(env, label, items):
    return [cell for name, cell in items], label.value, None

def post_labelled_mapped_rule(env, label, mapping, items):
    k = [name for name, cell in items]
    mapping = [k.index(name) for name in mapping]
    return [cell for name, cell in items], label.value, mapping

def post_named_item(env, name, (_, cell)):
    return name.value, cell

def post_symbolic_item(env, symbol):
    return symbol.value, symbol.value

def post_special(env, name, keyword):
    symboltab = env.symboltab
    name = name.value
    keyword = keyword.value
    assert keyword not in symboltab or symboltab[keyword] == 'symbol' or symboltab[keyword] == name
    symboltab[keyword] = name
    while len(keyword) > 1:
        keyword = keyword[:len(keyword)-1]
        symboltab[keyword] = symboltab.get(keyword, 'symbol')
    return name, name

def post_call(env, name, arguments):
    return env.functions[name.value](*arguments)

def post_append_arg_str(env, seq, token):
    seq.append(token.value)
    return seq

def post_append_arg_int(env, seq, token):
    seq.append(int(token.value))
    return seq

def post_nothing(env):
    return None

def post_pass(env, arg):
    return arg

class Env(object):
    def __init__(self, symboltab, functions):
        self.symboltab = symboltab
        self.functions = functions

parse = Parser(symboltab, grammar, 'file')

def load(functions, path):
    env = Env({}, functions)
    grammar = parse.from_file(globals(), env, path)
    assert len(grammar) > 0, "empty grammar"
    return Parser(env.symboltab, grammar, grammar[0].lhs)

def load_from_string(functions, string):
    env = Env({}, functions)
    grammar = parse(globals(), env, string)
    assert len(grammar) > 0, "empty grammar"
    return Parser(env.symboltab, grammar, grammar[0].lhs)