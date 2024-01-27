from pyomo.environ import *
import rich
def build_and_solve_model_with_strict_inequality():
    model = ConcreteModel()

    model.x = Var(bounds=(-1,1))
    model.y = Var(bounds=(-1,1))
    model.rel = Constraint(expr=model.x < model.y) # error, if not patched.

    model.obj = Objective(expr=model.x, sense=minimize)

    solver = SolverFactory('cplex')
    ret = solver.solve(model, tee=True)
    rich.print(ret)

# build_and_solve_model_with_strict_inequality()
# print("#"*60)
######## SUPPRESS STRICT INEQUALITY PATCH #########

def strict_setter(self, val):
    ...

def strict_getter(self):
    return False

InEq = pyomo.core.expr.relational_expr.InequalityExpression
setattr(InEq,"_strict_setter", strict_setter)
setattr(InEq,"_strict_getter", strict_getter)

InEq._strict = property(fget=InEq._strict_getter, fset=InEq._strict_setter)
InEq.strict = InEq._strict

######## SUPPRESS STRICT INEQUALITY PATCH #########

build_and_solve_model_with_strict_inequality()
