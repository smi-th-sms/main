import json
import os
import traceback

from alembic.Abc import IArchive, ICompoundProperty


PATHS = [
    "E:/script/pythonWorkSpace/_groom_debug/groom_default_export.abc",
    "E:/script/pythonWorkSpace/_groom_debug/groom_attr_export.abc",
]


def find_object(obj, full_name):
    if obj.getFullName() == full_name:
        return obj
    for index in range(obj.getNumChildren()):
        result = find_object(obj.getChild(index), full_name)
        if result:
            return result
    return None


def prop_names(compound_property):
    names = []
    count = compound_property.getNumProperties()
    for index in range(count):
        header = compound_property.getPropertyHeader(index)
        kind = "unknown"
        for method_name, label in [
            ("isCompound", "compound"),
            ("isScalar", "scalar"),
            ("isArray", "array"),
        ]:
            try:
                if getattr(header, method_name)():
                    kind = label
                    break
            except Exception:
                pass
        names.append(
            {
                "name": header.getName(),
                "meta": str(header.getMetaData()),
                "kind": kind,
            }
        )
    return names


def inspect_curve(obj):
    properties = obj.getProperties()
    geom = ICompoundProperty(properties, ".geom")
    geom_props = prop_names(geom)
    arb_props = None
    for prop in geom_props:
        if prop["name"] == ".arbGeomParams":
            arb = ICompoundProperty(geom, ".arbGeomParams")
            arb_props = prop_names(arb)
            break

    row = {
        "metadata": str(obj.getMetaData()),
        "object_properties": prop_names(properties),
        "geom_properties": geom_props,
        "arb_geom_properties": arb_props,
    }

    return row


def inspect_file(path):
    archive = IArchive(path)
    top = archive.getTop()
    result = {
        "size": os.path.getsize(path),
        "curves": {},
    }

    for full_name in ["/groom/curves/group_id_0", "/groom/guides/group_id_0"]:
        try:
            obj = find_object(top, full_name)
            if not obj:
                result["curves"][full_name] = {"found": False}
                continue
            result["curves"][full_name] = inspect_curve(obj)
        except Exception:
            result["curves"][full_name] = {"error": traceback.format_exc()}

    return result


output = {}
for path in PATHS:
    try:
        output[os.path.basename(path)] = inspect_file(path)
    except Exception:
        output[os.path.basename(path)] = {"error": traceback.format_exc()}

print(json.dumps(output, indent=2, ensure_ascii=False))
