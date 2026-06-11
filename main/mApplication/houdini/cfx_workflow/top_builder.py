# -*- coding: utf-8 -*-
"""Convert a WorkflowPlan into a Houdini TOPs/PDG node network."""

from __future__ import annotations

import json
from typing import Any

from .schema import WorkflowPlan, WorkflowStage, WorkflowTask

# Stages that fetch a ROP output get a ropfetch node; everything else gets a
# pythonscript stub that a real executor can fill in per stage.
_ROPFETCH_STAGES = {WorkflowStage.SIM_CACHE, WorkflowStage.PREVIEW}


def build_top_network(plan: WorkflowPlan, parent_path: str = "/obj") -> dict[str, Any]:
    """Build a TOP network mirroring the workflow plan's task graph.

    This function must be called inside Houdini because it imports ``hou``.

    One TOP node is created per task, named after ``task_id``, and wired
    according to ``depends_on``. ``sim_cache``/``preview`` tasks become
    ``ropfetch`` nodes pointing at the shot builder's ``write_cfx_cache``
    ROPs; other stages become ``pythonscript`` stubs carrying the task
    payload. Tasks whose status is ``skipped`` or ``blocked`` are created
    bypassed so the graph stays complete but does not cook them.

    Returns a structured result::

        {
            "shot_id": str,
            "topnet": str,                       # TOP network path
            "nodes": {
                task_id: {"path": str, "type": str, "status": str, "bypassed": bool},
            },
            "warnings": list[str],
        }
    """

    try:
        import hou  # type: ignore
    except ImportError as exc:
        raise RuntimeError("build_top_network must run inside Houdini") from exc

    parent = hou.node(parent_path)
    if parent is None:
        raise RuntimeError(f"Could not find parent node: {parent_path}")

    shot = plan.shot
    warnings: list[str] = []
    topnet_name = f"cfx_top_{shot.sequence}_{shot.shot}"
    topnet = parent.node(topnet_name) or parent.createNode("topnet", topnet_name)
    topnet.setComment(f"CFX workflow TOP graph for {shot.shot_id}")
    topnet.setGenericFlag(hou.nodeFlag.DisplayComment, True)

    result: dict[str, Any] = {
        "shot_id": shot.shot_id,
        "topnet": topnet.path(),
        "nodes": {},
        "warnings": warnings,
    }

    nodes: dict[str, Any] = {}
    last_node = None
    for task in plan.tasks:
        node = _create_task_node(hou, topnet, plan, task, warnings)
        nodes[task.task_id] = node
        bypassed = task.status in {"skipped", "blocked"}
        if bypassed:
            node.bypass(True)
        result["nodes"][task.task_id] = {
            "path": node.path(),
            "type": node.type().name(),
            "status": task.status,
            "bypassed": bypassed,
        }
        last_node = node

    for task in plan.tasks:
        node = nodes[task.task_id]
        for dep_id in task.depends_on:
            dep_node = nodes.get(dep_id)
            if dep_node is None:
                warnings.append(
                    f"{task.task_id}: dependency '{dep_id}' has no node; input left unconnected"
                )
                continue
            node.setNextInput(dep_node)

    if last_node is not None:
        last_node.setDisplayFlag(True)

    topnet.layoutChildren()
    return result


def _create_task_node(hou, topnet, plan: WorkflowPlan, task: WorkflowTask, warnings: list[str]):
    node_name = task.task_id.replace(" ", "_")
    existing = topnet.node(node_name)
    if existing is not None:
        return existing

    type_name = "ropfetch" if task.stage in _ROPFETCH_STAGES else "pythonscript"
    try:
        node = topnet.createNode(type_name, node_name)
    except hou.OperationFailed as exc:
        warnings.append(
            f"{task.task_id}: could not create '{type_name}' TOP node ({exc}); created null instead"
        )
        return topnet.createNode("null", node_name)

    node.setComment(f"[{task.stage.value}] {task.label}")
    node.setGenericFlag(hou.nodeFlag.DisplayComment, True)

    if type_name == "ropfetch":
        _configure_ropfetch(hou, node, plan, task, warnings)
    else:
        _configure_pythonscript(node, plan, task, warnings)
    return node


def _configure_ropfetch(hou, node, plan: WorkflowPlan, task: WorkflowTask, warnings: list[str]) -> None:
    shot = plan.shot
    asset_name = task.metadata.get("asset")
    cfx_type = task.metadata.get("cfx_type")
    if task.stage is WorkflowStage.SIM_CACHE and asset_name and cfx_type:
        rop_path = (
            f"/obj/cfx_{shot.sequence}_{shot.shot}/"
            f"{cfx_type}_{asset_name}".replace(" ", "_") + "/write_cfx_cache"
        )
        _set_parm(node, "roppath", rop_path, task.task_id, warnings)
    else:
        warnings.append(
            f"{task.task_id}: no ROP target resolved; set 'roppath' on {node.path()} manually"
        )

    # Cook the fetched ROP once over the shot frame range.
    if node.parm("framegeneration") is not None:
        _set_parm(node, "framegeneration", 1, task.task_id, warnings)
    range_parms = node.parmTuple("range1")
    if range_parms is not None:
        for parm, value in zip(range_parms, (shot.frame_start, shot.frame_end, 1)):
            parm.deleteAllKeyframes()
            parm.set(value)
    else:
        warnings.append(f"{task.task_id}: frame range parm 'range1' not found on {node.path()}")


def _configure_pythonscript(node, plan: WorkflowPlan, task: WorkflowTask, warnings: list[str]) -> None:
    payload = json.dumps(task.as_dict(), ensure_ascii=True, indent=2)
    shot_payload = json.dumps(plan.shot.as_dict(), ensure_ascii=True, indent=2)
    script = (
        "import json\n"
        f"task = json.loads(r'''{payload}''')\n"
        f"shot_config = json.loads(r'''{shot_payload}''')\n"
        "try:\n"
        "    from main.mApplication.houdini.cfx_workflow import executors\n"
        "except ImportError as exc:\n"
        "    print('CFX task (executors not importable):', task['task_id'], '|', exc)\n"
        "else:\n"
        "    result = executors.execute_payload(task, shot_config)\n"
        "    print(json.dumps(result, ensure_ascii=False, indent=2))\n"
        "    if result['status'] == 'failed':\n"
        "        raise RuntimeError(result['message'])\n"
    )
    _set_parm(node, "script", script, task.task_id, warnings)


def _set_parm(node, parm_name: str, value: Any, task_id: str, warnings: list[str]) -> bool:
    parm = node.parm(parm_name)
    if parm is None:
        warnings.append(f"{task_id}: parameter '{parm_name}' not found on {node.path()}")
        return False
    try:
        parm.deleteAllKeyframes()
        parm.set(value)
    except Exception as exc:
        warnings.append(f"{task_id}: failed to set '{parm_name}' on {node.path()}: {exc}")
        return False
    return True
