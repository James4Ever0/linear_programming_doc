from pytest import fixture, FixtureRequest

import os
import json

import sys

sys.path.append("../")
from ast_utils import walkModel

sample_code_dir = "sample_code"

path_to_mark = lambda path: os.path.basename(path).split(".")[0]

sample_code_paths = [
    os.path.join(sample_code_dir, code_path)
    for code_path in os.listdir(sample_code_dir)
    if code_path.endswith(".dsl")
]
sample_code_parsed_paths = [
    os.path.join(sample_code_dir, code_parsed_paths)
    for code_parsed_paths in os.listdir(sample_code_dir)
    if code_parsed_paths.endswith(".json")
]
sample_code_marks = [
    os.path.basename(rel_code_path).split(".")[0] for rel_code_path in sample_code_paths
]

# check if all code has parsed output
for mark in sample_code_marks:
    assert (
        os.path.join(sample_code_dir, mark + ".json") in sample_code_parsed_paths
    ), f"Missing parsed output: {mark}"

sample_code_parsed_paths_dict = {path_to_mark(p): p for p in sample_code_parsed_paths}
sample_code_paths_dict = {path_to_mark(p): p for p in sample_code_paths}

from collections import namedtuple

CPJ = namedtuple("CPJ", ["code", "parsed_json"])

import textx


@fixture
def metamodel():
    grammar_path = "../grammar.tx"
    with open(grammar_path, "r") as f:
        grammar_content = f.read()
    mm = textx.metamodel_from_str(grammar_content)
    return mm


@fixture(params=sample_code_marks)
def sample_code(request: FixtureRequest):
    mark = request.param
    code_path = sample_code_paths_dict[mark]
    parsed_path = sample_code_parsed_paths_dict[mark]
    print("READING CODE AT:", code_path)
    with open(code_path, "r") as f:
        code_content = f.read()
    with open(parsed_path, "r") as f:
        parsed_content = f.read()
        parsed_json = json.loads(parsed_content)
    return CPJ(code=code_content, parsed_json=parsed_json)


from textx.metamodel import TextXMetaModel


def test_parse_code(sample_code: CPJ, metamodel: TextXMetaModel):
    model = metamodel.model_from_str(sample_code.code)
    tree = walkModel(model)
    target_tree = sample_code.parsed_json
    assert tree == target_tree