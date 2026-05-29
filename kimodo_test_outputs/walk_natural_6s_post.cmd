# Automatically generated script by Houdini 21.0.440
# This file reproduces the geometric hierarchy of a motion capture file
# 
fset 180
frange 1 180
fps 30
set saved_path = `execute("oppwf")`
opcf /obj
set subnet = `run("opadd -n -v subnet E__script_pythonWorkSpace_kimodo_test_outputs_walk_natural_6s_post")`
opautoplace $subnet
opcf $subnet


# Create Skeleton Root
opadd null Root
opset -y on Root
chadd Root tx ty tz
chkey -f 1 -F 'chop("../mocap/data/Root:tx")' Root/tx
chkey -f 1 -F 'chop("../mocap/data/Root:ty")' Root/ty
chkey -f 1 -F 'chop("../mocap/data/Root:tz")' Root/tz


# Create Skeleton Bones
opadd -n bone Root_To_Hips
chlock Root_To_Hips +tx +ty +tz
opset -y on Root_To_Hips
opparm Root_To_Hips dcolor ( 1 0 0 )
opwire Root -0 Root_To_Hips
"$HH/scripts/obj/bone.cmd" Root_To_Hips 1
opparm Root_To_Hips crtopcap (0.29999999999999999 0.29999999999999999 0.40000000000000002) crbotcap (0.29999999999999999 0.29999999999999999 0.40000000000000002)
opparm Root_To_Hips length 100
chadd Root_To_Hips rx ry rz
chkey -f 1 -F 'chop("../mocap/data/Root_To_Hips:rx")' Root_To_Hips/rx
chkey -f 1 -F 'chop("../mocap/data/Root_To_Hips:ry")' Root_To_Hips/ry
chkey -f 1 -F 'chop("../mocap/data/Root_To_Hips:rz")' Root_To_Hips/rz

opadd -n bone Hips_To_Spine1
chlock Hips_To_Spine1 +tx +ty +tz
opset -y on Hips_To_Spine1
opparm Hips_To_Spine1 dcolor ( 0.85410207509994507 0 1 )
opwire Root_To_Hips -0 Hips_To_Spine1
"$HH/scripts/obj/bone.cmd" Hips_To_Spine1
opparm Hips_To_Spine1 crtopcap (0.29999999999999999 0.29999999999999999 0.40000000000000002) crbotcap (0.29999999999999999 0.29999999999999999 0.40000000000000002)
opparm Hips_To_Spine1 length 5.0040693147611375
chadd Hips_To_Spine1 rx ry rz
chkey -f 1 -F 'chop("../mocap/data/Hips_To_Spine1:rx")' Hips_To_Spine1/rx
chkey -f 1 -F 'chop("../mocap/data/Hips_To_Spine1:ry")' Hips_To_Spine1/ry
chkey -f 1 -F 'chop("../mocap/data/Hips_To_Spine1:rz")' Hips_To_Spine1/rz

opadd -n bone Spine1_To_Spine2
chlock Spine1_To_Spine2 +tx +ty +tz
opset -y on Spine1_To_Spine2
opparm Spine1_To_Spine2 dcolor ( 0 0.29179611802101135 1 )
opwire Hips_To_Spine1 -0 Spine1_To_Spine2
"$HH/scripts/obj/bone.cmd" Spine1_To_Spine2
opparm Spine1_To_Spine2 crtopcap (0.29999999999999999 0.29999999999999999 0.40000000000000002) crbotcap (0.29999999999999999 0.29999999999999999 0.40000000000000002)
opparm Spine1_To_Spine2 length 7.1253630000000703
chadd Spine1_To_Spine2 rx ry rz
chkey -f 1 -F 'chop("../mocap/data/Spine1_To_Spine2:rx")' Spine1_To_Spine2/rx
chkey -f 1 -F 'chop("../mocap/data/Spine1_To_Spine2:ry")' Spine1_To_Spine2/ry
chkey -f 1 -F 'chop("../mocap/data/Spine1_To_Spine2:rz")' Spine1_To_Spine2/rz

opadd -n bone Spine2_To_Chest
chlock Spine2_To_Chest +tx +ty +tz
opset -y on Spine2_To_Chest
opparm Spine2_To_Chest dcolor ( 0 1 0.5623059868812561 )
opwire Spine1_To_Spine2 -0 Spine2_To_Chest
"$HH/scripts/obj/bone.cmd" Spine2_To_Chest
opparm Spine2_To_Chest crtopcap (0.29999999999999999 0.29999999999999999 0.40000000000000002) crbotcap (0.29999999999999999 0.29999999999999999 0.40000000000000002)
opparm Spine2_To_Chest length 7.5940270000000654
chadd Spine2_To_Chest rx ry rz
chkey -f 1 -F 'chop("../mocap/data/Spine2_To_Chest:rx")' Spine2_To_Chest/rx
chkey -f 1 -F 'chop("../mocap/data/Spine2_To_Chest:ry")' Spine2_To_Chest/ry
chkey -f 1 -F 'chop("../mocap/data/Spine2_To_Chest:rz")' Spine2_To_Chest/rz

opadd -n bone Chest_To_Neck1
chlock Chest_To_Neck1 +tx +ty +tz
opset -y on Chest_To_Neck1
opparm Chest_To_Neck1 dcolor ( 0.58359211683273315 1 0 )
opwire Spine2_To_Chest -0 Chest_To_Neck1
"$HH/scripts/obj/bone.cmd" Chest_To_Neck1
opparm Chest_To_Neck1 crtopcap (0.29999999999999999 0.29999999999999999 0.40000000000000002) crbotcap (0.29999999999999999 0.29999999999999999 0.40000000000000002)
opparm Chest_To_Neck1 length 26.317738312266954
chadd Chest_To_Neck1 rx ry rz
chkey -f 1 -F 'chop("../mocap/data/Chest_To_Neck1:rx")' Chest_To_Neck1/rx
chkey -f 1 -F 'chop("../mocap/data/Chest_To_Neck1:ry")' Chest_To_Neck1/ry
chkey -f 1 -F 'chop("../mocap/data/Chest_To_Neck1:rz")' Chest_To_Neck1/rz

opadd -n bone Neck1_To_Neck2
chlock Neck1_To_Neck2 +tx +ty +tz
opset -y on Neck1_To_Neck2
opparm Neck1_To_Neck2 dcolor ( 1 0.27050983905792236 0 )
opwire Chest_To_Neck1 -0 Neck1_To_Neck2
"$HH/scripts/obj/bone.cmd" Neck1_To_Neck2
opparm Neck1_To_Neck2 crtopcap (0.29999999999999999 0.29999999999999999 0.40000000000000002) crbotcap (0.29999999999999999 0.29999999999999999 0.40000000000000002)
opparm Neck1_To_Neck2 length 8.0459110000000003
chadd Neck1_To_Neck2 rx ry rz
chkey -f 1 -F 'chop("../mocap/data/Neck1_To_Neck2:rx")' Neck1_To_Neck2/rx
chkey -f 1 -F 'chop("../mocap/data/Neck1_To_Neck2:ry")' Neck1_To_Neck2/ry
chkey -f 1 -F 'chop("../mocap/data/Neck1_To_Neck2:rz")' Neck1_To_Neck2/rz

opadd -n bone Neck2_To_Head
chlock Neck2_To_Head +tx +ty +tz
opset -y on Neck2_To_Head
opparm Neck2_To_Head dcolor ( 1 0 0.87538808584213257 )
opwire Neck1_To_Neck2 -0 Neck2_To_Head
"$HH/scripts/obj/bone.cmd" Neck2_To_Head
opparm Neck2_To_Head crtopcap (0.29999999999999999 0.29999999999999999 0.40000000000000002) crbotcap (0.29999999999999999 0.29999999999999999 0.40000000000000002)
opparm Neck2_To_Head length 6.4327740000000002
chadd Neck2_To_Head rx ry rz
chkey -f 1 -F 'chop("../mocap/data/Neck2_To_Head:rx")' Neck2_To_Head/rx
chkey -f 1 -F 'chop("../mocap/data/Neck2_To_Head:ry")' Neck2_To_Head/ry
chkey -f 1 -F 'chop("../mocap/data/Neck2_To_Head:rz")' Neck2_To_Head/rz

opadd -n bone Head_To_HeadEnd
chlock Head_To_HeadEnd +tx +ty +tz
opset -y on Head_To_HeadEnd
opparm Head_To_HeadEnd dcolor ( 0 0.021286265924572945 1 )
opwire Neck2_To_Head -0 Head_To_HeadEnd
"$HH/scripts/obj/bone.cmd" Head_To_HeadEnd
opparm Head_To_HeadEnd crtopcap (0.29999999999999999 0.29999999999999999 0.40000000000000002) crbotcap (0.29999999999999999 0.29999999999999999 0.40000000000000002)
opparm Head_To_HeadEnd length 16.169902087397713
chadd Head_To_HeadEnd rx ry rz
chkey -f 1 -F 'chop("../mocap/data/Head_To_HeadEnd:rx")' Head_To_HeadEnd/rx
chkey -f 1 -F 'chop("../mocap/data/Head_To_HeadEnd:ry")' Head_To_HeadEnd/ry
chkey -f 1 -F 'chop("../mocap/data/Head_To_HeadEnd:rz")' Head_To_HeadEnd/rz

opadd -n bone Head_To_Jaw
chlock Head_To_Jaw +tx +ty +tz
opset -y on Head_To_Jaw
opparm Head_To_Jaw dcolor ( 0 1 0.83281582593917847 )
opwire Neck2_To_Head -0 Head_To_Jaw
"$HH/scripts/obj/bone.cmd" Head_To_Jaw
opparm Head_To_Jaw crtopcap (0.29999999999999999 0.29999999999999999 0.40000000000000002) crbotcap (0.29999999999999999 0.29999999999999999 0.40000000000000002)
opparm Head_To_Jaw length 3.1312698308836304
chadd Head_To_Jaw rx ry rz
chkey -f 1 -F 'chop("../mocap/data/Head_To_Jaw:rx")' Head_To_Jaw/rx
chkey -f 1 -F 'chop("../mocap/data/Head_To_Jaw:ry")' Head_To_Jaw/ry
chkey -f 1 -F 'chop("../mocap/data/Head_To_Jaw:rz")' Head_To_Jaw/rz

opadd -n bone Head_To_LeftEye
chlock Head_To_LeftEye +tx +ty +tz
opset -y on Head_To_LeftEye
opparm Head_To_LeftEye dcolor ( 0.3130822479724884 1 0 )
opwire Neck2_To_Head -0 Head_To_LeftEye
"$HH/scripts/obj/bone.cmd" Head_To_LeftEye
opparm Head_To_LeftEye crtopcap (0.29999999999999999 0.29999999999999999 0.40000000000000002) crbotcap (0.29999999999999999 0.29999999999999999 0.40000000000000002)
opparm Head_To_LeftEye length 9.8381029150667558
chadd Head_To_LeftEye rx ry rz
chkey -f 1 -F 'chop("../mocap/data/Head_To_LeftEye:rx")' Head_To_LeftEye/rx
chkey -f 1 -F 'chop("../mocap/data/Head_To_LeftEye:ry")' Head_To_LeftEye/ry
chkey -f 1 -F 'chop("../mocap/data/Head_To_LeftEye:rz")' Head_To_LeftEye/rz

opadd -n bone Head_To_RightEye
chlock Head_To_RightEye +tx +ty +tz
opset -y on Head_To_RightEye
opparm Head_To_RightEye dcolor ( 1 0.54101967811584473 0 )
opwire Neck2_To_Head -0 Head_To_RightEye
"$HH/scripts/obj/bone.cmd" Head_To_RightEye
opparm Head_To_RightEye crtopcap (0.29999999999999999 0.29999999999999999 0.40000000000000002) crbotcap (0.29999999999999999 0.29999999999999999 0.40000000000000002)
opparm Head_To_RightEye length 9.8112508955601569
chadd Head_To_RightEye rx ry rz
chkey -f 1 -F 'chop("../mocap/data/Head_To_RightEye:rx")' Head_To_RightEye/rx
chkey -f 1 -F 'chop("../mocap/data/Head_To_RightEye:ry")' Head_To_RightEye/ry
chkey -f 1 -F 'chop("../mocap/data/Head_To_RightEye:rz")' Head_To_RightEye/rz

opadd -n bone Chest_To_LeftShoulder
chlock Chest_To_LeftShoulder +tx +ty +tz
opset -y on Chest_To_LeftShoulder
opparm Chest_To_LeftShoulder dcolor ( 1 0 0.60487824678421021 )
opwire Spine2_To_Chest -0 Chest_To_LeftShoulder
"$HH/scripts/obj/bone.cmd" Chest_To_LeftShoulder
opparm Chest_To_LeftShoulder crtopcap (0.29999999999999999 0.29999999999999999 0.40000000000000002) crbotcap (0.29999999999999999 0.29999999999999999 0.40000000000000002)
opparm Chest_To_LeftShoulder length 23.848320283804181
chadd Chest_To_LeftShoulder rx ry rz
chkey -f 1 -F 'chop("../mocap/data/Chest_To_LeftShoulder:rx")' Chest_To_LeftShoulder/rx
chkey -f 1 -F 'chop("../mocap/data/Chest_To_LeftShoulder:ry")' Chest_To_LeftShoulder/ry
chkey -f 1 -F 'chop("../mocap/data/Chest_To_LeftShoulder:rz")' Chest_To_LeftShoulder/rz

opadd -n bone LeftShoulder_To_LeftArm
chlock LeftShoulder_To_LeftArm +tx +ty +tz
opset -y on LeftShoulder_To_LeftArm
opparm LeftShoulder_To_LeftArm dcolor ( 0.24922357499599457 0 1 )
opwire Chest_To_LeftShoulder -0 LeftShoulder_To_LeftArm
"$HH/scripts/obj/bone.cmd" LeftShoulder_To_LeftArm
opparm LeftShoulder_To_LeftArm crtopcap (0.29999999999999999 0.29999999999999999 0.40000000000000002) crbotcap (0.29999999999999999 0.29999999999999999 0.40000000000000002)
opparm LeftShoulder_To_LeftArm length 15.902118000000252
chadd LeftShoulder_To_LeftArm rx ry rz
chkey -f 1 -F 'chop("../mocap/data/LeftShoulder_To_LeftArm:rx")' LeftShoulder_To_LeftArm/rx
chkey -f 1 -F 'chop("../mocap/data/LeftShoulder_To_LeftArm:ry")' LeftShoulder_To_LeftArm/ry
chkey -f 1 -F 'chop("../mocap/data/LeftShoulder_To_LeftArm:rz")' LeftShoulder_To_LeftArm/rz

opadd -n bone LeftArm_To_LeftForeArm
chlock LeftArm_To_LeftForeArm +tx +ty +tz
opset -y on LeftArm_To_LeftForeArm
opparm LeftArm_To_LeftForeArm dcolor ( 0 0.89667433500289917 1 )
opwire LeftShoulder_To_LeftArm -0 LeftArm_To_LeftForeArm
"$HH/scripts/obj/bone.cmd" LeftArm_To_LeftForeArm
opparm LeftArm_To_LeftForeArm crtopcap (0.29999999999999999 0.29999999999999999 0.40000000000000002) crbotcap (0.29999999999999999 0.29999999999999999 0.40000000000000002)
opparm LeftArm_To_LeftForeArm length 28.739307000000018
chadd LeftArm_To_LeftForeArm rx ry rz
chkey -f 1 -F 'chop("../mocap/data/LeftArm_To_LeftForeArm:rx")' LeftArm_To_LeftForeArm/rx
chkey -f 1 -F 'chop("../mocap/data/LeftArm_To_LeftForeArm:ry")' LeftArm_To_LeftForeArm/ry
chkey -f 1 -F 'chop("../mocap/data/LeftArm_To_LeftForeArm:rz")' LeftArm_To_LeftForeArm/rz

opadd -n bone LeftForeArm_To_LeftHand
chlock LeftForeArm_To_LeftHand +tx +ty +tz
opset -y on LeftForeArm_To_LeftHand
opparm LeftForeArm_To_LeftHand dcolor ( 0.042572531849145889 1 0 )
opwire LeftArm_To_LeftForeArm -0 LeftForeArm_To_LeftHand
"$HH/scripts/obj/bone.cmd" LeftForeArm_To_LeftHand
opparm LeftForeArm_To_LeftHand crtopcap (0.29999999999999999 0.29999999999999999 0.40000000000000002) crbotcap (0.29999999999999999 0.29999999999999999 0.40000000000000002)
opparm LeftForeArm_To_LeftHand length 27.093981000000294
chadd LeftForeArm_To_LeftHand rx ry rz
chkey -f 1 -F 'chop("../mocap/data/LeftForeArm_To_LeftHand:rx")' LeftForeArm_To_LeftHand/rx
chkey -f 1 -F 'chop("../mocap/data/LeftForeArm_To_LeftHand:ry")' LeftForeArm_To_LeftHand/ry
chkey -f 1 -F 'chop("../mocap/data/LeftForeArm_To_LeftHand:rz")' LeftForeArm_To_LeftHand/rz

opadd -n bone LeftHand_To_LeftHandThumb1
chlock LeftHand_To_LeftHandThumb1 +tx +ty +tz
opset -y on LeftHand_To_LeftHandThumb1
opparm LeftHand_To_LeftHandThumb1 dcolor ( 1 0.81152945756912231 0 )
opwire LeftForeArm_To_LeftHand -0 LeftHand_To_LeftHandThumb1
"$HH/scripts/obj/bone.cmd" LeftHand_To_LeftHandThumb1
opparm LeftHand_To_LeftHandThumb1 crtopcap (0.29999999999999999 0.29999999999999999 0.40000000000000002) crbotcap (0.29999999999999999 0.29999999999999999 0.40000000000000002)
opparm LeftHand_To_LeftHandThumb1 length 4.1599607188814902
chadd LeftHand_To_LeftHandThumb1 rx ry rz
chkey -f 1 -F 'chop("../mocap/data/LeftHand_To_LeftHandThumb1:rx")' LeftHand_To_LeftHandThumb1/rx
chkey -f 1 -F 'chop("../mocap/data/LeftHand_To_LeftHandThumb1:ry")' LeftHand_To_LeftHandThumb1/ry
chkey -f 1 -F 'chop("../mocap/data/LeftHand_To_LeftHandThumb1:rz")' LeftHand_To_LeftHandThumb1/rz

opadd -n bone LeftHandThumb1_To_LeftHandThumb2
chlock LeftHandThumb1_To_LeftHandThumb2 +tx +ty +tz
opset -y on LeftHandThumb1_To_LeftHandThumb2
opparm LeftHandThumb1_To_LeftHandThumb2 dcolor ( 1 0 0.33436837792396545 )
opwire LeftHand_To_LeftHandThumb1 -0 LeftHandThumb1_To_LeftHandThumb2
"$HH/scripts/obj/bone.cmd" LeftHandThumb1_To_LeftHandThumb2
opparm LeftHandThumb1_To_LeftHandThumb2 crtopcap (0.29999999999999999 0.29999999999999999 0.40000000000000002) crbotcap (0.29999999999999999 0.29999999999999999 0.40000000000000002)
opparm LeftHandThumb1_To_LeftHandThumb2 length 4.705309000000212
chadd LeftHandThumb1_To_LeftHandThumb2 rx ry rz
chkey -f 1 -F 'chop("../mocap/data/LeftHandThumb1_To_LeftHandThumb2:rx")' LeftHandThumb1_To_LeftHandThumb2/rx
chkey -f 1 -F 'chop("../mocap/data/LeftHandThumb1_To_LeftHandThumb2:ry")' LeftHandThumb1_To_LeftHandThumb2/ry
chkey -f 1 -F 'chop("../mocap/data/LeftHandThumb1_To_LeftHandThumb2:rz")' LeftHandThumb1_To_LeftHandThumb2/rz

opadd -n bone LeftHandThumb2_To_LeftHandThumb3
chlock LeftHandThumb2_To_LeftHandThumb3 +tx +ty +tz
opset -y on LeftHandThumb2_To_LeftHandThumb3
opparm LeftHandThumb2_To_LeftHandThumb3 dcolor ( 0.51973319053649902 0 1 )
opwire LeftHandThumb1_To_LeftHandThumb2 -0 LeftHandThumb2_To_LeftHandThumb3
"$HH/scripts/obj/bone.cmd" LeftHandThumb2_To_LeftHandThumb3
opparm LeftHandThumb2_To_LeftHandThumb3 crtopcap (0.29999999999999999 0.29999999999999999 0.40000000000000002) crbotcap (0.29999999999999999 0.29999999999999999 0.40000000000000002)
opparm LeftHandThumb2_To_LeftHandThumb3 length 2.7985150000016081
chadd LeftHandThumb2_To_LeftHandThumb3 rx ry rz
chkey -f 1 -F 'chop("../mocap/data/LeftHandThumb2_To_LeftHandThumb3:rx")' LeftHandThumb2_To_LeftHandThumb3/rx
chkey -f 1 -F 'chop("../mocap/data/LeftHandThumb2_To_LeftHandThumb3:ry")' LeftHandThumb2_To_LeftHandThumb3/ry
chkey -f 1 -F 'chop("../mocap/data/LeftHandThumb2_To_LeftHandThumb3:rz")' LeftHandThumb2_To_LeftHandThumb3/rz

opadd -n bone LeftHandThumb3_To_LeftHandThumbEnd
chlock LeftHandThumb3_To_LeftHandThumbEnd +tx +ty +tz
opset -y on LeftHandThumb3_To_LeftHandThumbEnd
opparm LeftHandThumb3_To_LeftHandThumbEnd dcolor ( 0 0.62616449594497681 1 )
opwire LeftHandThumb2_To_LeftHandThumb3 -0 LeftHandThumb3_To_LeftHandThumbEnd
"$HH/scripts/obj/bone.cmd" LeftHandThumb3_To_LeftHandThumbEnd
opparm LeftHandThumb3_To_LeftHandThumbEnd crtopcap (0.29999999999999999 0.29999999999999999 0.40000000000000002) crbotcap (0.29999999999999999 0.29999999999999999 0.40000000000000002)
opparm LeftHandThumb3_To_LeftHandThumbEnd length 3.1807930000050302
chadd LeftHandThumb3_To_LeftHandThumbEnd rx ry rz
chkey -f 1 -F 'chop("../mocap/data/LeftHandThumb3_To_LeftHandThumbEnd:rx")' LeftHandThumb3_To_LeftHandThumbEnd/rx
chkey -f 1 -F 'chop("../mocap/data/LeftHandThumb3_To_LeftHandThumbEnd:ry")' LeftHandThumb3_To_LeftHandThumbEnd/ry
chkey -f 1 -F 'chop("../mocap/data/LeftHandThumb3_To_LeftHandThumbEnd:rz")' LeftHandThumb3_To_LeftHandThumbEnd/rz

opadd -n bone LeftHand_To_LeftHandIndex1
chlock LeftHand_To_LeftHandIndex1 +tx +ty +tz
opset -y on LeftHand_To_LeftHandIndex1
opparm LeftHand_To_LeftHandIndex1 dcolor ( 0 1 0.22793731093406677 )
opwire LeftForeArm_To_LeftHand -0 LeftHand_To_LeftHandIndex1
"$HH/scripts/obj/bone.cmd" LeftHand_To_LeftHandIndex1
opparm LeftHand_To_LeftHandIndex1 crtopcap (0.29999999999999999 0.29999999999999999 0.40000000000000002) crbotcap (0.29999999999999999 0.29999999999999999 0.40000000000000002)
opparm LeftHand_To_LeftHandIndex1 length 4.0127328110639269
chadd LeftHand_To_LeftHandIndex1 rx ry rz
chkey -f 1 -F 'chop("../mocap/data/LeftHand_To_LeftHandIndex1:rx")' LeftHand_To_LeftHandIndex1/rx
chkey -f 1 -F 'chop("../mocap/data/LeftHand_To_LeftHandIndex1:ry")' LeftHand_To_LeftHandIndex1/ry
chkey -f 1 -F 'chop("../mocap/data/LeftHand_To_LeftHandIndex1:rz")' LeftHand_To_LeftHandIndex1/rz

opadd -n bone LeftHandIndex1_To_LeftHandIndex2
chlock LeftHandIndex1_To_LeftHandIndex2 +tx +ty +tz
opset -y on LeftHandIndex1_To_LeftHandIndex2
opparm LeftHandIndex1_To_LeftHandIndex2 dcolor ( 0.91796058416366577 1 0 )
opwire LeftHand_To_LeftHandIndex1 -0 LeftHandIndex1_To_LeftHandIndex2
"$HH/scripts/obj/bone.cmd" LeftHandIndex1_To_LeftHandIndex2
opparm LeftHandIndex1_To_LeftHandIndex2 crtopcap (0.29999999999999999 0.29999999999999999 0.40000000000000002) crbotcap (0.29999999999999999 0.29999999999999999 0.40000000000000002)
opparm LeftHandIndex1_To_LeftHandIndex2 length 6.367095000000079
chadd LeftHandIndex1_To_LeftHandIndex2 rx ry rz
chkey -f 1 -F 'chop("../mocap/data/LeftHandIndex1_To_LeftHandIndex2:rx")' LeftHandIndex1_To_LeftHandIndex2/rx
chkey -f 1 -F 'chop("../mocap/data/LeftHandIndex1_To_LeftHandIndex2:ry")' LeftHandIndex1_To_LeftHandIndex2/ry
chkey -f 1 -F 'chop("../mocap/data/LeftHandIndex1_To_LeftHandIndex2:rz")' LeftHandIndex1_To_LeftHandIndex2/rz

opadd -n bone LeftHandIndex2_To_LeftHandIndex3
chlock LeftHandIndex2_To_LeftHandIndex3 +tx +ty +tz
opset -y on LeftHandIndex2_To_LeftHandIndex3
opparm LeftHandIndex2_To_LeftHandIndex3 dcolor ( 1 0 0.063858538866043091 )
opwire LeftHandIndex1_To_LeftHandIndex2 -0 LeftHandIndex2_To_LeftHandIndex3
"$HH/scripts/obj/bone.cmd" LeftHandIndex2_To_LeftHandIndex3
opparm LeftHandIndex2_To_LeftHandIndex3 crtopcap (0.29999999999999999 0.29999999999999999 0.40000000000000002) crbotcap (0.29999999999999999 0.29999999999999999 0.40000000000000002)
opparm LeftHandIndex2_To_LeftHandIndex3 length 3.6623640000000002
chadd LeftHandIndex2_To_LeftHandIndex3 rx ry rz
chkey -f 1 -F 'chop("../mocap/data/LeftHandIndex2_To_LeftHandIndex3:rx")' LeftHandIndex2_To_LeftHandIndex3/rx
chkey -f 1 -F 'chop("../mocap/data/LeftHandIndex2_To_LeftHandIndex3:ry")' LeftHandIndex2_To_LeftHandIndex3/ry
chkey -f 1 -F 'chop("../mocap/data/LeftHandIndex2_To_LeftHandIndex3:rz")' LeftHandIndex2_To_LeftHandIndex3/rz

opadd -n bone LeftHandIndex3_To_LeftHandIndex4
chlock LeftHandIndex3_To_LeftHandIndex4 +tx +ty +tz
opset -y on LeftHandIndex3_To_LeftHandIndex4
opparm LeftHandIndex3_To_LeftHandIndex4 dcolor ( 0.79024302959442139 0 1 )
opwire LeftHandIndex2_To_LeftHandIndex3 -0 LeftHandIndex3_To_LeftHandIndex4
"$HH/scripts/obj/bone.cmd" LeftHandIndex3_To_LeftHandIndex4
opparm LeftHandIndex3_To_LeftHandIndex4 crtopcap (0.29999999999999999 0.29999999999999999 0.40000000000000002) crbotcap (0.29999999999999999 0.29999999999999999 0.40000000000000002)
opparm LeftHandIndex3_To_LeftHandIndex4 length 2.3292420000068685
chadd LeftHandIndex3_To_LeftHandIndex4 rx ry rz
chkey -f 1 -F 'chop("../mocap/data/LeftHandIndex3_To_LeftHandIndex4:rx")' LeftHandIndex3_To_LeftHandIndex4/rx
chkey -f 1 -F 'chop("../mocap/data/LeftHandIndex3_To_LeftHandIndex4:ry")' LeftHandIndex3_To_LeftHandIndex4/ry
chkey -f 1 -F 'chop("../mocap/data/LeftHandIndex3_To_LeftHandIndex4:rz")' LeftHandIndex3_To_LeftHandIndex4/rz

opadd -n bone LeftHandIndex4_To_LeftHandIndexEnd
chlock LeftHandIndex4_To_LeftHandIndexEnd +tx +ty +tz
opset -y on LeftHandIndex4_To_LeftHandIndexEnd
opparm LeftHandIndex4_To_LeftHandIndexEnd dcolor ( 0 0.35565465688705444 1 )
opwire LeftHandIndex3_To_LeftHandIndex4 -0 LeftHandIndex4_To_LeftHandIndexEnd
"$HH/scripts/obj/bone.cmd" LeftHandIndex4_To_LeftHandIndexEnd
opparm LeftHandIndex4_To_LeftHandIndexEnd crtopcap (0.29999999999999999 0.29999999999999999 0.40000000000000002) crbotcap (0.29999999999999999 0.29999999999999999 0.40000000000000002)
opparm LeftHandIndex4_To_LeftHandIndexEnd length 2.7678230000001807
chadd LeftHandIndex4_To_LeftHandIndexEnd rx ry rz
chkey -f 1 -F 'chop("../mocap/data/LeftHandIndex4_To_LeftHandIndexEnd:rx")' LeftHandIndex4_To_LeftHandIndexEnd/rx
chkey -f 1 -F 'chop("../mocap/data/LeftHandIndex4_To_LeftHandIndexEnd:ry")' LeftHandIndex4_To_LeftHandIndexEnd/ry
chkey -f 1 -F 'chop("../mocap/data/LeftHandIndex4_To_LeftHandIndexEnd:rz")' LeftHandIndex4_To_LeftHandIndexEnd/rz

opadd -n bone LeftHand_To_LeftHandMiddle1
chlock LeftHand_To_LeftHandMiddle1 +tx +ty +tz
opset -y on LeftHand_To_LeftHandMiddle1
opparm LeftHand_To_LeftHandMiddle1 dcolor ( 0 1 0.49844714999198914 )
opwire LeftForeArm_To_LeftHand -0 LeftHand_To_LeftHandMiddle1
"$HH/scripts/obj/bone.cmd" LeftHand_To_LeftHandMiddle1
opparm LeftHand_To_LeftHandMiddle1 crtopcap (0.29999999999999999 0.29999999999999999 0.40000000000000002) crbotcap (0.29999999999999999 0.29999999999999999 0.40000000000000002)
opparm LeftHand_To_LeftHandMiddle1 length 3.3266253641816963
chadd LeftHand_To_LeftHandMiddle1 rx ry rz
chkey -f 1 -F 'chop("../mocap/data/LeftHand_To_LeftHandMiddle1:rx")' LeftHand_To_LeftHandMiddle1/rx
chkey -f 1 -F 'chop("../mocap/data/LeftHand_To_LeftHandMiddle1:ry")' LeftHand_To_LeftHandMiddle1/ry
chkey -f 1 -F 'chop("../mocap/data/LeftHand_To_LeftHandMiddle1:rz")' LeftHand_To_LeftHandMiddle1/rz

opadd -n bone LeftHandMiddle1_To_LeftHandMiddle2
chlock LeftHandMiddle1_To_LeftHandMiddle2 +tx +ty +tz
opset -y on LeftHandMiddle1_To_LeftHandMiddle2
opparm LeftHandMiddle1_To_LeftHandMiddle2 dcolor ( 0.64745086431503296 1 0 )
opwire LeftHand_To_LeftHandMiddle1 -0 LeftHandMiddle1_To_LeftHandMiddle2
"$HH/scripts/obj/bone.cmd" LeftHandMiddle1_To_LeftHandMiddle2
opparm LeftHandMiddle1_To_LeftHandMiddle2 crtopcap (0.29999999999999999 0.29999999999999999 0.40000000000000002) crbotcap (0.29999999999999999 0.29999999999999999 0.40000000000000002)
opparm LeftHandMiddle1_To_LeftHandMiddle2 length 6.2767890000007167
chadd LeftHandMiddle1_To_LeftHandMiddle2 rx ry rz
chkey -f 1 -F 'chop("../mocap/data/LeftHandMiddle1_To_LeftHandMiddle2:rx")' LeftHandMiddle1_To_LeftHandMiddle2/rx
chkey -f 1 -F 'chop("../mocap/data/LeftHandMiddle1_To_LeftHandMiddle2:ry")' LeftHandMiddle1_To_LeftHandMiddle2/ry
chkey -f 1 -F 'chop("../mocap/data/LeftHandMiddle1_To_LeftHandMiddle2:rz")' LeftHandMiddle1_To_LeftHandMiddle2/rz

opadd -n bone LeftHandMiddle2_To_LeftHandMiddle3
chlock LeftHandMiddle2_To_LeftHandMiddle3 +tx +ty +tz
opset -y on LeftHandMiddle2_To_LeftHandMiddle3
opparm LeftHandMiddle2_To_LeftHandMiddle3 dcolor ( 1 0.20665112137794495 0 )
opwire LeftHandMiddle1_To_LeftHandMiddle2 -0 LeftHandMiddle2_To_LeftHandMiddle3
"$HH/scripts/obj/bone.cmd" LeftHandMiddle2_To_LeftHandMiddle3
opparm LeftHandMiddle2_To_LeftHandMiddle3 crtopcap (0.29999999999999999 0.29999999999999999 0.40000000000000002) crbotcap (0.29999999999999999 0.29999999999999999 0.40000000000000002)
opparm LeftHandMiddle2_To_LeftHandMiddle3 length 4.3565200000019511
chadd LeftHandMiddle2_To_LeftHandMiddle3 rx ry rz
chkey -f 1 -F 'chop("../mocap/data/LeftHandMiddle2_To_LeftHandMiddle3:rx")' LeftHandMiddle2_To_LeftHandMiddle3/rx
chkey -f 1 -F 'chop("../mocap/data/LeftHandMiddle2_To_LeftHandMiddle3:ry")' LeftHandMiddle2_To_LeftHandMiddle3/ry
chkey -f 1 -F 'chop("../mocap/data/LeftHandMiddle2_To_LeftHandMiddle3:rz")' LeftHandMiddle2_To_LeftHandMiddle3/rz

opadd -n bone LeftHandMiddle3_To_LeftHandMiddle4
chlock LeftHandMiddle3_To_LeftHandMiddle4 +tx +ty +tz
opset -y on LeftHandMiddle3_To_LeftHandMiddle4
opparm LeftHandMiddle3_To_LeftHandMiddle4 dcolor ( 1 0 0.93924713134765625 )
opwire LeftHandMiddle2_To_LeftHandMiddle3 -0 LeftHandMiddle3_To_LeftHandMiddle4
"$HH/scripts/obj/bone.cmd" LeftHandMiddle3_To_LeftHandMiddle4
opparm LeftHandMiddle3_To_LeftHandMiddle4 crtopcap (0.29999999999999999 0.29999999999999999 0.40000000000000002) crbotcap (0.29999999999999999 0.29999999999999999 0.40000000000000002)
opparm LeftHandMiddle3_To_LeftHandMiddle4 length 2.9968770000106781
chadd LeftHandMiddle3_To_LeftHandMiddle4 rx ry rz
chkey -f 1 -F 'chop("../mocap/data/LeftHandMiddle3_To_LeftHandMiddle4:rx")' LeftHandMiddle3_To_LeftHandMiddle4/rx
chkey -f 1 -F 'chop("../mocap/data/LeftHandMiddle3_To_LeftHandMiddle4:ry")' LeftHandMiddle3_To_LeftHandMiddle4/ry
chkey -f 1 -F 'chop("../mocap/data/LeftHandMiddle3_To_LeftHandMiddle4:rz")' LeftHandMiddle3_To_LeftHandMiddle4/rz

opadd -n bone LeftHandMiddle4_To_LeftHandMiddleEnd
chlock LeftHandMiddle4_To_LeftHandMiddleEnd +tx +ty +tz
opset -y on LeftHandMiddle4_To_LeftHandMiddleEnd
opparm LeftHandMiddle4_To_LeftHandMiddleEnd dcolor ( 0 0.085145063698291779 1 )
opwire LeftHandMiddle3_To_LeftHandMiddle4 -0 LeftHandMiddle4_To_LeftHandMiddleEnd
"$HH/scripts/obj/bone.cmd" LeftHandMiddle4_To_LeftHandMiddleEnd
opparm LeftHandMiddle4_To_LeftHandMiddleEnd crtopcap (0.29999999999999999 0.29999999999999999 0.40000000000000002) crbotcap (0.29999999999999999 0.29999999999999999 0.40000000000000002)
opparm LeftHandMiddle4_To_LeftHandMiddleEnd length 2.3232560000053808
chadd LeftHandMiddle4_To_LeftHandMiddleEnd rx ry rz
chkey -f 1 -F 'chop("../mocap/data/LeftHandMiddle4_To_LeftHandMiddleEnd:rx")' LeftHandMiddle4_To_LeftHandMiddleEnd/rx
chkey -f 1 -F 'chop("../mocap/data/LeftHandMiddle4_To_LeftHandMiddleEnd:ry")' LeftHandMiddle4_To_LeftHandMiddleEnd/ry
chkey -f 1 -F 'chop("../mocap/data/LeftHandMiddle4_To_LeftHandMiddleEnd:rz")' LeftHandMiddle4_To_LeftHandMiddleEnd/rz

opadd -n bone LeftHand_To_LeftHandRing1
chlock LeftHand_To_LeftHandRing1 +tx +ty +tz
opset -y on LeftHand_To_LeftHandRing1
opparm LeftHand_To_LeftHandRing1 dcolor ( 0 1 0.76895701885223389 )
opwire LeftForeArm_To_LeftHand -0 LeftHand_To_LeftHandRing1
"$HH/scripts/obj/bone.cmd" LeftHand_To_LeftHandRing1
opparm LeftHand_To_LeftHandRing1 crtopcap (0.29999999999999999 0.29999999999999999 0.40000000000000002) crbotcap (0.29999999999999999 0.29999999999999999 0.40000000000000002)
opparm LeftHand_To_LeftHandRing1 length 2.9011278705884371
chadd LeftHand_To_LeftHandRing1 rx ry rz
chkey -f 1 -F 'chop("../mocap/data/LeftHand_To_LeftHandRing1:rx")' LeftHand_To_LeftHandRing1/rx
chkey -f 1 -F 'chop("../mocap/data/LeftHand_To_LeftHandRing1:ry")' LeftHand_To_LeftHandRing1/ry
chkey -f 1 -F 'chop("../mocap/data/LeftHand_To_LeftHandRing1:rz")' LeftHand_To_LeftHandRing1/rz

opadd -n bone LeftHandRing1_To_LeftHandRing2
chlock LeftHandRing1_To_LeftHandRing2 +tx +ty +tz
opset -y on LeftHandRing1_To_LeftHandRing2
opparm LeftHandRing1_To_LeftHandRing2 dcolor ( 0.37694105505943298 1 0 )
opwire LeftHand_To_LeftHandRing1 -0 LeftHandRing1_To_LeftHandRing2
"$HH/scripts/obj/bone.cmd" LeftHandRing1_To_LeftHandRing2
opparm LeftHandRing1_To_LeftHandRing2 crtopcap (0.29999999999999999 0.29999999999999999 0.40000000000000002) crbotcap (0.29999999999999999 0.29999999999999999 0.40000000000000002)
opparm LeftHandRing1_To_LeftHandRing2 length 6.0331980000013257
chadd LeftHandRing1_To_LeftHandRing2 rx ry rz
chkey -f 1 -F 'chop("../mocap/data/LeftHandRing1_To_LeftHandRing2:rx")' LeftHandRing1_To_LeftHandRing2/rx
chkey -f 1 -F 'chop("../mocap/data/LeftHandRing1_To_LeftHandRing2:ry")' LeftHandRing1_To_LeftHandRing2/ry
chkey -f 1 -F 'chop("../mocap/data/LeftHandRing1_To_LeftHandRing2:rz")' LeftHandRing1_To_LeftHandRing2/rz

opadd -n bone LeftHandRing2_To_LeftHandRing3
chlock LeftHandRing2_To_LeftHandRing3 +tx +ty +tz
opset -y on LeftHandRing2_To_LeftHandRing3
opparm LeftHandRing2_To_LeftHandRing3 dcolor ( 1 0.47716096043586731 0 )
opwire LeftHandRing1_To_LeftHandRing2 -0 LeftHandRing2_To_LeftHandRing3
"$HH/scripts/obj/bone.cmd" LeftHandRing2_To_LeftHandRing3
opparm LeftHandRing2_To_LeftHandRing3 crtopcap (0.29999999999999999 0.29999999999999999 0.40000000000000002) crbotcap (0.29999999999999999 0.29999999999999999 0.40000000000000002)
opparm LeftHandRing2_To_LeftHandRing3 length 4.3505780000010343
chadd LeftHandRing2_To_LeftHandRing3 rx ry rz
chkey -f 1 -F 'chop("../mocap/data/LeftHandRing2_To_LeftHandRing3:rx")' LeftHandRing2_To_LeftHandRing3/rx
chkey -f 1 -F 'chop("../mocap/data/LeftHandRing2_To_LeftHandRing3:ry")' LeftHandRing2_To_LeftHandRing3/ry
chkey -f 1 -F 'chop("../mocap/data/LeftHandRing2_To_LeftHandRing3:rz")' LeftHandRing2_To_LeftHandRing3/rz

opadd -n bone LeftHandRing3_To_LeftHandRing4
chlock LeftHandRing3_To_LeftHandRing4 +tx +ty +tz
opset -y on LeftHandRing3_To_LeftHandRing4
opparm LeftHandRing3_To_LeftHandRing4 dcolor ( 1 0 0.66873729228973389 )
opwire LeftHandRing2_To_LeftHandRing3 -0 LeftHandRing3_To_LeftHandRing4
"$HH/scripts/obj/bone.cmd" LeftHandRing3_To_LeftHandRing4
opparm LeftHandRing3_To_LeftHandRing4 crtopcap (0.29999999999999999 0.29999999999999999 0.40000000000000002) crbotcap (0.29999999999999999 0.29999999999999999 0.40000000000000002)
opparm LeftHandRing3_To_LeftHandRing4 length 2.6513210000099949
chadd LeftHandRing3_To_LeftHandRing4 rx ry rz
chkey -f 1 -F 'chop("../mocap/data/LeftHandRing3_To_LeftHandRing4:rx")' LeftHandRing3_To_LeftHandRing4/rx
chkey -f 1 -F 'chop("../mocap/data/LeftHandRing3_To_LeftHandRing4:ry")' LeftHandRing3_To_LeftHandRing4/ry
chkey -f 1 -F 'chop("../mocap/data/LeftHandRing3_To_LeftHandRing4:rz")' LeftHandRing3_To_LeftHandRing4/rz

opadd -n bone LeftHandRing4_To_LeftHandRingEnd
chlock LeftHandRing4_To_LeftHandRingEnd +tx +ty +tz
opset -y on LeftHandRing4_To_LeftHandRingEnd
opparm LeftHandRing4_To_LeftHandRingEnd dcolor ( 0.18536478281021118 0 1 )
opwire LeftHandRing3_To_LeftHandRing4 -0 LeftHandRing4_To_LeftHandRingEnd
"$HH/scripts/obj/bone.cmd" LeftHandRing4_To_LeftHandRingEnd
opparm LeftHandRing4_To_LeftHandRingEnd crtopcap (0.29999999999999999 0.29999999999999999 0.40000000000000002) crbotcap (0.29999999999999999 0.29999999999999999 0.40000000000000002)
opparm LeftHandRing4_To_LeftHandRingEnd length 1.9376630000043866
chadd LeftHandRing4_To_LeftHandRingEnd rx ry rz
chkey -f 1 -F 'chop("../mocap/data/LeftHandRing4_To_LeftHandRingEnd:rx")' LeftHandRing4_To_LeftHandRingEnd/rx
chkey -f 1 -F 'chop("../mocap/data/LeftHandRing4_To_LeftHandRingEnd:ry")' LeftHandRing4_To_LeftHandRingEnd/ry
chkey -f 1 -F 'chop("../mocap/data/LeftHandRing4_To_LeftHandRingEnd:rz")' LeftHandRing4_To_LeftHandRingEnd/rz

opadd -n bone LeftHand_To_LeftHandPinky1
chlock LeftHand_To_LeftHandPinky1 +tx +ty +tz
opset -y on LeftHand_To_LeftHandPinky1
opparm LeftHand_To_LeftHandPinky1 dcolor ( 0 0.96053314208984375 1 )
opwire LeftForeArm_To_LeftHand -0 LeftHand_To_LeftHandPinky1
"$HH/scripts/obj/bone.cmd" LeftHand_To_LeftHandPinky1
opparm LeftHand_To_LeftHandPinky1 crtopcap (0.29999999999999999 0.29999999999999999 0.40000000000000002) crbotcap (0.29999999999999999 0.29999999999999999 0.40000000000000002)
opparm LeftHand_To_LeftHandPinky1 length 3.2967257334042817
chadd LeftHand_To_LeftHandPinky1 rx ry rz
chkey -f 1 -F 'chop("../mocap/data/LeftHand_To_LeftHandPinky1:rx")' LeftHand_To_LeftHandPinky1/rx
chkey -f 1 -F 'chop("../mocap/data/LeftHand_To_LeftHandPinky1:ry")' LeftHand_To_LeftHandPinky1/ry
chkey -f 1 -F 'chop("../mocap/data/LeftHand_To_LeftHandPinky1:rz")' LeftHand_To_LeftHandPinky1/rz

opadd -n bone LeftHandPinky1_To_LeftHandPinky2
chlock LeftHandPinky1_To_LeftHandPinky2 +tx +ty +tz
opset -y on LeftHandPinky1_To_LeftHandPinky2
opparm LeftHandPinky1_To_LeftHandPinky2 dcolor ( 0.10643120110034943 1 0 )
opwire LeftHand_To_LeftHandPinky1 -0 LeftHandPinky1_To_LeftHandPinky2
"$HH/scripts/obj/bone.cmd" LeftHandPinky1_To_LeftHandPinky2
opparm LeftHandPinky1_To_LeftHandPinky2 crtopcap (0.29999999999999999 0.29999999999999999 0.40000000000000002) crbotcap (0.29999999999999999 0.29999999999999999 0.40000000000000002)
opparm LeftHandPinky1_To_LeftHandPinky2 length 5.5493600000058567
chadd LeftHandPinky1_To_LeftHandPinky2 rx ry rz
chkey -f 1 -F 'chop("../mocap/data/LeftHandPinky1_To_LeftHandPinky2:rx")' LeftHandPinky1_To_LeftHandPinky2/rx
chkey -f 1 -F 'chop("../mocap/data/LeftHandPinky1_To_LeftHandPinky2:ry")' LeftHandPinky1_To_LeftHandPinky2/ry
chkey -f 1 -F 'chop("../mocap/data/LeftHandPinky1_To_LeftHandPinky2:rz")' LeftHandPinky1_To_LeftHandPinky2/rz

opadd -n bone LeftHandPinky2_To_LeftHandPinky3
chlock LeftHandPinky2_To_LeftHandPinky3 +tx +ty +tz
opset -y on LeftHandPinky2_To_LeftHandPinky3
opparm LeftHandPinky2_To_LeftHandPinky3 dcolor ( 1 0.74767082929611206 0 )
opwire LeftHandPinky1_To_LeftHandPinky2 -0 LeftHandPinky2_To_LeftHandPinky3
"$HH/scripts/obj/bone.cmd" LeftHandPinky2_To_LeftHandPinky3
opparm LeftHandPinky2_To_LeftHandPinky3 crtopcap (0.29999999999999999 0.29999999999999999 0.40000000000000002) crbotcap (0.29999999999999999 0.29999999999999999 0.40000000000000002)
opparm LeftHandPinky2_To_LeftHandPinky3 length 3.0709740000026051
chadd LeftHandPinky2_To_LeftHandPinky3 rx ry rz
chkey -f 1 -F 'chop("../mocap/data/LeftHandPinky2_To_LeftHandPinky3:rx")' LeftHandPinky2_To_LeftHandPinky3/rx
chkey -f 1 -F 'chop("../mocap/data/LeftHandPinky2_To_LeftHandPinky3:ry")' LeftHandPinky2_To_LeftHandPinky3/ry
chkey -f 1 -F 'chop("../mocap/data/LeftHandPinky2_To_LeftHandPinky3:rz")' LeftHandPinky2_To_LeftHandPinky3/rz

opadd -n bone LeftHandPinky3_To_LeftHandPinky4
chlock LeftHandPinky3_To_LeftHandPinky4 +tx +ty +tz
opset -y on LeftHandPinky3_To_LeftHandPinky4
opparm LeftHandPinky3_To_LeftHandPinky4 dcolor ( 1 0 0.39822742342948914 )
opwire LeftHandPinky2_To_LeftHandPinky3 -0 LeftHandPinky3_To_LeftHandPinky4
"$HH/scripts/obj/bone.cmd" LeftHandPinky3_To_LeftHandPinky4
opparm LeftHandPinky3_To_LeftHandPinky4 crtopcap (0.29999999999999999 0.29999999999999999 0.40000000000000002) crbotcap (0.29999999999999999 0.29999999999999999 0.40000000000000002)
opparm LeftHandPinky3_To_LeftHandPinky4 length 1.5496720000003226
chadd LeftHandPinky3_To_LeftHandPinky4 rx ry rz
chkey -f 1 -F 'chop("../mocap/data/LeftHandPinky3_To_LeftHandPinky4:rx")' LeftHandPinky3_To_LeftHandPinky4/rx
chkey -f 1 -F 'chop("../mocap/data/LeftHandPinky3_To_LeftHandPinky4:ry")' LeftHandPinky3_To_LeftHandPinky4/ry
chkey -f 1 -F 'chop("../mocap/data/LeftHandPinky3_To_LeftHandPinky4:rz")' LeftHandPinky3_To_LeftHandPinky4/rz

opadd -n bone LeftHandPinky4_To_LeftHandPinkyEnd
chlock LeftHandPinky4_To_LeftHandPinkyEnd +tx +ty +tz
opset -y on LeftHandPinky4_To_LeftHandPinkyEnd
opparm LeftHandPinky4_To_LeftHandPinkyEnd dcolor ( 0.45587462186813354 0 1 )
opwire LeftHandPinky3_To_LeftHandPinky4 -0 LeftHandPinky4_To_LeftHandPinkyEnd
"$HH/scripts/obj/bone.cmd" LeftHandPinky4_To_LeftHandPinkyEnd
opparm LeftHandPinky4_To_LeftHandPinkyEnd crtopcap (0.29999999999999999 0.29999999999999999 0.40000000000000002) crbotcap (0.29999999999999999 0.29999999999999999 0.40000000000000002)
opparm LeftHandPinky4_To_LeftHandPinkyEnd length 1.9521230000000001
chadd LeftHandPinky4_To_LeftHandPinkyEnd rx ry rz
chkey -f 1 -F 'chop("../mocap/data/LeftHandPinky4_To_LeftHandPinkyEnd:rx")' LeftHandPinky4_To_LeftHandPinkyEnd/rx
chkey -f 1 -F 'chop("../mocap/data/LeftHandPinky4_To_LeftHandPinkyEnd:ry")' LeftHandPinky4_To_LeftHandPinkyEnd/ry
chkey -f 1 -F 'chop("../mocap/data/LeftHandPinky4_To_LeftHandPinkyEnd:rz")' LeftHandPinky4_To_LeftHandPinkyEnd/rz

opadd -n bone Chest_To_RightShoulder
chlock Chest_To_RightShoulder +tx +ty +tz
opset -y on Chest_To_RightShoulder
opparm Chest_To_RightShoulder dcolor ( 0 0.69002330303192139 1 )
opwire Spine2_To_Chest -0 Chest_To_RightShoulder
"$HH/scripts/obj/bone.cmd" Chest_To_RightShoulder
opparm Chest_To_RightShoulder crtopcap (0.29999999999999999 0.29999999999999999 0.40000000000000002) crbotcap (0.29999999999999999 0.29999999999999999 0.40000000000000002)
opparm Chest_To_RightShoulder length 23.799552746985306
chadd Chest_To_RightShoulder rx ry rz
chkey -f 1 -F 'chop("../mocap/data/Chest_To_RightShoulder:rx")' Chest_To_RightShoulder/rx
chkey -f 1 -F 'chop("../mocap/data/Chest_To_RightShoulder:ry")' Chest_To_RightShoulder/ry
chkey -f 1 -F 'chop("../mocap/data/Chest_To_RightShoulder:rz")' Chest_To_RightShoulder/rz

opadd -n bone RightShoulder_To_RightArm
chlock RightShoulder_To_RightArm +tx +ty +tz
opset -y on RightShoulder_To_RightArm
opparm RightShoulder_To_RightArm dcolor ( 0 1 0.16407877206802368 )
opwire Chest_To_RightShoulder -0 RightShoulder_To_RightArm
"$HH/scripts/obj/bone.cmd" RightShoulder_To_RightArm
opparm RightShoulder_To_RightArm crtopcap (0.29999999999999999 0.29999999999999999 0.40000000000000002) crbotcap (0.29999999999999999 0.29999999999999999 0.40000000000000002)
opparm RightShoulder_To_RightArm length 16.027195000003896
chadd RightShoulder_To_RightArm rx ry rz
chkey -f 1 -F 'chop("../mocap/data/RightShoulder_To_RightArm:rx")' RightShoulder_To_RightArm/rx
chkey -f 1 -F 'chop("../mocap/data/RightShoulder_To_RightArm:ry")' RightShoulder_To_RightArm/ry
chkey -f 1 -F 'chop("../mocap/data/RightShoulder_To_RightArm:rz")' RightShoulder_To_RightArm/rz

opadd -n bone RightArm_To_RightForeArm
chlock RightArm_To_RightForeArm +tx +ty +tz
opset -y on RightArm_To_RightForeArm
opparm RightArm_To_RightForeArm dcolor ( 0.98181939125061035 1 0 )
opwire RightShoulder_To_RightArm -0 RightArm_To_RightForeArm
"$HH/scripts/obj/bone.cmd" RightArm_To_RightForeArm
opparm RightArm_To_RightForeArm crtopcap (0.29999999999999999 0.29999999999999999 0.40000000000000002) crbotcap (0.29999999999999999 0.29999999999999999 0.40000000000000002)
opparm RightArm_To_RightForeArm length 28.736639000000348
chadd RightArm_To_RightForeArm rx ry rz
chkey -f 1 -F 'chop("../mocap/data/RightArm_To_RightForeArm:rx")' RightArm_To_RightForeArm/rx
chkey -f 1 -F 'chop("../mocap/data/RightArm_To_RightForeArm:ry")' RightArm_To_RightForeArm/ry
chkey -f 1 -F 'chop("../mocap/data/RightArm_To_RightForeArm:rz")' RightArm_To_RightForeArm/rz

opadd -n bone RightForeArm_To_RightHand
chlock RightForeArm_To_RightHand +tx +ty +tz
opset -y on RightForeArm_To_RightHand
opparm RightForeArm_To_RightHand dcolor ( 1 0 0.12771758437156677 )
opwire RightArm_To_RightForeArm -0 RightForeArm_To_RightHand
"$HH/scripts/obj/bone.cmd" RightForeArm_To_RightHand
opparm RightForeArm_To_RightHand crtopcap (0.29999999999999999 0.29999999999999999 0.40000000000000002) crbotcap (0.29999999999999999 0.29999999999999999 0.40000000000000002)
opparm RightForeArm_To_RightHand length 27.133619000000664
chadd RightForeArm_To_RightHand rx ry rz
chkey -f 1 -F 'chop("../mocap/data/RightForeArm_To_RightHand:rx")' RightForeArm_To_RightHand/rx
chkey -f 1 -F 'chop("../mocap/data/RightForeArm_To_RightHand:ry")' RightForeArm_To_RightHand/ry
chkey -f 1 -F 'chop("../mocap/data/RightForeArm_To_RightHand:rz")' RightForeArm_To_RightHand/rz

opadd -n bone RightHand_To_RightHandThumb1
chlock RightHand_To_RightHandThumb1 +tx +ty +tz
opset -y on RightHand_To_RightHandThumb1
opparm RightHand_To_RightHandThumb1 dcolor ( 0.72638446092605591 0 1 )
opwire RightForeArm_To_RightHand -0 RightHand_To_RightHandThumb1
"$HH/scripts/obj/bone.cmd" RightHand_To_RightHandThumb1
opparm RightHand_To_RightHandThumb1 crtopcap (0.29999999999999999 0.29999999999999999 0.40000000000000002) crbotcap (0.29999999999999999 0.29999999999999999 0.40000000000000002)
opparm RightHand_To_RightHandThumb1 length 4.1342491545272164
chadd RightHand_To_RightHandThumb1 rx ry rz
chkey -f 1 -F 'chop("../mocap/data/RightHand_To_RightHandThumb1:rx")' RightHand_To_RightHandThumb1/rx
chkey -f 1 -F 'chop("../mocap/data/RightHand_To_RightHandThumb1:ry")' RightHand_To_RightHandThumb1/ry
chkey -f 1 -F 'chop("../mocap/data/RightHand_To_RightHandThumb1:rz")' RightHand_To_RightHandThumb1/rz

opadd -n bone RightHandThumb1_To_RightHandThumb2
chlock RightHandThumb1_To_RightHandThumb2 +tx +ty +tz
opset -y on RightHandThumb1_To_RightHandThumb2
opparm RightHandThumb1_To_RightHandThumb2 dcolor ( 0 0.41951343417167664 1 )
opwire RightHand_To_RightHandThumb1 -0 RightHandThumb1_To_RightHandThumb2
"$HH/scripts/obj/bone.cmd" RightHandThumb1_To_RightHandThumb2
opparm RightHandThumb1_To_RightHandThumb2 crtopcap (0.29999999999999999 0.29999999999999999 0.40000000000000002) crbotcap (0.29999999999999999 0.29999999999999999 0.40000000000000002)
opparm RightHandThumb1_To_RightHandThumb2 length 4.7035940000013818
chadd RightHandThumb1_To_RightHandThumb2 rx ry rz
chkey -f 1 -F 'chop("../mocap/data/RightHandThumb1_To_RightHandThumb2:rx")' RightHandThumb1_To_RightHandThumb2/rx
chkey -f 1 -F 'chop("../mocap/data/RightHandThumb1_To_RightHandThumb2:ry")' RightHandThumb1_To_RightHandThumb2/ry
chkey -f 1 -F 'chop("../mocap/data/RightHandThumb1_To_RightHandThumb2:rz")' RightHandThumb1_To_RightHandThumb2/rz

opadd -n bone RightHandThumb2_To_RightHandThumb3
chlock RightHandThumb2_To_RightHandThumb3 +tx +ty +tz
opset -y on RightHandThumb2_To_RightHandThumb3
opparm RightHandThumb2_To_RightHandThumb3 dcolor ( 0 1 0.43458837270736694 )
opwire RightHandThumb1_To_RightHandThumb2 -0 RightHandThumb2_To_RightHandThumb3
"$HH/scripts/obj/bone.cmd" RightHandThumb2_To_RightHandThumb3
opparm RightHandThumb2_To_RightHandThumb3 crtopcap (0.29999999999999999 0.29999999999999999 0.40000000000000002) crbotcap (0.29999999999999999 0.29999999999999999 0.40000000000000002)
opparm RightHandThumb2_To_RightHandThumb3 length 2.7949350000044726
chadd RightHandThumb2_To_RightHandThumb3 rx ry rz
chkey -f 1 -F 'chop("../mocap/data/RightHandThumb2_To_RightHandThumb3:rx")' RightHandThumb2_To_RightHandThumb3/rx
chkey -f 1 -F 'chop("../mocap/data/RightHandThumb2_To_RightHandThumb3:ry")' RightHandThumb2_To_RightHandThumb3/ry
chkey -f 1 -F 'chop("../mocap/data/RightHandThumb2_To_RightHandThumb3:rz")' RightHandThumb2_To_RightHandThumb3/rz

opadd -n bone RightHandThumb3_To_RightHandThumbEnd
chlock RightHandThumb3_To_RightHandThumbEnd +tx +ty +tz
opset -y on RightHandThumb3_To_RightHandThumbEnd
opparm RightHandThumb3_To_RightHandThumbEnd dcolor ( 0.71130955219268799 1 0 )
opwire RightHandThumb2_To_RightHandThumb3 -0 RightHandThumb3_To_RightHandThumbEnd
"$HH/scripts/obj/bone.cmd" RightHandThumb3_To_RightHandThumbEnd
opparm RightHandThumb3_To_RightHandThumbEnd crtopcap (0.29999999999999999 0.29999999999999999 0.40000000000000002) crbotcap (0.29999999999999999 0.29999999999999999 0.40000000000000002)
opparm RightHandThumb3_To_RightHandThumbEnd length 3.1838520000026698
chadd RightHandThumb3_To_RightHandThumbEnd rx ry rz
chkey -f 1 -F 'chop("../mocap/data/RightHandThumb3_To_RightHandThumbEnd:rx")' RightHandThumb3_To_RightHandThumbEnd/rx
chkey -f 1 -F 'chop("../mocap/data/RightHandThumb3_To_RightHandThumbEnd:ry")' RightHandThumb3_To_RightHandThumbEnd/ry
chkey -f 1 -F 'chop("../mocap/data/RightHandThumb3_To_RightHandThumbEnd:rz")' RightHandThumb3_To_RightHandThumbEnd/rz

opadd -n bone RightHand_To_RightHandIndex1
chlock RightHand_To_RightHandIndex1 +tx +ty +tz
opset -y on RightHand_To_RightHandIndex1
opparm RightHand_To_RightHandIndex1 dcolor ( 1 0.14279241859912872 0 )
opwire RightForeArm_To_RightHand -0 RightHand_To_RightHandIndex1
"$HH/scripts/obj/bone.cmd" RightHand_To_RightHandIndex1
opparm RightHand_To_RightHandIndex1 crtopcap (0.29999999999999999 0.29999999999999999 0.40000000000000002) crbotcap (0.29999999999999999 0.29999999999999999 0.40000000000000002)
opparm RightHand_To_RightHandIndex1 length 4.0082009789187216
chadd RightHand_To_RightHandIndex1 rx ry rz
chkey -f 1 -F 'chop("../mocap/data/RightHand_To_RightHandIndex1:rx")' RightHand_To_RightHandIndex1/rx
chkey -f 1 -F 'chop("../mocap/data/RightHand_To_RightHandIndex1:ry")' RightHand_To_RightHandIndex1/ry
chkey -f 1 -F 'chop("../mocap/data/RightHand_To_RightHandIndex1:rz")' RightHand_To_RightHandIndex1/rz

opadd -n bone RightHandIndex1_To_RightHandIndex2
chlock RightHandIndex1_To_RightHandIndex2 +tx +ty +tz
opset -y on RightHandIndex1_To_RightHandIndex2
opparm RightHandIndex1_To_RightHandIndex2 dcolor ( 0.99689429998397827 0 1 )
opwire RightHand_To_RightHandIndex1 -0 RightHandIndex1_To_RightHandIndex2
"$HH/scripts/obj/bone.cmd" RightHandIndex1_To_RightHandIndex2
opparm RightHandIndex1_To_RightHandIndex2 crtopcap (0.29999999999999999 0.29999999999999999 0.40000000000000002) crbotcap (0.29999999999999999 0.29999999999999999 0.40000000000000002)
opparm RightHandIndex1_To_RightHandIndex2 length 6.3444339999999997
chadd RightHandIndex1_To_RightHandIndex2 rx ry rz
chkey -f 1 -F 'chop("../mocap/data/RightHandIndex1_To_RightHandIndex2:rx")' RightHandIndex1_To_RightHandIndex2/rx
chkey -f 1 -F 'chop("../mocap/data/RightHandIndex1_To_RightHandIndex2:ry")' RightHandIndex1_To_RightHandIndex2/ry
chkey -f 1 -F 'chop("../mocap/data/RightHandIndex1_To_RightHandIndex2:rz")' RightHandIndex1_To_RightHandIndex2/rz

opadd -n bone RightHandIndex2_To_RightHandIndex3
chlock RightHandIndex2_To_RightHandIndex3 +tx +ty +tz
opset -y on RightHandIndex2_To_RightHandIndex3
opparm RightHandIndex2_To_RightHandIndex3 dcolor ( 0 0.14900359511375427 1 )
opwire RightHandIndex1_To_RightHandIndex2 -0 RightHandIndex2_To_RightHandIndex3
"$HH/scripts/obj/bone.cmd" RightHandIndex2_To_RightHandIndex3
opparm RightHandIndex2_To_RightHandIndex3 crtopcap (0.29999999999999999 0.29999999999999999 0.40000000000000002) crbotcap (0.29999999999999999 0.29999999999999999 0.40000000000000002)
opparm RightHandIndex2_To_RightHandIndex3 length 3.6548710000087556
chadd RightHandIndex2_To_RightHandIndex3 rx ry rz
chkey -f 1 -F 'chop("../mocap/data/RightHandIndex2_To_RightHandIndex3:rx")' RightHandIndex2_To_RightHandIndex3/rx
chkey -f 1 -F 'chop("../mocap/data/RightHandIndex2_To_RightHandIndex3:ry")' RightHandIndex2_To_RightHandIndex3/ry
chkey -f 1 -F 'chop("../mocap/data/RightHandIndex2_To_RightHandIndex3:rz")' RightHandIndex2_To_RightHandIndex3/rz

opadd -n bone RightHandIndex3_To_RightHandIndex4
chlock RightHandIndex3_To_RightHandIndex4 +tx +ty +tz
opset -y on RightHandIndex3_To_RightHandIndex4
opparm RightHandIndex3_To_RightHandIndex4 dcolor ( 0 1 0.70509821176528931 )
opwire RightHandIndex2_To_RightHandIndex3 -0 RightHandIndex3_To_RightHandIndex4
"$HH/scripts/obj/bone.cmd" RightHandIndex3_To_RightHandIndex4
opparm RightHandIndex3_To_RightHandIndex4 crtopcap (0.29999999999999999 0.29999999999999999 0.40000000000000002) crbotcap (0.29999999999999999 0.29999999999999999 0.40000000000000002)
opparm RightHandIndex3_To_RightHandIndex4 length 2.3275860000002151
chadd RightHandIndex3_To_RightHandIndex4 rx ry rz
chkey -f 1 -F 'chop("../mocap/data/RightHandIndex3_To_RightHandIndex4:rx")' RightHandIndex3_To_RightHandIndex4/rx
chkey -f 1 -F 'chop("../mocap/data/RightHandIndex3_To_RightHandIndex4:ry")' RightHandIndex3_To_RightHandIndex4/ry
chkey -f 1 -F 'chop("../mocap/data/RightHandIndex3_To_RightHandIndex4:rz")' RightHandIndex3_To_RightHandIndex4/rz

opadd -n bone RightHandIndex4_To_RightHandIndexEnd
chlock RightHandIndex4_To_RightHandIndexEnd +tx +ty +tz
opset -y on RightHandIndex4_To_RightHandIndexEnd
opparm RightHandIndex4_To_RightHandIndexEnd dcolor ( 0.44079971313476562 1 0 )
opwire RightHandIndex3_To_RightHandIndex4 -0 RightHandIndex4_To_RightHandIndexEnd
"$HH/scripts/obj/bone.cmd" RightHandIndex4_To_RightHandIndexEnd
opparm RightHandIndex4_To_RightHandIndexEnd crtopcap (0.29999999999999999 0.29999999999999999 0.40000000000000002) crbotcap (0.29999999999999999 0.29999999999999999 0.40000000000000002)
opparm RightHandIndex4_To_RightHandIndexEnd length 2.7700010000131772
chadd RightHandIndex4_To_RightHandIndexEnd rx ry rz
chkey -f 1 -F 'chop("../mocap/data/RightHandIndex4_To_RightHandIndexEnd:rx")' RightHandIndex4_To_RightHandIndexEnd/rx
chkey -f 1 -F 'chop("../mocap/data/RightHandIndex4_To_RightHandIndexEnd:ry")' RightHandIndex4_To_RightHandIndexEnd/ry
chkey -f 1 -F 'chop("../mocap/data/RightHandIndex4_To_RightHandIndexEnd:rz")' RightHandIndex4_To_RightHandIndexEnd/rz

opadd -n bone RightHand_To_RightHandMiddle1
chlock RightHand_To_RightHandMiddle1 +tx +ty +tz
opset -y on RightHand_To_RightHandMiddle1
opparm RightHand_To_RightHandMiddle1 dcolor ( 1 0.41330224275588989 0 )
opwire RightForeArm_To_RightHand -0 RightHand_To_RightHandMiddle1
"$HH/scripts/obj/bone.cmd" RightHand_To_RightHandMiddle1
opparm RightHand_To_RightHandMiddle1 crtopcap (0.29999999999999999 0.29999999999999999 0.40000000000000002) crbotcap (0.29999999999999999 0.29999999999999999 0.40000000000000002)
opparm RightHand_To_RightHandMiddle1 length 3.3316308225955948
chadd RightHand_To_RightHandMiddle1 rx ry rz
chkey -f 1 -F 'chop("../mocap/data/RightHand_To_RightHandMiddle1:rx")' RightHand_To_RightHandMiddle1/rx
chkey -f 1 -F 'chop("../mocap/data/RightHand_To_RightHandMiddle1:ry")' RightHand_To_RightHandMiddle1/ry
chkey -f 1 -F 'chop("../mocap/data/RightHand_To_RightHandMiddle1:rz")' RightHand_To_RightHandMiddle1/rz

opadd -n bone RightHandMiddle1_To_RightHandMiddle2
chlock RightHandMiddle1_To_RightHandMiddle2 +tx +ty +tz
opset -y on RightHandMiddle1_To_RightHandMiddle2
opparm RightHandMiddle1_To_RightHandMiddle2 dcolor ( 1 0 0.73259580135345459 )
opwire RightHand_To_RightHandMiddle1 -0 RightHandMiddle1_To_RightHandMiddle2
"$HH/scripts/obj/bone.cmd" RightHandMiddle1_To_RightHandMiddle2
opparm RightHandMiddle1_To_RightHandMiddle2 crtopcap (0.29999999999999999 0.29999999999999999 0.40000000000000002) crbotcap (0.29999999999999999 0.29999999999999999 0.40000000000000002)
opparm RightHandMiddle1_To_RightHandMiddle2 length 6.2666910000013569
chadd RightHandMiddle1_To_RightHandMiddle2 rx ry rz
chkey -f 1 -F 'chop("../mocap/data/RightHandMiddle1_To_RightHandMiddle2:rx")' RightHandMiddle1_To_RightHandMiddle2/rx
chkey -f 1 -F 'chop("../mocap/data/RightHandMiddle1_To_RightHandMiddle2:ry")' RightHandMiddle1_To_RightHandMiddle2/ry
chkey -f 1 -F 'chop("../mocap/data/RightHandMiddle1_To_RightHandMiddle2:rz")' RightHandMiddle1_To_RightHandMiddle2/rz

opadd -n bone RightHandMiddle2_To_RightHandMiddle3
chlock RightHandMiddle2_To_RightHandMiddle3 +tx +ty +tz
opset -y on RightHandMiddle2_To_RightHandMiddle3
opparm RightHandMiddle2_To_RightHandMiddle3 dcolor ( 0.12150624394416809 0 1 )
opwire RightHandMiddle1_To_RightHandMiddle2 -0 RightHandMiddle2_To_RightHandMiddle3
"$HH/scripts/obj/bone.cmd" RightHandMiddle2_To_RightHandMiddle3
opparm RightHandMiddle2_To_RightHandMiddle3 crtopcap (0.29999999999999999 0.29999999999999999 0.40000000000000002) crbotcap (0.29999999999999999 0.29999999999999999 0.40000000000000002)
opparm RightHandMiddle2_To_RightHandMiddle3 length 4.3489009999999997
chadd RightHandMiddle2_To_RightHandMiddle3 rx ry rz
chkey -f 1 -F 'chop("../mocap/data/RightHandMiddle2_To_RightHandMiddle3:rx")' RightHandMiddle2_To_RightHandMiddle3/rx
chkey -f 1 -F 'chop("../mocap/data/RightHandMiddle2_To_RightHandMiddle3:ry")' RightHandMiddle2_To_RightHandMiddle3/ry
chkey -f 1 -F 'chop("../mocap/data/RightHandMiddle2_To_RightHandMiddle3:rz")' RightHandMiddle2_To_RightHandMiddle3/rz

opadd -n bone RightHandMiddle3_To_RightHandMiddle4
chlock RightHandMiddle3_To_RightHandMiddle4 +tx +ty +tz
opset -y on RightHandMiddle3_To_RightHandMiddle4
opparm RightHandMiddle3_To_RightHandMiddle4 dcolor ( 0 1 0.97560805082321167 )
opwire RightHandMiddle2_To_RightHandMiddle3 -0 RightHandMiddle3_To_RightHandMiddle4
"$HH/scripts/obj/bone.cmd" RightHandMiddle3_To_RightHandMiddle4
opparm RightHandMiddle3_To_RightHandMiddle4 crtopcap (0.29999999999999999 0.29999999999999999 0.40000000000000002) crbotcap (0.29999999999999999 0.29999999999999999 0.40000000000000002)
opparm RightHandMiddle3_To_RightHandMiddle4 length 3.0002400000033327
chadd RightHandMiddle3_To_RightHandMiddle4 rx ry rz
chkey -f 1 -F 'chop("../mocap/data/RightHandMiddle3_To_RightHandMiddle4:rx")' RightHandMiddle3_To_RightHandMiddle4/rx
chkey -f 1 -F 'chop("../mocap/data/RightHandMiddle3_To_RightHandMiddle4:ry")' RightHandMiddle3_To_RightHandMiddle4/ry
chkey -f 1 -F 'chop("../mocap/data/RightHandMiddle3_To_RightHandMiddle4:rz")' RightHandMiddle3_To_RightHandMiddle4/rz

opadd -n bone RightHandMiddle4_To_RightHandMiddleEnd
chlock RightHandMiddle4_To_RightHandMiddleEnd +tx +ty +tz
opset -y on RightHandMiddle4_To_RightHandMiddleEnd
opparm RightHandMiddle4_To_RightHandMiddleEnd dcolor ( 0.17028985917568207 1 0 )
opwire RightHandMiddle3_To_RightHandMiddle4 -0 RightHandMiddle4_To_RightHandMiddleEnd
"$HH/scripts/obj/bone.cmd" RightHandMiddle4_To_RightHandMiddleEnd
opparm RightHandMiddle4_To_RightHandMiddleEnd crtopcap (0.29999999999999999 0.29999999999999999 0.40000000000000002) crbotcap (0.29999999999999999 0.29999999999999999 0.40000000000000002)
opparm RightHandMiddle4_To_RightHandMiddleEnd length 2.3214770000068921
chadd RightHandMiddle4_To_RightHandMiddleEnd rx ry rz
chkey -f 1 -F 'chop("../mocap/data/RightHandMiddle4_To_RightHandMiddleEnd:rx")' RightHandMiddle4_To_RightHandMiddleEnd/rx
chkey -f 1 -F 'chop("../mocap/data/RightHandMiddle4_To_RightHandMiddleEnd:ry")' RightHandMiddle4_To_RightHandMiddleEnd/ry
chkey -f 1 -F 'chop("../mocap/data/RightHandMiddle4_To_RightHandMiddleEnd:rz")' RightHandMiddle4_To_RightHandMiddleEnd/rz

opadd -n bone RightHand_To_RightHandRing1
chlock RightHand_To_RightHandRing1 +tx +ty +tz
opset -y on RightHand_To_RightHandRing1
opparm RightHand_To_RightHandRing1 dcolor ( 1 0.68381208181381226 0 )
opwire RightForeArm_To_RightHand -0 RightHand_To_RightHandRing1
"$HH/scripts/obj/bone.cmd" RightHand_To_RightHandRing1
opparm RightHand_To_RightHandRing1 crtopcap (0.29999999999999999 0.29999999999999999 0.40000000000000002) crbotcap (0.29999999999999999 0.29999999999999999 0.40000000000000002)
opparm RightHand_To_RightHandRing1 length 2.9029669808079115
chadd RightHand_To_RightHandRing1 rx ry rz
chkey -f 1 -F 'chop("../mocap/data/RightHand_To_RightHandRing1:rx")' RightHand_To_RightHandRing1/rx
chkey -f 1 -F 'chop("../mocap/data/RightHand_To_RightHandRing1:ry")' RightHand_To_RightHandRing1/ry
chkey -f 1 -F 'chop("../mocap/data/RightHand_To_RightHandRing1:rz")' RightHand_To_RightHandRing1/rz

opadd -n bone RightHandRing1_To_RightHandRing2
chlock RightHandRing1_To_RightHandRing2 +tx +ty +tz
opset -y on RightHandRing1_To_RightHandRing2
opparm RightHandRing1_To_RightHandRing2 dcolor ( 1 0 0.46208599209785461 )
opwire RightHand_To_RightHandRing1 -0 RightHandRing1_To_RightHandRing2
"$HH/scripts/obj/bone.cmd" RightHandRing1_To_RightHandRing2
opparm RightHandRing1_To_RightHandRing2 crtopcap (0.29999999999999999 0.29999999999999999 0.40000000000000002) crbotcap (0.29999999999999999 0.29999999999999999 0.40000000000000002)
opparm RightHandRing1_To_RightHandRing2 length 6.0328350000014099
chadd RightHandRing1_To_RightHandRing2 rx ry rz
chkey -f 1 -F 'chop("../mocap/data/RightHandRing1_To_RightHandRing2:rx")' RightHandRing1_To_RightHandRing2/rx
chkey -f 1 -F 'chop("../mocap/data/RightHandRing1_To_RightHandRing2:ry")' RightHandRing1_To_RightHandRing2/ry
chkey -f 1 -F 'chop("../mocap/data/RightHandRing1_To_RightHandRing2:rz")' RightHandRing1_To_RightHandRing2/rz

opadd -n bone RightHandRing2_To_RightHandRing3
chlock RightHandRing2_To_RightHandRing3 +tx +ty +tz
opset -y on RightHandRing2_To_RightHandRing3
opparm RightHandRing2_To_RightHandRing3 dcolor ( 0.39201608300209045 0 1 )
opwire RightHandRing1_To_RightHandRing2 -0 RightHandRing2_To_RightHandRing3
"$HH/scripts/obj/bone.cmd" RightHandRing2_To_RightHandRing3
opparm RightHandRing2_To_RightHandRing3 crtopcap (0.29999999999999999 0.29999999999999999 0.40000000000000002) crbotcap (0.29999999999999999 0.29999999999999999 0.40000000000000002)
opparm RightHandRing2_To_RightHandRing3 length 4.3388100000018435
chadd RightHandRing2_To_RightHandRing3 rx ry rz
chkey -f 1 -F 'chop("../mocap/data/RightHandRing2_To_RightHandRing3:rx")' RightHandRing2_To_RightHandRing3/rx
chkey -f 1 -F 'chop("../mocap/data/RightHandRing2_To_RightHandRing3:ry")' RightHandRing2_To_RightHandRing3/ry
chkey -f 1 -F 'chop("../mocap/data/RightHandRing2_To_RightHandRing3:rz")' RightHandRing2_To_RightHandRing3/rz

opadd -n bone RightHandRing3_To_RightHandRing4
chlock RightHandRing3_To_RightHandRing4 +tx +ty +tz
opset -y on RightHandRing3_To_RightHandRing4
opparm RightHandRing3_To_RightHandRing4 dcolor ( 0 0.75388211011886597 1 )
opwire RightHandRing2_To_RightHandRing3 -0 RightHandRing3_To_RightHandRing4
"$HH/scripts/obj/bone.cmd" RightHandRing3_To_RightHandRing4
opparm RightHandRing3_To_RightHandRing4 crtopcap (0.29999999999999999 0.29999999999999999 0.40000000000000002) crbotcap (0.29999999999999999 0.29999999999999999 0.40000000000000002)
opparm RightHandRing3_To_RightHandRing4 length 2.6549030000060267
chadd RightHandRing3_To_RightHandRing4 rx ry rz
chkey -f 1 -F 'chop("../mocap/data/RightHandRing3_To_RightHandRing4:rx")' RightHandRing3_To_RightHandRing4/rx
chkey -f 1 -F 'chop("../mocap/data/RightHandRing3_To_RightHandRing4:ry")' RightHandRing3_To_RightHandRing4/ry
chkey -f 1 -F 'chop("../mocap/data/RightHandRing3_To_RightHandRing4:rz")' RightHandRing3_To_RightHandRing4/rz

opadd -n bone RightHandRing4_To_RightHandRingEnd
chlock RightHandRing4_To_RightHandRingEnd +tx +ty +tz
opset -y on RightHandRing4_To_RightHandRingEnd
opparm RightHandRing4_To_RightHandRingEnd dcolor ( 0 1 0.1002199798822403 )
opwire RightHandRing3_To_RightHandRing4 -0 RightHandRing4_To_RightHandRingEnd
"$HH/scripts/obj/bone.cmd" RightHandRing4_To_RightHandRingEnd
opparm RightHandRing4_To_RightHandRingEnd crtopcap (0.29999999999999999 0.29999999999999999 0.40000000000000002) crbotcap (0.29999999999999999 0.29999999999999999 0.40000000000000002)
opparm RightHandRing4_To_RightHandRingEnd length 1.9351220000041343
chadd RightHandRing4_To_RightHandRingEnd rx ry rz
chkey -f 1 -F 'chop("../mocap/data/RightHandRing4_To_RightHandRingEnd:rx")' RightHandRing4_To_RightHandRingEnd/rx
chkey -f 1 -F 'chop("../mocap/data/RightHandRing4_To_RightHandRingEnd:ry")' RightHandRing4_To_RightHandRingEnd/ry
chkey -f 1 -F 'chop("../mocap/data/RightHandRing4_To_RightHandRingEnd:rz")' RightHandRing4_To_RightHandRingEnd/rz

opadd -n bone RightHand_To_RightHandPinky1
chlock RightHand_To_RightHandPinky1 +tx +ty +tz
opset -y on RightHand_To_RightHandPinky1
opparm RightHand_To_RightHandPinky1 dcolor ( 1 0.95432192087173462 0 )
opwire RightForeArm_To_RightHand -0 RightHand_To_RightHandPinky1
"$HH/scripts/obj/bone.cmd" RightHand_To_RightHandPinky1
opparm RightHand_To_RightHandPinky1 crtopcap (0.29999999999999999 0.29999999999999999 0.40000000000000002) crbotcap (0.29999999999999999 0.29999999999999999 0.40000000000000002)
opparm RightHand_To_RightHandPinky1 length 3.2929343273434712
chadd RightHand_To_RightHandPinky1 rx ry rz
chkey -f 1 -F 'chop("../mocap/data/RightHand_To_RightHandPinky1:rx")' RightHand_To_RightHandPinky1/rx
chkey -f 1 -F 'chop("../mocap/data/RightHand_To_RightHandPinky1:ry")' RightHand_To_RightHandPinky1/ry
chkey -f 1 -F 'chop("../mocap/data/RightHand_To_RightHandPinky1:rz")' RightHand_To_RightHandPinky1/rz

opadd -n bone RightHandPinky1_To_RightHandPinky2
chlock RightHandPinky1_To_RightHandPinky2 +tx +ty +tz
opset -y on RightHandPinky1_To_RightHandPinky2
opparm RightHandPinky1_To_RightHandPinky2 dcolor ( 1 0 0.19157613813877106 )
opwire RightHand_To_RightHandPinky1 -0 RightHandPinky1_To_RightHandPinky2
"$HH/scripts/obj/bone.cmd" RightHandPinky1_To_RightHandPinky2
opparm RightHandPinky1_To_RightHandPinky2 crtopcap (0.29999999999999999 0.29999999999999999 0.40000000000000002) crbotcap (0.29999999999999999 0.29999999999999999 0.40000000000000002)
opparm RightHandPinky1_To_RightHandPinky2 length 5.5531770000003595
chadd RightHandPinky1_To_RightHandPinky2 rx ry rz
chkey -f 1 -F 'chop("../mocap/data/RightHandPinky1_To_RightHandPinky2:rx")' RightHandPinky1_To_RightHandPinky2/rx
chkey -f 1 -F 'chop("../mocap/data/RightHandPinky1_To_RightHandPinky2:ry")' RightHandPinky1_To_RightHandPinky2/ry
chkey -f 1 -F 'chop("../mocap/data/RightHandPinky1_To_RightHandPinky2:rz")' RightHandPinky1_To_RightHandPinky2/rz

opadd -n bone RightHandPinky2_To_RightHandPinky3
chlock RightHandPinky2_To_RightHandPinky3 +tx +ty +tz
opset -y on RightHandPinky2_To_RightHandPinky3
opparm RightHandPinky2_To_RightHandPinky3 dcolor ( 0.66252595186233521 0 1 )
opwire RightHandPinky1_To_RightHandPinky2 -0 RightHandPinky2_To_RightHandPinky3
"$HH/scripts/obj/bone.cmd" RightHandPinky2_To_RightHandPinky3
opparm RightHandPinky2_To_RightHandPinky3 crtopcap (0.29999999999999999 0.29999999999999999 0.40000000000000002) crbotcap (0.29999999999999999 0.29999999999999999 0.40000000000000002)
opparm RightHandPinky2_To_RightHandPinky3 length 3.0626640000027749
chadd RightHandPinky2_To_RightHandPinky3 rx ry rz
chkey -f 1 -F 'chop("../mocap/data/RightHandPinky2_To_RightHandPinky3:rx")' RightHandPinky2_To_RightHandPinky3/rx
chkey -f 1 -F 'chop("../mocap/data/RightHandPinky2_To_RightHandPinky3:ry")' RightHandPinky2_To_RightHandPinky3/ry
chkey -f 1 -F 'chop("../mocap/data/RightHandPinky2_To_RightHandPinky3:rz")' RightHandPinky2_To_RightHandPinky3/rz

opadd -n bone RightHandPinky3_To_RightHandPinky4
chlock RightHandPinky3_To_RightHandPinky4 +tx +ty +tz
opset -y on RightHandPinky3_To_RightHandPinky4
opparm RightHandPinky3_To_RightHandPinky4 dcolor ( 0 0.48337224125862122 1 )
opwire RightHandPinky2_To_RightHandPinky3 -0 RightHandPinky3_To_RightHandPinky4
"$HH/scripts/obj/bone.cmd" RightHandPinky3_To_RightHandPinky4
opparm RightHandPinky3_To_RightHandPinky4 crtopcap (0.29999999999999999 0.29999999999999999 0.40000000000000002) crbotcap (0.29999999999999999 0.29999999999999999 0.40000000000000002)
opparm RightHandPinky3_To_RightHandPinky4 length 1.5465290000064662
chadd RightHandPinky3_To_RightHandPinky4 rx ry rz
chkey -f 1 -F 'chop("../mocap/data/RightHandPinky3_To_RightHandPinky4:rx")' RightHandPinky3_To_RightHandPinky4/rx
chkey -f 1 -F 'chop("../mocap/data/RightHandPinky3_To_RightHandPinky4:ry")' RightHandPinky3_To_RightHandPinky4/ry
chkey -f 1 -F 'chop("../mocap/data/RightHandPinky3_To_RightHandPinky4:rz")' RightHandPinky3_To_RightHandPinky4/rz

opadd -n bone RightHandPinky4_To_RightHandPinkyEnd
chlock RightHandPinky4_To_RightHandPinkyEnd +tx +ty +tz
opset -y on RightHandPinky4_To_RightHandPinkyEnd
opparm RightHandPinky4_To_RightHandPinkyEnd dcolor ( 0 1 0.37072983384132385 )
opwire RightHandPinky3_To_RightHandPinky4 -0 RightHandPinky4_To_RightHandPinkyEnd
"$HH/scripts/obj/bone.cmd" RightHandPinky4_To_RightHandPinkyEnd
opparm RightHandPinky4_To_RightHandPinkyEnd crtopcap (0.29999999999999999 0.29999999999999999 0.40000000000000002) crbotcap (0.29999999999999999 0.29999999999999999 0.40000000000000002)
opparm RightHandPinky4_To_RightHandPinkyEnd length 1.9523410000040977
chadd RightHandPinky4_To_RightHandPinkyEnd rx ry rz
chkey -f 1 -F 'chop("../mocap/data/RightHandPinky4_To_RightHandPinkyEnd:rx")' RightHandPinky4_To_RightHandPinkyEnd/rx
chkey -f 1 -F 'chop("../mocap/data/RightHandPinky4_To_RightHandPinkyEnd:ry")' RightHandPinky4_To_RightHandPinkyEnd/ry
chkey -f 1 -F 'chop("../mocap/data/RightHandPinky4_To_RightHandPinkyEnd:rz")' RightHandPinky4_To_RightHandPinkyEnd/rz

opadd -n bone Hips_To_LeftLeg
chlock Hips_To_LeftLeg +tx +ty +tz
opset -y on Hips_To_LeftLeg
opparm Hips_To_LeftLeg dcolor ( 0.77516824007034302 1 0 )
opwire Root_To_Hips -0 Hips_To_LeftLeg
"$HH/scripts/obj/bone.cmd" Hips_To_LeftLeg
opparm Hips_To_LeftLeg crtopcap (0.29999999999999999 0.29999999999999999 0.40000000000000002) crbotcap (0.29999999999999999 0.29999999999999999 0.40000000000000002)
opparm Hips_To_LeftLeg length 13.369547246038701
chadd Hips_To_LeftLeg rx ry rz
chkey -f 1 -F 'chop("../mocap/data/Hips_To_LeftLeg:rx")' Hips_To_LeftLeg/rx
chkey -f 1 -F 'chop("../mocap/data/Hips_To_LeftLeg:ry")' Hips_To_LeftLeg/ry
chkey -f 1 -F 'chop("../mocap/data/Hips_To_LeftLeg:rz")' Hips_To_LeftLeg/rz

opadd -n bone LeftLeg_To_LeftShin
chlock LeftLeg_To_LeftShin +tx +ty +tz
opset -y on LeftLeg_To_LeftShin
opparm LeftLeg_To_LeftShin dcolor ( 1 0.078933708369731903 0 )
opwire Hips_To_LeftLeg -0 LeftLeg_To_LeftShin
"$HH/scripts/obj/bone.cmd" LeftLeg_To_LeftShin
opparm LeftLeg_To_LeftShin crtopcap (0.29999999999999999 0.29999999999999999 0.40000000000000002) crbotcap (0.29999999999999999 0.29999999999999999 0.40000000000000002)
opparm LeftLeg_To_LeftShin length 43.229198000000018
chadd LeftLeg_To_LeftShin rx ry rz
chkey -f 1 -F 'chop("../mocap/data/LeftLeg_To_LeftShin:rx")' LeftLeg_To_LeftShin/rx
chkey -f 1 -F 'chop("../mocap/data/LeftLeg_To_LeftShin:ry")' LeftLeg_To_LeftShin/ry
chkey -f 1 -F 'chop("../mocap/data/LeftLeg_To_LeftShin:rz")' LeftLeg_To_LeftShin/rz

opadd -n bone LeftShin_To_LeftFoot
chlock LeftShin_To_LeftFoot +tx +ty +tz
opset -y on LeftShin_To_LeftFoot
opparm LeftShin_To_LeftFoot dcolor ( 0.93303579092025757 0 1 )
opwire LeftLeg_To_LeftShin -0 LeftShin_To_LeftFoot
"$HH/scripts/obj/bone.cmd" LeftShin_To_LeftFoot
opparm LeftShin_To_LeftFoot crtopcap (0.29999999999999999 0.29999999999999999 0.40000000000000002) crbotcap (0.29999999999999999 0.29999999999999999 0.40000000000000002)
opparm LeftShin_To_LeftFoot length 42.298611000000022
chadd LeftShin_To_LeftFoot rx ry rz
chkey -f 1 -F 'chop("../mocap/data/LeftShin_To_LeftFoot:rx")' LeftShin_To_LeftFoot/rx
chkey -f 1 -F 'chop("../mocap/data/LeftShin_To_LeftFoot:ry")' LeftShin_To_LeftFoot/ry
chkey -f 1 -F 'chop("../mocap/data/LeftShin_To_LeftFoot:rz")' LeftShin_To_LeftFoot/rz

opadd -n bone LeftFoot_To_LeftToeBase
chlock LeftFoot_To_LeftToeBase +tx +ty +tz
opset -y on LeftFoot_To_LeftToeBase
opparm LeftFoot_To_LeftToeBase dcolor ( 0 0.21286240220069885 1 )
opwire LeftShin_To_LeftFoot -0 LeftFoot_To_LeftToeBase
"$HH/scripts/obj/bone.cmd" LeftFoot_To_LeftToeBase
opparm LeftFoot_To_LeftToeBase crtopcap (0.29999999999999999 0.29999999999999999 0.40000000000000002) crbotcap (0.29999999999999999 0.29999999999999999 0.40000000000000002)
opparm LeftFoot_To_LeftToeBase length 14.165858000000036
chadd LeftFoot_To_LeftToeBase rx ry rz
chkey -f 1 -F 'chop("../mocap/data/LeftFoot_To_LeftToeBase:rx")' LeftFoot_To_LeftToeBase/rx
chkey -f 1 -F 'chop("../mocap/data/LeftFoot_To_LeftToeBase:ry")' LeftFoot_To_LeftToeBase/ry
chkey -f 1 -F 'chop("../mocap/data/LeftFoot_To_LeftToeBase:rz")' LeftFoot_To_LeftToeBase/rz

opadd -n bone LeftToeBase_To_LeftToeEnd
chlock LeftToeBase_To_LeftToeEnd +tx +ty +tz
opset -y on LeftToeBase_To_LeftToeEnd
opparm LeftToeBase_To_LeftToeEnd dcolor ( 0 1 0.6412397027015686 )
opwire LeftFoot_To_LeftToeBase -0 LeftToeBase_To_LeftToeEnd
"$HH/scripts/obj/bone.cmd" LeftToeBase_To_LeftToeEnd
opparm LeftToeBase_To_LeftToeEnd crtopcap (0.29999999999999999 0.29999999999999999 0.40000000000000002) crbotcap (0.29999999999999999 0.29999999999999999 0.40000000000000002)
opparm LeftToeBase_To_LeftToeEnd length 6.7181925225852979
chadd LeftToeBase_To_LeftToeEnd rx ry rz
chkey -f 1 -F 'chop("../mocap/data/LeftToeBase_To_LeftToeEnd:rx")' LeftToeBase_To_LeftToeEnd/rx
chkey -f 1 -F 'chop("../mocap/data/LeftToeBase_To_LeftToeEnd:ry")' LeftToeBase_To_LeftToeEnd/ry
chkey -f 1 -F 'chop("../mocap/data/LeftToeBase_To_LeftToeEnd:rz")' LeftToeBase_To_LeftToeEnd/rz

opadd -n bone Hips_To_RightLeg
chlock Hips_To_RightLeg +tx +ty +tz
opset -y on Hips_To_RightLeg
opparm Hips_To_RightLeg dcolor ( 0.50465840101242065 1 0 )
opwire Root_To_Hips -0 Hips_To_RightLeg
"$HH/scripts/obj/bone.cmd" Hips_To_RightLeg
opparm Hips_To_RightLeg crtopcap (0.29999999999999999 0.29999999999999999 0.40000000000000002) crbotcap (0.29999999999999999 0.29999999999999999 0.40000000000000002)
opparm Hips_To_RightLeg length 13.290040484011101
chadd Hips_To_RightLeg rx ry rz
chkey -f 1 -F 'chop("../mocap/data/Hips_To_RightLeg:rx")' Hips_To_RightLeg/rx
chkey -f 1 -F 'chop("../mocap/data/Hips_To_RightLeg:ry")' Hips_To_RightLeg/ry
chkey -f 1 -F 'chop("../mocap/data/Hips_To_RightLeg:rz")' Hips_To_RightLeg/rz

opadd -n bone RightLeg_To_RightShin
chlock RightLeg_To_RightShin +tx +ty +tz
opset -y on RightLeg_To_RightShin
opparm RightLeg_To_RightShin dcolor ( 1 0.34944352507591248 0 )
opwire Hips_To_RightLeg -0 RightLeg_To_RightShin
"$HH/scripts/obj/bone.cmd" RightLeg_To_RightShin
opparm RightLeg_To_RightShin crtopcap (0.29999999999999999 0.29999999999999999 0.40000000000000002) crbotcap (0.29999999999999999 0.29999999999999999 0.40000000000000002)
opparm RightLeg_To_RightShin length 43.369682000000012
chadd RightLeg_To_RightShin rx ry rz
chkey -f 1 -F 'chop("../mocap/data/RightLeg_To_RightShin:rx")' RightLeg_To_RightShin/rx
chkey -f 1 -F 'chop("../mocap/data/RightLeg_To_RightShin:ry")' RightLeg_To_RightShin/ry
chkey -f 1 -F 'chop("../mocap/data/RightLeg_To_RightShin:rz")' RightLeg_To_RightShin/rz

opadd -n bone RightShin_To_RightFoot
chlock RightShin_To_RightFoot +tx +ty +tz
opset -y on RightShin_To_RightFoot
opparm RightShin_To_RightFoot dcolor ( 1 0 0.79645437002182007 )
opwire RightLeg_To_RightShin -0 RightShin_To_RightFoot
"$HH/scripts/obj/bone.cmd" RightShin_To_RightFoot
opparm RightShin_To_RightFoot crtopcap (0.29999999999999999 0.29999999999999999 0.40000000000000002) crbotcap (0.29999999999999999 0.29999999999999999 0.40000000000000002)
opparm RightShin_To_RightFoot length 42.260784000000235
chadd RightShin_To_RightFoot rx ry rz
chkey -f 1 -F 'chop("../mocap/data/RightShin_To_RightFoot:rx")' RightShin_To_RightFoot/rx
chkey -f 1 -F 'chop("../mocap/data/RightShin_To_RightFoot:ry")' RightShin_To_RightFoot/ry
chkey -f 1 -F 'chop("../mocap/data/RightShin_To_RightFoot:rz")' RightShin_To_RightFoot/rz

opadd -n bone RightFoot_To_RightToeBase
chlock RightFoot_To_RightToeBase +tx +ty +tz
opset -y on RightFoot_To_RightToeBase
opparm RightFoot_To_RightToeBase dcolor ( 0.057647451758384705 0 1 )
opwire RightShin_To_RightFoot -0 RightFoot_To_RightToeBase
"$HH/scripts/obj/bone.cmd" RightFoot_To_RightToeBase
opparm RightFoot_To_RightToeBase crtopcap (0.29999999999999999 0.29999999999999999 0.40000000000000002) crbotcap (0.29999999999999999 0.29999999999999999 0.40000000000000002)
opparm RightFoot_To_RightToeBase length 14.222245000000175
chadd RightFoot_To_RightToeBase rx ry rz
chkey -f 1 -F 'chop("../mocap/data/RightFoot_To_RightToeBase:rx")' RightFoot_To_RightToeBase/rx
chkey -f 1 -F 'chop("../mocap/data/RightFoot_To_RightToeBase:ry")' RightFoot_To_RightToeBase/ry
chkey -f 1 -F 'chop("../mocap/data/RightFoot_To_RightToeBase:rz")' RightFoot_To_RightToeBase/rz

opadd -n bone RightToeBase_To_RightToeEnd
chlock RightToeBase_To_RightToeEnd +tx +ty +tz
opset -y on RightToeBase_To_RightToeEnd
opparm RightToeBase_To_RightToeEnd dcolor ( 0 1 0.91174954175949097 )
opwire RightFoot_To_RightToeBase -0 RightToeBase_To_RightToeEnd
"$HH/scripts/obj/bone.cmd" RightToeBase_To_RightToeEnd
opparm RightToeBase_To_RightToeEnd crtopcap (0.29999999999999999 0.29999999999999999 0.40000000000000002) crbotcap (0.29999999999999999 0.29999999999999999 0.40000000000000002)
opparm RightToeBase_To_RightToeEnd length 6.6641215857248577
chadd RightToeBase_To_RightToeEnd rx ry rz
chkey -f 1 -F 'chop("../mocap/data/RightToeBase_To_RightToeEnd:rx")' RightToeBase_To_RightToeEnd/rx
chkey -f 1 -F 'chop("../mocap/data/RightToeBase_To_RightToeEnd:ry")' RightToeBase_To_RightToeEnd/ry
chkey -f 1 -F 'chop("../mocap/data/RightToeBase_To_RightToeEnd:rz")' RightToeBase_To_RightToeEnd/rz



# Create CHOP net to store this motion
opadd chopnet mocap
opcf mocap
opadd file E__script_pythonWorkSpace_kimodo_test_outputs_walk_natural_6s_post
opparm E__script_pythonWorkSpace_kimodo_test_outputs_walk_natural_6s_post file ( '$HIP/E:\script\pythonWorkSpace\kimodo_test_outputs\walk_natural_6s_post.bclip' ) rate (30) rateoption ( override ) export ( ../.. )
opadd null data
opparm data export ( ../.. )
opwire E__script_pythonWorkSpace_kimodo_test_outputs_walk_natural_6s_post -0 data
oplayout
opcf ..

# Layout the object nodes
oplayout
opautoplace mocap


opcf $saved_path
