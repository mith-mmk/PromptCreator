# <program> ::= <block>
# <block> ::= <statement> | <statement> <block> | function <id>(<args>) { <block> } | { <block> }
# id := [a-zA-Z_][a-zA-Z0-9_]*
# <args> ::= <arg> | <arg>, <args>
# <statement> ::= <assignment> | <if> | <while> | <print> | <return> | <function> | <break> | <continue>
# <assignment> ::= <variable> = <expression>
# <if> ::= if <formula> <block> | if <formula> <block> else <block>
# <while> ::= while <formula> <block>
# <break> ::= break
# <continue> ::= continue
# <print> ::= print <expression>
# <return> ::= return <expression>
# <function> ::= function <variable> <block>

# <formula> and <variable> implementation is compute.FormulaCompute.compute()
