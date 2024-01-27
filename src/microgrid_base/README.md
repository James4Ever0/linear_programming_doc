# Microgrid Algorithm Service

The main objective of this directory is to model an IES system and optimize its operation.

User defines topology, in which devices such as loads, grids, energy sources and generators are.

Inputs and outputs follow a standard format. Modeling language "IESLang" is used to describe the system.

## "passwords.py"

This file is ignored by default. Should you create this under `./passwords.py` and `./microgrid_server_release/server/passwords.py`.

Example content:

```python
from log_utils import logger_print

redis_password = ''
```

## "docker_launch.py"

Just run this file by `python3 docker_launch.py` and service will be created under `http://localhost:9870`.

Attach container by `docker container attach <container_id>`.

## "openapi.json"

This file describe public APIs of the algorithm server. You can load this file using Postman/Apifox.

To acquire this file, run `curl -O <server_end_point>/openapi.json`.

## Usage

The easiest way for setting this up is by installing all dependencies and then invoke `make` under base directory.

On different system you may need to modify code in `Makefile` to ensure correct dependency resolution.

Install CPLEX and Anaconda (for environment management) on your system. Do not use non-Linux OSes for deployment since they do not support `tmux`.

Minimum Python version is `3.9`.

Install Python dependencies by `pip install -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt`.

To run `celery`, you need to install and run `redis-server` and `rabbitmq-server`.

## Developing

If some files are generated by templates, do not modify them. Instead, find related ".j2" files and modify it, then invoke `make test` under base directory, to ensure your modification is not making more troubles.

For more info on Pyomo, please check [this tutorial](https://www.shangyexinzhi.com/article/5385476.html), [github repo](https://github.com/WenYuZhi/PyomoTutorial) or [official docs](https://pyomo.readthedocs.io/en/stable/index.html).

## Roadmap

* [x] create algorithm service
* [x] parse input parameters from excel
* [x] create name mapping table
* [x] define port types and connectivity matrix
* [x] generate model code using jinja2 and macros
* [x] prepare generative tests
* [x] type check undefined variables
* [ ] define and parse `*.ies` DSL files

## File Structure

- Makefile: main makefile for code generation, define build dependencies, handles and share environment variables across submake sessions.
- ies_optim.py.j2: template for generating main model code
- jinja_utils.py: utils for reading and rendering template, testing and formatting generated code
- type_system_v2.py: topology type system generation
- parse_params.py: shared params for code generation
- parse_frontend_sim_param_translation.py: parse `.js` file and generate export table header translation map
- parse_export_format.py: generate `export_format_validate.py`
- parse_optim_constraints.py: generate `constraints.log` (which contains all constraints used in model) by parsing `ies_optim.py`
- parse_units_and_names.py: generate `microgrid_jinja_param_base.py` used for input datastructure and unit definitions in `ies_optim.py`
- microgrid_server_release: for service distribution
    - constants_en.txt: constants definitions imported by merged_units.txt
    - merged_units.txt: modified unit definitions used by package "pint"
    - init: setup scripts for server (incomplete)
        - init.sh: bash setup script
        - requirements.txt: python requirements file
    - server: main server code
        - export_format_validate.py: validate and export data to output
        - export_format.json: used by `solve_model.py` for data validation
        - expr_utils.py: for analyzing expressions in exceptions
        - fastapi_celery_server.py: celery worker for model solving
        - fastapi_datamodel_template.py: data exchange schema for api
        - fastapi_server_template.py: fastapi server code, which defines apis
        - fastapi_terminate_service.sh: for finding and killing previous algorithm service (for restart)
        - fastapi_tmuxp.sh: launching service by creating four panes in one tmux session
        - fastapi_tmuxp.yml: config file read by tmuxp, used to create tmux session
        - frontend_sim_param_translation.json: translate Chinese table headers into predefined terms for output
        - ies_optim.py: model definition and implementation
        - passwords.py: stores password for redis, used by `fastapi_celery_server.py`
        - solve_model.py: receive input as model specification, invoke optimization session and create results.
        - template_input.json: example api input data format
        - test_json_input_format.py: test reading file for input data, checking topology consistency, model solving and data exporting
        - test_topo_check.py: test using code to construct model topology as input data and check topology consistency, model solving and data exporting
        - topo_check.py: utils for constructing model topology and checking
        - unit_utils.py: utils for unit conversion
- test: code for testing
    - sample_data: stores data which might causes problem to system
    - common_fixtures.py: shared fixtures used by `test_model.py`
    - common_fixtures.py.j2: code template which uses `ies_optim.py` for generating input data fixtures to `common_fixtures.py.tmp`
    - common_fixtures.py.tmp: template generation target, used as reference while writing `common_fixtures.py`
    - conic_problem.py: experiment on solving fictional optimization nonlinear objectives using numpy
    - dev_info_tmp_gen.py: reading `common_fixtures.py.j2` and generate `.tmp` target
    - generate_test_model.py: reading `test_model.py.j2` and generate `test_model.py`
    - test_model.py: test code for main model code
    - Makefile: test makefile for easy construction by specifying build dependencies
- dsl_parser: IESLang parser and code generator
    - functional_base.py: experimental functional exeucution mechanism
    - functional_base.py.j2: for generating functional_base.py.j2
    - generate_code.py: for reading functional_base.py.j2 and generate python code
    - lex_yacc.py: for tokenizing and parsing IESLang code (experiment)
    - Makefile: define IESLang related build tasks
    - mylang.ies: IESLang language specification
    - mylang.txt: legacy language specification
    - pyomo_reduce_ineqalities.py: for calculating variable bounds from a system of ineqality expressions, used by iesl
    - yacc_init.py: experimencal parser
    - your_model_name.lp: experimental model export as lp files which contains Chinese charactors
    - 柴油.ies: diesel power generator model written in IESLang language
- cplex_convex_debug: test files for debugging cplex solver
    - init.sh: for moving `*.lp` files to this directory.
- frontend_convert_format: convert non-standard frontend data into standard model specification format, used by frontend
    - customToolbar.vue: code used by frontend, which includes logics for input data construction
    - cvt.js: non-standard input format conversion
    - error_cvt.js: error message handling (translation)
    - input_template_processed.json: example input template
    - sample_parse.json: partial cleaned non-standard input data
    - sample.json: raw non-standard input data
- logs: directory reserved for logging
    - .log: need to be touched in order to preserve this directory in release archive `release.7z`
- makefile_ninja_pytest_incremental_test
    - platform_detect_makefile: for detecting different os using makefile
        - Makefile: os detect implementation
    - construct_ninja_file.py: using package "ninja_syntax" to generate ninja.build file
    - dodo.py: experiment of package "pydo"
    - generic.py: python type system experiment
    - lfnf.py: pytest file used for testing pytest "-lfnf" commandline flag
    - Makefile.j2: test jinja template for generating Makefile
    - mytest.py: pytest file using type hints and request fixture
    - test_buffer.py: infinite loop for conda stdout buffer mechanism
    - type_check.py: multiple experiments of python type system
    - typecheck.py: static condition exhausitiveness check