# Automatically generated script by Houdini 21.0.440
# This file reproduces the geometric hierarchy of a motion capture file
# 
fset 2
frange 1 2
fps 30.000030000029998
set saved_path = `execute("oppwf")`
opcf /obj
set subnet = `run("opadd -n -v subnet E__script_pythonWorkSpace_kimodo_test_outputs_minimal_test")`
opautoplace $subnet
opcf $subnet


# Create Skeleton Root
opadd null Hips
opset -y on Hips
chadd Hips tx ty tz
chkey -f 1 -F 'chop("../mocap/data/Hips:tx")' Hips/tx
chkey -f 1 -F 'chop("../mocap/data/Hips:ty")' Hips/ty
chkey -f 1 -F 'chop("../mocap/data/Hips:tz")' Hips/tz


# Create Skeleton Bones
opadd -n bone Hips_To_Chest
chlock Hips_To_Chest +tx +ty +tz
opset -y on Hips_To_Chest
opparm Hips_To_Chest dcolor ( 1 0 0 )
opwire Hips -0 Hips_To_Chest
"$HH/scripts/obj/bone.cmd" Hips_To_Chest 1
opparm Hips_To_Chest crtopcap (0.29999999999999999 0.29999999999999999 0.40000000000000002) crbotcap (0.29999999999999999 0.29999999999999999 0.40000000000000002)
opparm Hips_To_Chest length 10
chadd Hips_To_Chest rx ry rz
chkey -f 1 -F 'chop("../mocap/data/Hips_To_Chest:rx")' Hips_To_Chest/rx
chkey -f 1 -F 'chop("../mocap/data/Hips_To_Chest:ry")' Hips_To_Chest/ry
chkey -f 1 -F 'chop("../mocap/data/Hips_To_Chest:rz")' Hips_To_Chest/rz

opadd -n bone Chest_To_ChestEnd
chlock Chest_To_ChestEnd +tx +ty +tz
opset -y on Chest_To_ChestEnd
opparm Chest_To_ChestEnd dcolor ( 0.85410207509994507 0 1 )
opwire Hips_To_Chest -0 Chest_To_ChestEnd
"$HH/scripts/obj/bone.cmd" Chest_To_ChestEnd
opparm Chest_To_ChestEnd crtopcap (0.29999999999999999 0.29999999999999999 0.40000000000000002) crbotcap (0.29999999999999999 0.29999999999999999 0.40000000000000002)
opparm Chest_To_ChestEnd length 10
chadd Chest_To_ChestEnd rx ry rz
chkey -f 1 -F 'chop("../mocap/data/Chest_To_ChestEnd:rx")' Chest_To_ChestEnd/rx
chkey -f 1 -F 'chop("../mocap/data/Chest_To_ChestEnd:ry")' Chest_To_ChestEnd/ry
chkey -f 1 -F 'chop("../mocap/data/Chest_To_ChestEnd:rz")' Chest_To_ChestEnd/rz



# Create CHOP net to store this motion
opadd chopnet mocap
opcf mocap
opadd file E__script_pythonWorkSpace_kimodo_test_outputs_minimal_test
opparm E__script_pythonWorkSpace_kimodo_test_outputs_minimal_test file ( '$HIP/E:\script\pythonWorkSpace\kimodo_test_outputs\minimal_test.bclip' ) rate (30.000030000029998) rateoption ( override ) export ( ../.. )
opadd null data
opparm data export ( ../.. )
opwire E__script_pythonWorkSpace_kimodo_test_outputs_minimal_test -0 data
oplayout
opcf ..

# Layout the object nodes
oplayout
opautoplace mocap


opcf $saved_path
