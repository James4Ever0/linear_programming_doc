from log_utils import logger_print

import cmath
import datetime
import json
import os
import tempfile
from typing import Any, Dict, List, Tuple, Union, cast
from constants import Solver

import pandas as pd
from beartype import beartype

from constants import *  # pylance issue: unrecognized var names
from debug_utils import *
from error_utils import ErrorManager

# finding every integer feasible solution
# ref: https://www.ibm.com/support/pages/obtaining-solution-values-each-time-cplex-finds-integer-solution
from log_utils import (
    log_dir,
    logger_print,
    pretty_format_excinfo_context,
    timezone,
    logger_traceback,
)

# TODO: save model as .lp & .mps format
# import pyomo_patch  # type: ignore
# TODO: invoke conflict refiner everytime each submodel is built, once conflict is found.
# TODO: deactivate one to all objective functions
# TODO: cache function input/output to redis for faster response
# TODO: profile code performance
# TODO: partial deletion/elastic filter
# TODO: finding maximum feasible subset (maxFS) instead of IIS
from pyomo_environ import *

# from ies_optim import 规划结果详情,规划方案概览

try:
    from typing import Literal
except:
    from typing_extensions import Literal

from pydantic import BaseModel
from enum import IntEnum

from export_format_validate import *  # pylance issue: multiple star import (false positive)
from ies_optim import InputParams, ModelWrapper

# from pyomo.util.infeasible import log_infeasible_constraints

# TODO: add pareto plot, change data structure of solution result object.

import shutil

REQUIRED_BINARIES = [Solver.cplex, "swipl"]

if ies_env.FAILSAFE:
    REQUIRED_BINARIES.append(Solver.ipopt)
    REQUIRED_BINARIES.append(Solver.scip)

with ErrorManager(default_error="Not all required binaries were found.") as em:
    for b in REQUIRED_BINARIES:
        if shutil.which(b) is None:
            em.append("Binary %s not found in PATH." % b)

EXPORT_FORMAT_FPATH = os.path.join(os.path.dirname(__file__), "export_format.json")
with open(EXPORT_FORMAT_FPATH, "r") as f:
    dt = json.load(f)
    simulationResultColumns = dt["仿真结果"]["ALL"]
    simulationResultColumns = [
        e if type(e) == str else e[0] for e in simulationResultColumns
    ]

FRONTEND_SIM_PARAM_TRANS_FPATH = os.path.join(
    os.path.dirname(__file__), "frontend_sim_param_translation.json"
)

with open(FRONTEND_SIM_PARAM_TRANS_FPATH, "r") as f:
    FSPT = json.load(f)

from pandas import DataFrame

from topo_check import 拓扑图


###
def 导出结果表_格式化(
    结果表: DataFrame, 字符串表头: List[str], 翻译表: Dict[str, str], columns: List[str]
) -> Tuple[
    List[Dict[str, Union[float, int, str]]],
    DataFrame,
    List[Dict[str, Union[float, int, str]]],
]:
    结果表_导出 = pd.DataFrame([v for _, v in 结果表.items()], columns=columns)
    # use "inplace" otherwise you have to manually assign return values.
    结果表_导出.fillna({elem: "" for elem in 字符串表头}, inplace=True)
    结果表_导出.fillna(
        cmath.nan, inplace=True
    )  # default "nan" or "null" replacement, compatible with type "float"
    结果表_未翻译 = 结果表_导出.to_dict(orient="records")
    结果表_导出 = translateDataframeHeaders(结果表_导出, 翻译表)

    结果表_导出.head()
    # 仿真结果表_导出, 仿真结果表_格式化 = 导出结果表_格式化(仿真结果表,仿真结果字符串表头,FSPT)
    # export_table = 仿真结果表.to_html()
    # may you change the format.
    结果表_格式化 = 结果表_导出.to_dict(orient="records")
    return 结果表_未翻译, 结果表_导出, 结果表_格式化


from networkx.readwrite import json_graph


def calcParamListToMDictList(calcParamList: List):
    mDictList = []
    for calcParam in calcParamList:
        devs, adders, graph_data, G = calcParam
        mDict = json_graph.node_link_data(G)
        mDictList.append(mDict)
    return mDictList


###
def mDictListToCalcParamList(mDictList: List):
    calcParamList = []

    for md in mDictList:
        topo_load = 拓扑图.from_json(md)  # static method, consistency checked
        # print_with_banner(topo_load, "图对象")
        # how to check error now?
        # all connected?

        # topo_load.check_consistency()  # may not need to be checked twice, or you can modify some flag for skipping.
        ## COMPUTE THIS GRAPH ##
        # use devs, adders

        graph_data = topo_load.get_graph_data()
        # print_with_banner(graph_data, "图元数据")
        # objective is contained in the graph data.
        # so all we need to pass to the compute function are: devs, adders, graph_data
        devs = topo_load.get_all_devices()
        adders = topo_load.get_all_adders()
        calcParam = (devs, adders, graph_data, topo_load.G)
        calcParamList.append(calcParam)
    return calcParamList


def translateDataframeHeaders(df: DataFrame, translationTable: Dict[str, str]):
    df_dict = df.to_dict()
    # breakpoint()
    df_dict_translated = {translationTable[k]: v for k, v in df_dict.items()}
    ret = DataFrame(df_dict_translated)
    return ret


# obj_expr = 0
from copy import deepcopy

from ies_optim import ModelWrapperContext, compute

SOLVER_LOG_FNAME = "solver.log"


# disable io_options.
def solve_model(
    mw: ModelWrapper,
    obj_expr,
    sense=minimize,
    # io_options=dict()
):
    OBJ = mw.Objective(expr=obj_expr, sense=sense)

    transformDisjunctiveModel(mw.model)  # right before solving

    solved = False
    with SolverFactory(Solver.cplex) as solver:
        # try:
        # io_options = dict() # disable unicode variables.
        # io_options = dict(symbolic_solver_labels=True)
        # BUG: OOM
        solver.options["timelimit"] = 60 * 24  # solver timeout: 24 minutes.
        solver.options["tune display"] = 3
        solver.options["sifting display"] = 2
        solver.options["mip display"] = 5
        solver.options["barrier display"] = 2
        if ies_env.THREAD_COUNT:
            solver.options["threads"] = ies_env.THREAD_COUNT
        # disable this option to prevent OOM.
        # solver.options["read fileencoding"] = "utf-8"

        logger_print(">>>SOLVING<<<")
        # results = solver.solve(mw.model, tee=True, keepfiles= True)
        # results = solver.solve(mw.model, tee=True, options = dict(mipgap=0.01, emphasis_numerical='y'))
        timestamp = getTimestampForFilename()

        with tempfile.TemporaryDirectory() as solver_log_dir:
            solver_log = os.path.join(solver_log_dir, SOLVER_LOG_FNAME)
            with modelSolvedTestContext(mw.model) as check_solved:
                results = solver.solve(
                    mw.model,
                    tee=True,
                    # io_options=io_options,
                    logfile=solver_log,
                )
                solved = check_solved()

            logger_print("SOLVED?", solved)
            logger_print("SOLVER RESULTS?")
            logger_print(results)

            if not solved:
                # translation could be extremely slow for large models. you have been warned.
                solved = rescue(mw, solver, timestamp, solver_log, results)
        if solved:
            logger_print("OBJ:", value(OBJ))
    return solved


from failsafe_utils import solve_failsafe


def rescue(mw, solver, timestamp, solver_log, results):
    solved = False

    # TODO: make this into background tasks, which will not raise exception and stop failsafe routines
    # TODO: prevent solver log get recycled
    try:
        if ies_env.INFEASIBILITY_DIAGNOSTIC:
            os.mkdir(
                solver_log_dir_with_timestamp := os.path.join(
                    log_dir, f"infeasibility_diagnostic_{timestamp}"
                )
            )
            shutil.move(
                solver_log,
                solver_log_new := os.path.join(
                    solver_log_dir_with_timestamp, SOLVER_LOG_FNAME
                ),
            )

            analyzeInfeasibility(
                mw,
                solver,
                solver_log_new,
                results,
                solver_log_dir_with_timestamp,
            )
    except Exception as e:
        if ies_env.FAILSAFE:
            logger_traceback()
        else:
            raise e

    if ies_env.FAILSAFE:
        failsafe_logdir = os.path.join(log_dir, f"failsafe_{timestamp}")
        os.mkdir(failsafe_logdir)
        solved = solve_failsafe(mw, failsafe_logdir)
    return solved


import sys


def getTimestampForFilename():
    timestamp = (
        str(datetime.datetime.now(timezone))
        .replace(" ", "_")
        .replace("-", "_")
        .replace(".", "_")
        .replace(":", "_")
        .replace("+", "_")
    )
    return timestamp


from plot_utils import plotMultipleTopologies


def analyzeInfeasibility(
    mw: ModelWrapper, solver, solver_log, results, solver_log_dir_with_timestamp
):
    with ErrorManager(default_error="Solver does not have solution.") as em:
        # TODO: plot the model.
        os.mkdir(
            plot_output_dir := os.path.join(
                solver_log_dir_with_timestamp, "topology_plots"
            )
        )
        mDictList = calcParamListToMDictList(
            mw.inputParams.calcParamList
        )  # [(devs, adders, graph_data, topo_load.G), ...]
        plotMultipleTopologies(dict(mDictList=mDictList), plot_output_dir)
        analyzeSolverResults(results, em)

        lp_filepath = os.path.join(solver_log_dir_with_timestamp, "model.lp")
        # TODO: export input parameters.
        # BUG: unserializable object 'Graph' found

        # input_params_filepath = os.path.join(
        #     solver_log_dir_with_timestamp, "input_params.json"
        # )
        # with open(input_params_filepath, "w+") as f:
        #     content = json.dumps(mw.inputParams.dict(), ensure_ascii=False, indent=4)
        #     f.write(content)

        exported_model = ExportedModel(mw.model, lp_filepath)
        export_model_smap = exported_model.smap

        solver_model_smap = mw.model.solutions.symbol_map[solver._smap_id]

        if not cplex_refine_model_and_display_info(
            mw,
            lp_filepath,
            solver_log_dir_with_timestamp,
            export_model_smap,
            # word_counter,
        ):
            em.append("No conflicts found by cplex.")

        # solver_log_new = os.path.join(
        #     solver_log_dir_with_timestamp, os.path.basename(solver_log)
        # )

        # shutil.move(solver_log, solver_log_new)

        em.append("")
        em.append("Solver log saved to: " + solver_log)
        em.append("Model saved to: " + lp_filepath)
        # em.append("Input params saved to: " + input_params_filepath)

        translateFileUsingSymbolMap(lp_filepath, export_model_smap)

        # BUG: solver_log not found (in temp)
        # translate_and_append(solver_log_new, solver_model_smap)
        translateFileUsingSymbolMap(solver_log, solver_model_smap)

        # after translation, begin experiments.
        checkIOUDirectory = os.path.join(solver_log_dir_with_timestamp, "checkIOU")
        os.mkdir(checkIOUDirectory)
        checkInfeasibleOrUnboundedModel(mw, solver, checkIOUDirectory)


def analyzeSolverResults(results, em: ErrorManager):
    if results is not None:
        try:
            checkResult = checkIfSolverHasSolvedModel(results)
            status = checkResult.status
            em.append(status)
            TC = status.terminationCondition
            SS = status.solverStatus
            if TC in IOUTerminationConditions:
                ...
            if TC not in normalTCs:
                em.append(f"abnormal termination condition: {TC}")
            if SS not in normalSSs:
                em.append(f"abnormal solver status: {TC}")
        except:
            em.append("exception while processing solver results")
            with pretty_format_excinfo_context(*sys.exc_info()) as formatted:
                em.append(formatted)


class CalcStruct(BaseModel):
    calcTargetLUT: Dict
    devInstDictList: List[Dict]
    PDList: List[Dict]
    timeParamList: List[Union[float, int]]
    graph_data_list: List
    targetType: str
    extra_data_list: List


def targetTypeAsTargetName(targetType: str):
    targets = targetType.split("_")
    if len(targets) == 1:
        return f"{targets[0]}性最优"
    elif len(targets) == 2:
        return "多目标最优"
    else:
        raise Exception("Invalid targetType: {}".format(targetType))


def getCalcStruct(mw: ModelWrapper, mCalcParamList: list, 典型日, 计算步长, 计算类型):
    calcParamList = deepcopy(mCalcParamList)
    # calcParamList = cast(tuple, deepcopy(mCalcParamList))
    calcTargetLUT = {
        "经济": 0,
        "环保": 0,
        "compensation": 0,
    }

    devInstDictList = []
    PDList = []
    timeParamList = []
    graph_data_list = []
    extra_data_list = []

    targetType = calcParamList[0][2]["计算目标"]  # graph_data @ elem_0

    for calc_id, (devs, adders, graph_data, topo_G) in enumerate(calcParamList):
        典型日ID = calc_id

        if 典型日:
            assert 计算步长 == "小时", f"典型日计算步长异常: {计算步长}"
            graph_data["典型日ID"] = 典型日ID
            timeParam = 每天小时数 * len(graph_data["典型日代表的日期"])
        else:
            timeParam = 每年小时数 if 计算步长 == "小时" else 秒级仿真小时数  # how many hours?
        # timeParam /= 每年小时数  # TODO: eliminate invalid results due to timeParam
        timeParamList.append(timeParam)
        obj_exprs, devInstDict, PD, extra_data = compute(
            # obj_exprs, devInstDict, PD = compute(
            devs,
            adders,
            graph_data,
            topo_G,
            mw,
        )  # single instance.

        # TODO: show & plot compensation

        compensation_expr = (
            0
            if ies_env.ADDER_ERROR_COMPENSATION == "none"
            else extra_data["adder_error_total"][
                f"{ies_env.ADDER_ERROR_COMPENSATION}_error"
            ]
        )
        (
            financial_obj_expr,
            financial_dyn_obj_expr,
            environment_obj_expr,
        ) = obj_exprs

        # handle weights in objectives

        obj_time_param = 1 if not 典型日 else len(graph_data["典型日代表的日期"])
        calcTargetLUT["环保"] += environment_obj_expr * obj_time_param
        calcTargetLUT["经济"] += (
            financial_obj_expr if 计算类型 == "设计规划" else financial_dyn_obj_expr
        ) * obj_time_param
        calcTargetLUT["compensation"] += compensation_expr

        devInstDictList.append(devInstDict)
        PDList.append(PD)
        graph_data_list.append(graph_data)
        extra_data_list.append(extra_data)

    ret = CalcStruct(
        calcTargetLUT=calcTargetLUT,
        devInstDictList=devInstDictList,
        PDList=PDList,
        timeParamList=timeParamList,
        graph_data_list=graph_data_list,
        targetType=targetType,
        extra_data_list=extra_data_list,
    )
    return ret


def add_with_nan(v0, v1):
    if pd.isna(v0):
        return v1
    elif pd.isna(v1):
        return v0
    else:
        return v0 + v1


def 合并结果表(结果, 结果表: dict, 设备模型实例, 不可累加表头: List[str]):
    之前结果 = deepcopy(结果表.get(设备模型实例, None))
    if 之前结果 == None:
        结果表[设备模型实例] = 结果.dict()
    else:
        # TODO: deal with "nan"
        结果表[设备模型实例] = {
            k: add_with_nan(v, 之前结果[k]) for k, v in 结果.dict().items() if k not in 不可累加表头
        }


# TODO: unit test
def fetchResult(solved: bool, ret: CalcStruct, 典型日):
    if solved:
        # try:

        仿真结果表 = {}
        规划结果详情表 = {}
        出力曲线字典 = {}  # 设备ID: 设备出力曲线

        创建出力曲线模版 = lambda: [
            0 for _ in range(每年小时数)
        ]  # 1d array, placed when running under typical day mode.

        @beartype
        def 填充出力曲线(
            出力曲线模版: List[Union[float, int]],
            典型日出力曲线: List[Union[int, float]],
            典型日代表的日期: List[int],
        ):
            assert len(出力曲线模版) == 每年小时数, f"Actual: {len(出力曲线模版)}"
            logger_print(典型日出力曲线)  # ANY? please use "beartype.
            assert len(典型日出力曲线) == 每天小时数, f"Actual: {len(典型日出力曲线)}"
            for day_index in 典型日代表的日期:
                出力曲线模版[day_index * 每天小时数 : (day_index + 1) * 每天小时数] = 典型日出力曲线
            return 出力曲线模版

        仿真结果不可累加表头 = [*(仿真结果字符串表头 := ["元件名称", "元件类型", "设备型号"]), "设备台数"]
        规划结果详情不可累加表头 = [
            *(
                规划结果详情字符串表头 := [
                    "元件名称",
                    "型号",
                ]
            ),
            "数量",
        ]

        for index, devInstDict in enumerate(
            ret.devInstDictList
        ):  # 多个典型日 多个相同拓扑结构的计算图对应的设备模型字典
            graph_data = ret.graph_data_list[index]
            典型日代表的日期 = graph_data["典型日代表的日期"]
            timeParam = ret.timeParamList[index]
            # timeParam = 24 * len(典型日代表的日期) if 典型日 else (8760 if 计算步长 == "小时" else 2)
            # # TODO: fix inconsistent timeParam.
            # timeParam /= 8760
            for devId, devInst in devInstDict.items():
                devClassName = devInst.__class__.__name__.strip("模型")
                # devClassHiddenName = devInst.设备信息.subtype
                # devClassHiddenName = devInst.设备信息.subtype_hidden
                # where you convert the units.
                # devName = devInst.设备信息.设备名称
                结果类 = globals()[f"{devClassName}仿真结果"]  # 一定有的
                出力曲线类 = globals().get(f"{devClassName}出力曲线", None)
                _仿真结果 = 结果 = 结果类.export(devInst, timeParam)
                # 结果.元件类型 = devClassName
                # 结果['元件类型'] = devClassName
                # 结果['元件类型'] = devClassHiddenName
                _规划结果详情 = 规划结果详情.export(devInst, _仿真结果, timeParam)
                # _规划结果详情[] = devClassHiddenName
                # use this as input for planning data export export
                # 仿真结果表.append(结果.dict())
                # 之前结果 = deepcopy(仿真结果表.get(devInst, None))
                # 之前规划结果 = deepcopy(规划结果表.get(devInst, None))

                合并结果表(结果, 仿真结果表, devInst, 仿真结果不可累加表头)
                合并结果表(_规划结果详情, 规划结果详情表, devInst, 规划结果详情不可累加表头)
                # if 之前结果 == None:
                #     仿真结果表[devInst] = 结果.dict()
                # else:
                #     仿真结果表[devInst] = {
                #         k: v + 之前结果[k]
                #         for k, v in 结果.dict().items()
                #         if k not in 仿真结果不可累加表头
                #     }

                if 出力曲线类:
                    出力曲线 = 出力曲线类.export(devInst, timeParam)
                    logger_print("EXPORTING:", 出力曲线类.__name__)
                    # logger_print("EXPORTING:", 出力曲线类.__name__.replace(devClassName, devClassHiddenName))
                    logger_print("DATA:")
                    logger_print(出力曲线)
                    if 典型日:
                        if 出力曲线字典.get(devId, None) is None:
                            出力曲线字典[devId] = {
                                k: 创建出力曲线模版()
                                for k in 出力曲线.dict().keys()
                                if k not in ["元件名称"]
                            }
                        mdict = deepcopy(出力曲线字典[devId])
                        出力曲线字典.update(
                            {
                                devId: {
                                    k: 填充出力曲线(mdict[k], v, 典型日代表的日期)
                                    if isinstance(v, list)
                                    else v
                                    for k, v in 出力曲线.dict().items()
                                }
                            }
                        )
                    else:
                        出力曲线字典.update({devId: 出力曲线.dict()})
        # ############################
        # 仿真结果表_导出 = pd.DataFrame([v for _, v in 仿真结果表.items()], columns=columns)
        # # use "inplace" otherwise you have to manually assign return values.
        # 仿真结果表_导出.fillna({elem: "" for elem in 仿真结果字符串表头}, inplace=True)
        # 仿真结果表_导出.fillna(
        #     cmath.nan, inplace=True
        # )  # default "nan" or "null" replacement, compatible with type "float"
        # 仿真结果表_导出 = translateDataframeHeaders(仿真结果表_导出, FSPT)
        # logger_print()
        # logger_print(出力曲线字典)
        # logger_print()
        # 仿真结果表_导出.head()
        # # 仿真结果表_导出, 仿真结果表_格式化 = 导出结果表_格式化(仿真结果表,仿真结果字符串表头,FSPT)
        # # export_table = 仿真结果表.to_html()
        # # may you change the format.
        # 仿真结果表_格式化 = 仿真结果表_导出.to_dict(orient="records")
        ############################
        logger_print()
        logger_print(出力曲线字典)
        logger_print()
        # breakpoint()
        仿真结果表_未翻译, _, 仿真结果表_格式化 = 导出结果表_格式化(
            仿真结果表, 仿真结果字符串表头, FSPT, simulationResultColumns
        )
        # 仿真结果表_未翻译, _, 仿真结果表_格式化 = 导出结果表_格式化(仿真结果表, 仿真结果字符串表头, FSPT, 仿真结果.schema()['required'])
        # breakpoint()
        规划结果详情表_未翻译, _, 规划结果详情表_格式化 = 导出结果表_格式化(
            规划结果详情表,
            规划结果详情字符串表头,
            规划结果详情.get_translation_table(),
            规划结果详情.schema()["required"],
        )

        simulationResultList = [仿真结果.parse_obj(e) for e in 仿真结果表_格式化]
        planningResultList = [规划结果详情.parse_obj(e) for e in 规划结果详情表_未翻译]
        # return 出力曲线字典, 仿真结果表_格式化
        出力曲线列表 = []
        for devId, content_dict in 出力曲线字典.items():
            deviceName = ret.devInstDictList[0][devId].设备信息.设备名称
            deviceType = ret.devInstDictList[0][devId].__class__.__name__.strip("模型")
            # deviceHiddenType = ret.devInstDictList[0][devId].设备信息.subtype
            # deviceHiddenType = ret.devInstDictList[0][devId].设备信息.subtype_hidden
            elem = {"name": deviceName, "plot_list": []}
            for abbr, val in content_dict.items():
                if abbr in ["元件名称", "时间"]:
                    continue
                # plotName = f"{deviceHiddenType}{abbr}曲线"
                plotName = f"{deviceType}{abbr}曲线"
                # plotName = f"{deviceType}{abbr}出力曲线"
                # xData = content_dict["时间"]
                # override xData.
                # xData = [f'{e}时' for e in range(len(val))]
                xData = list(range(len(val)))
                yData = val
                subElem = {
                    "name": plotName,
                    "abbr": abbr,
                    "data": {"x": xData, "y": yData},
                }
                elem["plot_list"].append(subElem)
            出力曲线列表.append(elem)
        return dict( # TODO: locate and log the error around the problematic adders, and connected devices
            performanceDataList=出力曲线列表,
            simulationResultTable=仿真结果表_格式化,
            objectiveResult=dict(
                financialObjective=value(ret.calcTargetLUT["经济"]),
                environmentalObjective=value(ret.calcTargetLUT["环保"]),
                adderError=value(ret.calcTargetLUT["compensation"]),
            ),
            planningResultTable=规划结果详情表_格式化,
            planningSummary=规划方案概览.export(
                planningResultList,
                simulationResultList,
                FSPT,
                totalAnnualFee=value(ret.calcTargetLUT["经济"]),
                planType=targetTypeAsTargetName(ret.targetType),
            ).translate(),
        )
        # except:
        #     import traceback

        #     traceback.print_exc()
    return None


## assume we have multiobjective here.


class DualObjectiveRange(BaseModel):
    min_finance: float
    fin_env: float
    env_finance: float
    min_env: float


def prepareConstraintRangesFromDualObjectiveRange(
    DOR: DualObjectiveRange, target: Union[Literal["fin"], Literal["env"]]
):
    # min_finance, fin_env = 0, 3
    # env_finance, min_env = 1, 1

    # DOR.min_finance, DOR.fin_env = 0, 3
    # DOR.env_finance, DOR.min_env = 1, 1

    import numpy as np

    if target == "fin":
        a, b = DOR.min_finance, DOR.env_finance
    elif target == "env":
        a, b = DOR.min_env, DOR.fin_env
    else:
        raise Exception("Unsupported target:", target)
    if a == b:
        raise Exception("Unable to perform multiobjective search.")
    elif a > b:
        a, b = b, a
    # a is smaller than b.
    fin_points = np.linspace(a, b, num=11)
    # remove last point to avoid duplicated results.
    # total range count: 9
    fin_points = fin_points[:-1]
    # shall you remove one point.
    constraint_ranges = list(zip(fin_points[:-1].tolist(), fin_points[1:].tolist()))
    for fin_start, fin_end in constraint_ranges:
        logger_print(f"{fin_start} <= {target.upper()} <= {fin_end}")  # constraint
        # min env under this condition. recalculate.
    return constraint_ranges


def solve_model_and_fetch_result(
    calcParamList: List,
    calcTarget: str,
    典型日,
    计算步长,
    计算类型,
    rangeDict: Union[None, Dict] = None,
    needResult: bool = True,
    additional_constraints: Dict = {},
):
    targetNameMappings = dict(
        abbr=dict(经济="fin", 环保="env"), full=dict(经济="finance", 环保="env")
    )
    inputParams = InputParams(
        calcParamList=calcParamList,
        计算目标=calcTarget,
        典型日=典型日,
        计算步长=计算步长,
        计算类型=计算类型,
        rangeDict=rangeDict,
        needResult=needResult,
        additional_constraints=additional_constraints,
    )
    with ModelWrapperContext(inputParams) as mw:
        ret = getCalcStruct(mw, calcParamList, 典型日, 计算步长, 计算类型)
        for expr_name, constraints in additional_constraints.items():
            expr = ret.calcTargetLUT[expr_name]
            min_const = constraints.get("min", None)
            max_const = constraints.get("max", None)
            if min_const:
                mw.Constraint(expr >= min_const)
            if max_const:
                mw.Constraint(expr <= max_const)

        obj_expr = ret.calcTargetLUT[calcTarget]
        compensation_expr = ret.calcTargetLUT["compensation"]
        solved = solve_model(
            mw, obj_expr + compensation_expr * ies_env.ADDER_ERROR_WEIGHT
        )
        # solved = solve_model(mw, obj_expr+compensation_expr)
        # logger_print("compensation:", value(compensation_expr))
        # compensation_val = value(compensation_expr)
        # breakpoint()
        result = None
        if solved:
            if rangeDict is not None:
                rangeDict[f"min_{targetNameMappings['full'][calcTarget]}"] = value(
                    ret.calcTargetLUT[calcTarget]
                )
                for key in targetNameMappings["full"].keys():
                    if key != calcTarget:
                        rangeDict[
                            f"{targetNameMappings['abbr'][calcTarget]}_{targetNameMappings['full'][key]}"
                        ] = value(ret.calcTargetLUT[key])
            if needResult:
                result = fetchResult(solved, ret, 典型日)  # use 'ret' to prepare result.
        return solved, result, rangeDict


# if sys.argv[-1] in ["-f", "--full"]:
def solveModelFromCalcParamList(
    calcParamList: List,
    DEBUG: bool = False,  # replaced by poly degree based verification.
) -> List:
    assert len(calcParamList) >= 1
    # breakpoint()
    firstParam_graphparam = calcParamList[0][2]
    典型日 = firstParam_graphparam["典型日"]
    计算步长 = firstParam_graphparam["计算步长"]
    计算类型 = firstParam_graphparam["计算类型"]
    计算目标 = firstParam_graphparam["计算目标"]

    if 典型日:
        assert len(calcParamList) >= 1  # 允许单典型日计算
        # assert len(calcParamList) > 1
    else:
        assert len(calcParamList) == 1
    # 测试全年8760,没有典型日

    resultList = []

    commonParams = dict(典型日=典型日, 计算步长=计算步长, 计算类型=计算类型)
    # try:
    if 计算目标 in ["经济", "环保"]:
        solved, result, _ = solve_model_and_fetch_result(
            calcParamList, 计算目标, rangeDict={}, **commonParams
        )
        if result:
            resultList.append(result)
    else:
        # breakpoint()
        rangeDict = {}
        solved, fin_result, rangeDict = solve_model_and_fetch_result(
            calcParamList, "经济", rangeDict=rangeDict, **commonParams
        )
        # breakpoint()
        if rangeDict != {} and solved:
            solved, env_result, rangeDict = solve_model_and_fetch_result(
                calcParamList, "环保", rangeDict=rangeDict, **commonParams
            )
            # breakpoint()
            if solved:
                # breakpoint()
                DOR = DualObjectiveRange.parse_obj(rangeDict)

                ### 检验经济环保是否互相影响 ###
                if DOR.fin_env == DOR.min_env:
                    # 环境不影响经济 返回最小经济结果
                    return [fin_result]
                elif DOR.env_finance == DOR.min_finance:
                    # 经济不影响环境 返回最小环保结果
                    return [env_result]

                constraint_ranges = prepareConstraintRangesFromDualObjectiveRange(
                    DOR, target="env"  # add some more paremeters.
                )
                for env_start, env_end in constraint_ranges:
                    # for fin_start, fin_end in constraint_ranges:
                    additional_constraints = {
                        #     "经济": {"min": fin_start, "max": fin_end}
                        "环保": {"min": env_start, "max": env_end}
                    }
                    solved, result, _ = solve_model_and_fetch_result(
                        calcParamList,
                        "经济",
                        rangeDict=None,
                        **commonParams,
                        additional_constraints=additional_constraints
                        # calcParamList, "环保", None, additional_constraints = additional_constraints
                    )
                    if solved:
                        if result:
                            resultList.append(result)
        #### LOOP OF PREPARING SOLUTION ####
    # except:
    #     import traceback

    #     traceback.print_exc()
    #     #         breakpoint()  # you need to turn off these breakpoints in release.
    #     # breakpoint()
    logger_print("SOLVER WORKER END.")
    return resultList
