# Kimodo Houdini Panel

## Launch

In Houdini, open Python Source Editor and run:

```python
exec(open(r"E:/script/pythonWorkSpace/kimodo_houdini/launch_kimodo_panel.py", encoding="utf-8").read())
```

The panel script is:

```text
E:/script/pythonWorkSpace/kimodo_houdini/kimodo_houdini_panel.py
```

## Included Workflow

- Prompts tab
  - Add/delete multiple text prompts.
  - Set per-prompt duration.
  - Load prompts from Kimodo example folders.

- Generate tab
  - Launches the local Kimodo venv executable:
    `E:/script/pythonWorkSpace/.venv-kimodo310/Scripts/kimodo_gen.exe`
  - Supports model, diffusion steps, samples, seed, transition frames, CFG, postprocess, BVH, examples, constraints, and input folder generation.
  - Can auto-import and retarget the generated NPZ to the FBX target.

- Constraints tab
  - Builds Kimodo-compatible `constraints.json` from an existing Kimodo NPZ.
  - Supported types:
    - `root2d`
    - `fullbody`
    - `left-hand`
    - `right-hand`
    - `left-foot`
    - `right-foot`
    - `end-effector`
  - Houdini frame 1 maps to Kimodo frame index 0.

- Visualize tab
  - Switch display between source pose, source MotionClip, target rest, retarget pose, retarget MotionClip, and skinned mesh.
  - Set Houdini frame and focus the viewport.

## Notes

- The panel uses the existing direct NPZ importer and Scaglione retarget setup scripts.
- Auto retarget clears the current Houdini scene because the current retarget builder creates a clean test scene.
- Interactive timeline dragging and viewport pose editing are not yet a full clone of Kimodo's web demo. The first implemented Houdini-native constraint workflow is file-based constraints sampled from NPZ motion.
