import sympy
from typing import cast
def calc(i0, a_arr: list, x0):
    i, x = sympy.symbols('i x')
    f = lambda i, n, a: a / ((1 + i) ** n)
    result = cast(sympy.Expr, -x)
    for n, a in enumerate(a_arr):
        result += f(i, n + 1, a)
    print('[expr]', result)
    return result.evalf(subs={i:i0, x:x0})

# a_arr = [
#     -28197.28,
#     -4789.57,
#     6691,
#     8706.48,
#     8932.69,
#     9605.62,
#     11030.94,
#     11281.97,
#     11259.61,
#     11236.13,
#     11609.99,
#     2075.55,
# ]

a_arr = [
    -28197.28,
    -5172.43,
    5884.55,
    7848.69,
    7518.68,
    8149.41,
    9051.99,
    9191.49,
    9174.72,
    9157.11,
    9537.14,
    1817.88,
]

i = 0.05
x = 29695.24

ret = calc(i, a_arr, x)
print('[val]',ret)
