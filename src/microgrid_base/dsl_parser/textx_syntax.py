import textx

# TODO: perform unittest on serialized AST

# STRING is something quoted. not plain words.
# define and use TOKEN or VARNAME instead.
# shall you name collected items to retrieve them.
with open("grammar.tx", "r") as f:
    grammar = f.read()

metamodel = textx.metamodel_from_str(grammar)

with open(fp := "sample.ies", "r") as f:
    content = f.read()

from ast_utils import walkModel

model = metamodel.model_from_str(content)
# print(dir(model))
# breakpoint()
import rich
tree = walkModel(model)
rich.print(tree)
breakpoint()

cn = lambda i: i.__class__.__name__

print(model.modelInfo)
for subModel in model.subModels:
    print(subModel)
    if cn(subModel) == "Constants":
        print(subModel.constants)
    elif cn(subModel) == "ConstantLists":
        print(subModel.constantLists)

# import rich
# rich.print(model.__dict__)
# breakpoint()
