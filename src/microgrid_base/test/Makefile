
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

# CONDA = conda run -n ${CONDA_ENV} --live-stream --no-capture-output

ifeq (${OS_TYPE}, macos)
MAIN_EXEC=bash run_test.sh
else
# MAIN_EXEC=python ${PYTHON_ENV} -m pytest --lf --lfnf=all --capture=no
MAIN_EXEC=python ${PYTHON_ENV} -m pytest --lf --lfnf=all --capture=tee-sys
# MAIN_EXEC=python ${PYTHON_ENV} -m pytest --lf --lfnf=all --capture=tee-sys test_model.py
# MAIN_EXEC=${CONDA} python ${PYTHON_ENV} -m pytest --lf --lfnf=all --capture=tee-sys test_model.py
endif

# main: run_test.sh test_model.py common_fixtures.py stepwise
main: run_test.sh test_model.py test_export.py test_failsafe.py common_fixtures.py
	env VAR_INIT_AS_ZERO=1 ${MAIN_EXEC} test_export.py
	${MAIN_EXEC} test_model.py
	${PYTHON} test_failsafe.py

t_export:
	${MAIN_EXEC} test_export.py

t_model:
	${MAIN_EXEC} test_model.py

t_failsafe:
	${PYTHON} test_failsafe.py

test_model.py: generate_test_model.py test_model.py.j2
	${PYTHON} $<

common_fixtures.py.tmp test_export.py: dev_info_tmp_gen.py common_fixtures.py.j2 test_export.py.j2 ../export_format_validate.py
	${PYTHON} $<

# stepwise: runtime_override_stepwise.py
# 	${PYTHON} $< -t
# 	${CONDA} python ${PYTHON_ENV} $< -t
