# -*- coding: utf-8 -*-
"""Minimal fake ``hou`` module so builder code can run outside Houdini.

Usage in tests::

    module = fake_hou.create_fake_hou(available_hda_types={"studio::cloth_sim::1.0"})
    fake_hou.install(module)
    self.addCleanup(fake_hou.uninstall)
    ...
    obj = module.obj  # the fake /obj node
"""

from __future__ import annotations

import sys
import types


class OperationFailed(Exception):
    pass


class FakeParm:
    def __init__(self, name: str):
        self.name = name
        self.value = None
        self.pressed = 0

    def deleteAllKeyframes(self) -> None:
        pass

    def set(self, value) -> None:
        self.value = value

    def eval(self):
        return self.value

    def pressButton(self) -> None:
        self.pressed += 1


class FakeNodeType:
    def __init__(self, name: str):
        self._name = name

    def name(self) -> str:
        return self._name


class FakeNode:
    def __init__(self, path: str, type_name: str, config: "_Config"):
        self._path = path
        self._type = FakeNodeType(type_name)
        self._config = config
        self.children: dict[str, FakeNode] = {}
        self.parms: dict[str, FakeParm] = {}
        self.indexed_inputs: dict[int, FakeNode] = {}
        self.next_inputs: list[FakeNode] = []
        self.bypassed = False
        self.display = False
        self.render = False
        self.comment = None

    def node(self, name: str):
        return self.children.get(name)

    def createNode(self, type_name: str, name: str) -> "FakeNode":
        if type_name in self._config.fail_node_types:
            raise OperationFailed(f"cannot create node type: {type_name}")
        child = FakeNode(self._path + "/" + name, type_name, self._config)
        self.children[name] = child
        return child

    def parm(self, name: str) -> FakeParm:
        return self.parms.setdefault(name, FakeParm(name))

    def parmTuple(self, name: str):
        if name == "f":
            return (self.parm("f1"), self.parm("f2"))
        if name == "range1":
            return (self.parm("range1x"), self.parm("range1y"), self.parm("range1z"))
        return None

    def path(self) -> str:
        return self._path

    def type(self) -> FakeNodeType:
        return self._type

    def setInput(self, index: int, node: "FakeNode") -> None:
        self.indexed_inputs[index] = node

    def setNextInput(self, node: "FakeNode") -> None:
        self.next_inputs.append(node)

    def bypass(self, value: bool) -> None:
        self.bypassed = value

    def setComment(self, text: str) -> None:
        self.comment = text

    def setGenericFlag(self, flag, value) -> None:
        pass

    def setDisplayFlag(self, value: bool) -> None:
        self.display = value

    def setRenderFlag(self, value: bool) -> None:
        self.render = value

    def layoutChildren(self) -> None:
        pass


class FakeHipFile:
    def __init__(self, fresh: bool = True):
        self.fresh = fresh
        self.loaded: list[str] = []
        self.merged: list[str] = []

    def basename(self) -> str:
        return "untitled.hip" if self.fresh else "shot020_cfx_v001.hip"

    def hasUnsavedChanges(self) -> bool:
        return not self.fresh

    def load(self, path: str, suppress_save_prompt: bool = False) -> None:
        self.loaded.append(path)

    def merge(self, path: str) -> None:
        self.merged.append(path)


class _Config:
    def __init__(self):
        self.fail_node_types: set[str] = set()
        self.available_hda_types: set[str] = set()


def create_fake_hou(
    fresh_session: bool = True,
    available_hda_types=(),
    fail_node_types=(),
) -> types.ModuleType:
    config = _Config()
    config.available_hda_types = set(available_hda_types)
    config.fail_node_types = set(fail_node_types)

    module = types.ModuleType("hou")
    module.nodeFlag = types.SimpleNamespace(DisplayComment="display_comment")
    module.OperationFailed = OperationFailed
    module.hipFile = FakeHipFile(fresh=fresh_session)
    module.sopNodeTypeCategory = lambda: "Sop"
    module.nodeType = (
        lambda category, name: FakeNodeType(name) if name in config.available_hda_types else None
    )

    root = FakeNode("", "root", config)
    obj = root.createNode("obj", "obj")
    out = root.createNode("ropnet", "out")

    def _node(path: str):
        current = root
        for part in path.strip("/").split("/"):
            if not part:
                continue
            current = current.children.get(part)
            if current is None:
                return None
        return current

    module.node = _node
    module.obj = obj  # convenience handles for assertions
    module.out = out
    return module


def install(module: types.ModuleType) -> None:
    sys.modules["hou"] = module


def uninstall() -> None:
    sys.modules.pop("hou", None)
