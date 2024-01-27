
# pass environment variables by higher level make invocation.

.PHONY: test

# PLATFORM := $(shell python -c "import os; print(os.name)")
# ifeq (${PLATFORM}, )
# PLATFORM := $(shell python3 -c "import os; print(os.name)") # executed on macos
# endif

# ifeq (${PLATFORM}, nt)
# OS_TYPE = windows
# else
# OS_TYPE = macos
# endif

# PYTHON_ENV = -X utf8=1

# ifeq (${OS_TYPE}, macos)
# CONDA_ENV = rosetta
# PYTHON = /usr/bin/python3
# else
# CONDA_ENV = cplex
# PYTHON = python ${PYTHON_ENV}
# endif

# not unittest!

test:
	cd test && ${PYTHON} -m pytest --lf --lfnf=all --capture=tee-sys test_dsl.py
	# ${PYTHON} textx_syntax.py

functional_base.py: functional_base.py.j2 generate_code.py
	${PYTHON} generate_code.py