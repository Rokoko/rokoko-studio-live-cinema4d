'''These tables hold the strings for automatic rig and face morph detection.'''

#   nameStudio           : (nameDisplay,                       type,[namesMain],                             [nameAttrNeeded],    [nameAttrForbidden],      [nameSideInclude], [nameSideExclude])   # noqa: E241, E501
STUDIO_NAMES_TO_GUESS = {
    "hip"                : (0,  "Hips"                        , 1,  [["hip"], ["pelvis"]],                   [],                  [],                       [],                []               ),  # noqa: E202, E203, E241, E501
    "spine"              : (1,  "Spine"                       , 1,  [["spine"]],                             [],                  [],                       [],                []               ),  # noqa: E202, E203, E241, E501
    "chest"              : (2,  "Chest"                       , 1,  [["chest"], ["spine", "4"]],             [],                  [],                       [],                []               ),  # noqa: E202, E203, E241, E501
    "neck"               : (3,  "Neck"                        , 1,  [["neck"]],                              [],                  [],                       [],                []               ),  # noqa: E202, E203, E241, E501
    "head"               : (4,  "Head"                        , 1,  [["head"]],                              [],                  ["tip", "end", "vertex"], [],                []               ),  # noqa: E202, E203, E241, E501
    "leftShoulder"       : (5,  "Left Shoulder"               , 1,  [["shoulder"], ["collar"]],              [],                  [],                       ["left"],          ["right", "___R"]),  # noqa: E202, E203, E241, E501
    "leftUpperArm"       : (6,  "Left Upper Arm"              , 1,  [["arm"]],                               [],                  ["low", "fore"],          ["left"],          ["right", "___R"]),  # noqa: E202, E203, E241, E501
    "leftLowerArm"       : (7,  "Left Forearm"                , 1,  [["arm", "low"], ["forearm"]],           [],                  ["up"],                   ["left"],          ["right", "___R"]),  # noqa: E202, E203, E241, E501
    "leftHand"           : (8,  "Left Hand"                   , 1,  [["hand"]],                              [],                  [],                       ["left"],          ["right", "___R"]),  # noqa: E202, E203, E241, E501
    "rightShoulder"      : (9,  "Right Shoulder"              , 1,  [["shoulder"], ["collar"]],              [],                  [],                       ["right", "___R"], ["left"]         ),  # noqa: E202, E203, E241, E501
    "rightUpperArm"      : (10, "Right Upper Arm"             , 1,  [["arm"]],                               [],                  ["low", "fore"],          ["right", "___R"], ["left"]         ),  # noqa: E202, E203, E241, E501
    "rightLowerArm"      : (11, "Right ForeArm"               , 1,  [["arm", "low"], ["forearm"]],           [],                  ["up"],                   ["right", "___R"], ["left"]         ),  # noqa: E202, E203, E241, E501
    "rightHand"          : (12, "Right Hand"                  , 1,  [["hand"]],                              [],                  [],                       ["right", "___R"], ["left"]         ),  # noqa: E202, E203, E241, E501
    "leftUpLeg"          : (13, "Left Thigh"                  , 1,  [["leg", "up"], ["thigh"]],              [],                  ["low"],                  ["left"],          ["right", "___R"]),  # noqa: E202, E203, E241, E501
    "leftLeg"            : (14, "Left Shin"                   , 1,  [["shin"], ["leg"]],                     [],                  ["up"],                   ["left"],          ["right", "___R"]),  # noqa: E202, E203, E241, E501
    "leftFoot"           : (15, "Left Foot"                   , 1,  [["foot"]],                              [],                  [],                       ["left"],          ["right", "___R"]),  # noqa: E202, E203, E241, E501
    "leftToe"            : (16, "Left Toe"                    , 1,  [["toe"]],                               [],                  ["end", "tip"],           ["left"],          ["right", "___R"]),  # noqa: E202, E203, E241, E501
    "leftToeEnd"         : (17, "Left Toe Tip"                , 1,  [["toe", "end"], ["toe", "tip"]],        [],                  [],                       ["left"],          ["right", "___R"]),  # noqa: E202, E203, E241, E501
    "rightUpLeg"         : (18, "Right Thigh"                 , 1,  [["leg", "up"], ["thigh"]],              [],                  ["low"],                  ["right", "___R"], ["left"]         ),  # noqa: E202, E203, E241, E501
    "rightLeg"           : (19, "Right Shin"                  , 1,  [["shin"], ["leg"]],                     [],                  ["up"],                   ["right", "___R"], ["left"]         ),  # noqa: E202, E203, E241, E501
    "rightFoot"          : (20, "Right Foot"                  , 1,  [["foot"]],                              [],                  [],                       ["right", "___R"], ["left"]         ),  # noqa: E202, E203, E241, E501
    "rightToe"           : (21, "Right Toe"                   , 1,  [["toe"]],                               [],                  ["end", "tip"],           ["right", "___R"], ["left"]         ),  # noqa: E202, E203, E241, E501
    "rightToeEnd"        : (22, "Right Toe Tip"               , 1,  [["toe", "end"], ["toe", "tip"]],        [],                  [],                       ["right", "___R"], ["left"]         ),  # noqa: E202, E203, E241, E501
    "leftThumbProximal"  : (23, "Left Thumb Metacarpal"       , 6,  [["thumb"], ["finger", "1"]],            ["metacarpal", "0"], [],                       ["left"],          ["right", "___R"]),  # noqa: E202, E203, E241, E501
    "leftThumbMedial"    : (24, "Left Thumb Proximal"         , 6,  [["thumb"], ["finger", "1"]],            ["proximal", "1"],   [],                       ["left"],          ["right", "___R"]),  # noqa: E202, E203, E241, E501
    "leftThumbDistal"    : (25, "Left Thumb Distal"           , 6,  [["thumb"], ["finger", "1"]],            ["distal", "2"],     [],                       ["left"],          ["right", "___R"]),  # noqa: E202, E203, E241, E501
    "leftThumbTip"       : (26, "Left Thumb Tip"              , 6,  [["thumb"], ["finger", "1"]],            ["tip", "end", "3"], [],                       ["left"],          ["right", "___R"]),  # noqa: E202, E203, E241, E501
    "leftIndexProximal"  : (27, "Left Index Finger Proximal"  , 6,  [["index"], ["finger", "2"]],            ["proximal", "1"],   ["metacarpal"],           ["left"],          ["right", "___R"]),  # noqa: E202, E203, E241, E501
    "leftIndexMedial"    : (28, "Left Index Finger Medial"    , 6,  [["index"], ["finger", "2"]],            ["medial", "2"],     ["metacarpal"],           ["left"],          ["right", "___R"]),  # noqa: E202, E203, E241, E501
    "leftIndexDistal"    : (29, "Left Index Finger Distal"    , 6,  [["index"], ["finger", "2"]],            ["distal", "3"],     ["metacarpal"],           ["left"],          ["right", "___R"]),  # noqa: E202, E203, E241, E501
    "leftIndexTip"       : (30, "Left Index Finger Tip"       , 6,  [["index"], ["finger", "2"]],            ["tip", "end", "4"], ["metacarpal"],           ["left"],          ["right", "___R"]),  # noqa: E202, E203, E241, E501
    "leftMiddleProximal" : (31, "Left Middle Finger Proximal" , 6,  [["middle"], ["finger", "3"]],           ["proximal", "1"],   ["metacarpal"],           ["left"],          ["right", "___R"]),  # noqa: E202, E203, E241, E501
    "leftMiddleMedial"   : (32, "Left Middle Finger Medial"   , 6,  [["middle"], ["finger", "3"]],           ["medial", "2"],     ["metacarpal"],           ["left"],          ["right", "___R"]),  # noqa: E202, E203, E241, E501
    "leftMiddleDistal"   : (33, "Left Middle Finger Distal"   , 6,  [["middle"], ["finger", "3"]],           ["distal", "3"],     ["metacarpal"],           ["left"],          ["right", "___R"]),  # noqa: E202, E203, E241, E501
    "leftMiddleTip"      : (34, "Left Middle Finger Tip"      , 6,  [["middle"], ["finger", "3"]],           ["tip", "end", "4"], ["metacarpal"],           ["left"],          ["right", "___R"]),  # noqa: E202, E203, E241, E501
    "leftRingProximal"   : (35, "Left Ring Finger Proximal"   , 6,  [["ring"], ["finger", "4"]],             ["proximal", "1"],   ["metacarpal"],           ["left"],          ["right", "___R"]),  # noqa: E202, E203, E241, E501
    "leftRingMedial"     : (36, "Left Ring Finger Medial"     , 6,  [["ring"], ["finger", "4"]],             ["medial", "2"],     ["metacarpal"],           ["left"],          ["right", "___R"]),  # noqa: E202, E203, E241, E501
    "leftRingDistal"     : (37, "Left Ring Finger Distal"     , 6,  [["ring"], ["finger", "4"]],             ["distal", "3"],     ["metacarpal"],           ["left"],          ["right", "___R"]),  # noqa: E202, E203, E241, E501
    "leftRingTip"        : (38, "Left Ring Finger Tip"        , 6,  [["ring"], ["finger", "4"]],             ["tip", "end", "4"], ["metacarpal"],           ["left"],          ["right", "___R"]),  # noqa: E202, E203, E241, E501
    "leftLittleProximal" : (39, "Left Little Finger Proximal" , 6,  [["little"], ["finger", "5"], ["pink"]], ["proximal", "1"],   ["metacarpal"],           ["left"],          ["right", "___R"]),  # noqa: E202, E203, E241, E501
    "leftLittleMedial"   : (40, "Left Little Finger Medial"   , 6,  [["little"], ["finger", "5"], ["pink"]], ["medial", "2"],     ["metacarpal"],           ["left"],          ["right", "___R"]),  # noqa: E202, E203, E241, E501
    "leftLittleDistal"   : (41, "Left Little Finger Distal"   , 6,  [["little"], ["finger", "5"], ["pink"]], ["distal", "3"],     ["metacarpal"],           ["left"],          ["right", "___R"]),  # noqa: E202, E203, E241, E501
    "leftLittleTip"      : (42, "Left Little Finger Tip"      , 6,  [["little"], ["finger", "5"], ["pink"]], ["tip", "end", "4"], ["metacarpal"],           ["left"],          ["right", "___R"]),  # noqa: E202, E203, E241, E501
    "rightThumbProximal" : (43, "Right Thumb Metacarpal"      , 10, [["thumb"], ["finger", "1"]],            ["metacarpal", "0"], [],                       ["right", "___R"], ["left"]         ),  # noqa: E202, E203, E241, E501
    "rightThumbMedial"   : (44, "Right Thumb Proximal"        , 10, [["thumb"], ["finger", "1"]],            ["proximal", "1"],   ["metacarpal"],           ["right", "___R"], ["left"]         ),  # noqa: E202, E203, E241, E501
    "rightThumbDistal"   : (45, "Right Thumb Distal"          , 10, [["thumb"], ["finger", "1"]],            ["distal", "2"],     ["metacarpal"],           ["right", "___R"], ["left"]         ),  # noqa: E202, E203, E241, E501
    "rightThumbTip"      : (46, "Right Thumb Tip"             , 10, [["thumb"], ["finger", "1"]],            ["tip", "end", "3"], ["metacarpal"],           ["right", "___R"], ["left"]         ),  # noqa: E202, E203, E241, E501
    "rightIndexProximal" : (47, "Right Index Finger Proximal" , 10, [["index"], ["finger", "2"]],            ["proximal", "1"],   ["metacarpal"],           ["right", "___R"], ["left"]         ),  # noqa: E202, E203, E241, E501
    "rightIndexMedial"   : (48, "Right Index Finger Medial"   , 10, [["index"], ["finger", "2"]],            ["medial", "2"],     ["metacarpal"],           ["right", "___R"], ["left"]         ),  # noqa: E202, E203, E241, E501
    "rightIndexDistal"   : (49, "Right Index Finger Distal"   , 10, [["index"], ["finger", "2"]],            ["distal", "3"],     ["metacarpal"],           ["right", "___R"], ["left"]         ),  # noqa: E202, E203, E241, E501
    "rightIndexTip"      : (50, "Right Index Finger Tip"      , 10, [["index"], ["finger", "2"]],            ["tip", "end", "4"], ["metacarpal"],           ["right", "___R"], ["left"]         ),  # noqa: E202, E203, E241, E501
    "rightMiddleProximal": (51, "Right Middle Finger Proximal", 10, [["middle"], ["finger", "3"]],           ["proximal", "1"],   ["metacarpal"],           ["right", "___R"], ["left"]         ),  # noqa: E202, E203, E241, E501
    "rightMiddleMedial"  : (52, "Right Middle Finger Medial"  , 10, [["middle"], ["finger", "3"]],           ["medial", "2"],     ["metacarpal"],           ["right", "___R"], ["left"]         ),  # noqa: E202, E203, E241, E501
    "rightMiddleDistal"  : (53, "Right Middle Finger Distal"  , 10, [["middle"], ["finger", "3"]],           ["distal", "3"],     ["metacarpal"],           ["right", "___R"], ["left"]         ),  # noqa: E202, E203, E241, E501
    "rightMiddleTip"     : (54, "Right Middle Finger Tip"     , 10, [["middle"], ["finger", "3"]],           ["tip", "end", "4"], ["metacarpal"],           ["right", "___R"], ["left"]         ),  # noqa: E202, E203, E241, E501
    "rightRingProximal"  : (55, "Right Ring Finger Proximal"  , 10, [["ring"], ["finger", "4"]],             ["proximal", "1"],   ["metacarpal"],           ["right", "___R"], ["left"]         ),  # noqa: E202, E203, E241, E501
    "rightRingMedial"    : (56, "Right Ring Finger Medial"    , 10, [["ring"], ["finger", "4"]],             ["medial", "2"],     ["metacarpal"],           ["right", "___R"], ["left"]         ),  # noqa: E202, E203, E241, E501
    "rightRingDistal"    : (57, "Right Ring Finger Distal"    , 10, [["ring"], ["finger", "4"]],             ["distal", "3"],     ["metacarpal"],           ["right", "___R"], ["left"]         ),  # noqa: E202, E203, E241, E501
    "rightRingTip"       : (58, "Right Ring Finger Tip"       , 10, [["ring"], ["finger", "4"]],             ["tip", "end", "4"], ["metacarpal"],           ["right", "___R"], ["left"]         ),  # noqa: E202, E203, E241, E501
    "rightLittleProximal": (59, "Right Little Finger Proximal", 10, [["little"], ["finger", "5"], ["pink"]], ["proximal", "1"],   ["metacarpal"],           ["right", "___R"], ["left"]         ),  # noqa: E202, E203, E241, E501
    "rightLittleMedial"  : (60, "Right Little Finger Medial"  , 10, [["little"], ["finger", "5"], ["pink"]], ["medial", "2"],     ["metacarpal"],           ["right", "___R"], ["left"]         ),  # noqa: E202, E203, E241, E501
    "rightLittleDistal"  : (61, "Right Little Finger Distal"  , 10, [["little"], ["finger", "5"], ["pink"]], ["distal", "3"],     ["metacarpal"],           ["right", "___R"], ["left"]         ),  # noqa: E202, E203, E241, E501
    "rightLittleTip"     : (62, "Right Little Finger Tip"     , 10, [["little"], ["finger", "5"], ["pink"]], ["tip", "end", "4"], ["metacarpal"],           ["right", "___R"], ["left"]         ),  # noqa: E202, E203, E241, E501
}

#   nameStudio              idx, nameDisplay,             [namesMain],                  [namesExclude],      [nameSideInclude], [nameSideExclude])  # noqa: E202, E203, E241, E501
FACE_POSE_NAMES = {
    "eyeBlinkLeft"       : (1,  "Eye Blink Left",         [["eye", "blink"]],           [],                  ["left"],          ["right"]),  # noqa: E202, E203, E241, E501
    "eyeLookDownLeft"    : (2,  "Eye Look Down Left",     [["eye", "look", "down"]],    [],                  ["left"],          ["right"]),  # noqa: E202, E203, E241, E501
    "eyeLookInLeft"      : (3,  "Eye Look In Left",       [["eye", "look", "in"]],      [],                  ["left"],          ["right"]),  # noqa: E202, E203, E241, E501
    "eyeLookOutLeft"     : (4,  "Eye Look Out Left",      [["eye", "look", "out"]],     [],                  ["left"],          ["right"]),  # noqa: E202, E203, E241, E501
    "eyeLookUpLeft"      : (5,  "Eye Look Up Left",       [["eye", "look", "up"]],      [],                  ["left"],          ["right"]),  # noqa: E202, E203, E241, E501
    "eyeSquintLeft"      : (6,  "Eye Squint Left",        [["eye", "squint"]],          [],                  ["left"],          ["right"]),  # noqa: E202, E203, E241, E501
    "eyeWideLeft"        : (7,  "Eye Wide Left",          [["eye", "wide"]],            [],                  ["left"],          ["right"]),  # noqa: E202, E203, E241, E501
    "eyeBlinkRight"      : (8,  "Eye Blink Right",        [["eye", "blink"]],           [],                  ["right"],         ["left"] ),  # noqa: E202, E203, E241, E501
    "eyeLookDownRight"   : (9,  "Eye Look Down Right",    [["eye", "look", "down"]],    [],                  ["right"],         ["left"] ),  # noqa: E202, E203, E241, E501
    "eyeLookInRight"     : (10, "Eye Look In Right",      [["eye", "look", "in"]],      [],                  ["right"],         ["left"] ),  # noqa: E202, E203, E241, E501
    "eyeLookOutRight"    : (11, "Eye Look Out Right",     [["eye", "look", "out"]],     [],                  ["right"],         ["left"] ),  # noqa: E202, E203, E241, E501
    "eyeLookUpRight"     : (12, "Eye Look Up Right",      [["eye", "look", "up"]],      [],                  ["right"],         ["left"] ),  # noqa: E202, E203, E241, E501
    "eyeSquintRight"     : (13, "Eye Squint Right",       [["eye", "squint"]],          [],                  ["right"],         ["left"] ),  # noqa: E202, E203, E241, E501
    "eyeWideRight"       : (14, "Eye Wide Right",         [["eye", "wide"]],            [],                  ["right"],         ["left"] ),  # noqa: E202, E203, E241, E501
    "jawForward"         : (15, "Jaw Forward",            [["jaw", "forward"]],         [],                  [],                []       ),  # noqa: E202, E203, E241, E501
    "jawLeft"            : (16, "Jaw Left",               [["jaw"]],                    ["forward", "open"], ["left"],          ["right"]),  # noqa: E202, E203, E241, E501
    "jawRight"           : (17, "Jaw Right",              [["jaw"]],                    ["forward", "open"], ["right"],         ["left"] ),  # noqa: E202, E203, E241, E501
    "jawOpen"            : (18, "Jaw Open",               [["jaw", "open"]],            [],                  [],                []       ),  # noqa: E202, E203, E241, E501
    "mouthClose"         : (19, "Mouth Close",            [["mouth", "close"]],         [],                  [],                []       ),  # noqa: E202, E203, E241, E501
    "mouthFunnel"        : (20, "Mouth Funnel",           [["mouth", "funnel"]],        [],                  [],                []       ),  # noqa: E202, E203, E241, E501
    "mouthPucker"        : (21, "Mouth Pucker",           [["mouth", "pucker"]],        [],                  [],                []       ),  # noqa: E202, E203, E241, E501
    "mouthLeft"          : (22, "Mouth Left",             [["mouth"]],                  ["close", "funnel", "pucker", "smile", "frown", "dimple", "stretch", "roll", "shrug", "press", "lower", "upper"], ["left"], ["right"]),  # noqa: E202, E203, E241, E501
    "mouthRight"         : (23, "Mouth Right",            [["mouth"]],                  ["close", "funnel", "pucker", "smile", "frown", "dimple", "stretch", "roll", "shrug", "press", "lower", "upper"], ["right"], ["left"]),  # noqa: E202, E203, E241, E501
    "mouthSmileLeft"     : (24, "Mouth Smile Left",       [["mouth", "smile"]],         [],                  ["left"],          ["right"]),  # noqa: E202, E203, E241, E501
    "mouthSmileRight"    : (25, "Mouth Smile Right",      [["mouth", "smile"]],         [],                  ["right"],         ["left"] ),  # noqa: E202, E203, E241, E501
    "mouthFrownLeft"     : (26, "Mouth Frown Left",       [["mouth", "frown"]],         [],                  ["left"],          ["right"]),  # noqa: E202, E203, E241, E501
    "mouthFrownRight"    : (27, "Mouth Frown Right",      [["mouth", "frown"]],         [],                  ["right"],         ["left"] ),  # noqa: E202, E203, E241, E501
    "mouthDimpleLeft"    : (28, "Mouth Dimple Left",      [["mouth", "dimple"]],        [],                  ["left"],          ["right"]),  # noqa: E202, E203, E241, E501
    "mouthDimpleRight"   : (29, "Mouth Dimple Right",     [["mouth", "dimple"]],        [],                  ["right"],         ["left"] ),  # noqa: E202, E203, E241, E501
    "mouthStretchLeft"   : (30, "Mouth Stretch Left",     [["mouth", "stretch"]],       [],                  ["left"],          ["right"]),  # noqa: E202, E203, E241, E501
    "mouthStretchRight"  : (31, "Mouth Stretch Right",    [["mouth", "stretch"]],       [],                  ["right"],         ["left"] ),  # noqa: E202, E203, E241, E501
    "mouthRollLower"     : (32, "Mouth Roll Lower",       [["mouth", "roll"]],          [],                  ["lower"],         ["upper"]),  # noqa: E202, E203, E241, E501
    "mouthRollUpper"     : (33, "Mouth Roll Upper",       [["mouth", "roll"]],          [],                  ["upper"],         ["lower"]),  # noqa: E202, E203, E241, E501
    "mouthShrugLower"    : (34, "Mouth Shrug Lower",      [["mouth", "shrug"]],         [],                  ["lower"],         ["upper"]),  # noqa: E202, E203, E241, E501
    "mouthShrugUpper"    : (35, "Mouth Shrug Upper",      [["mouth", "shrug"]],         [],                  ["upper"],         ["lower"]),  # noqa: E202, E203, E241, E501
    "mouthPressLeft"     : (36, "Mouth Press Left",       [["mouth", "press"]],         [],                  ["left"],          ["right"]),  # noqa: E202, E203, E241, E501
    "mouthPressRight"    : (37, "Mouth Press Right",      [["mouth", "press"]],         [],                  ["right"],         ["left"] ),  # noqa: E202, E203, E241, E501
    "mouthLowerDownLeft" : (38, "Mouth Lower Down Left",  [["mouth", "lower", "down"]], [],                  ["left"],          ["right"]),  # noqa: E202, E203, E241, E501
    "mouthLowerDownRight": (39, "Mouth Lower Down Right", [["mouth", "lower", "down"]], [],                  ["right"],         ["left"] ),  # noqa: E202, E203, E241, E501
    "mouthUpperUpLeft"   : (40, "Mouth Upper Up Left",    [["mouth", "upper", "up"]],   [],                  ["left"],          ["right"]),  # noqa: E202, E203, E241, E501
    "mouthUpperUpRight"  : (41, "Mouth Upper Up Right",   [["mouth", "upper", "up"]],   [],                  ["right"],         ["left"] ),  # noqa: E202, E203, E241, E501
    "browDownLeft"       : (42, "Brow Down Left",         [["brow", "down"]],           [],                  ["left"],          ["right"]),  # noqa: E202, E203, E241, E501
    "browDownRight"      : (43, "Brow Down Right",        [["brow", "down"]],           [],                  ["right"],         ["left"] ),  # noqa: E202, E203, E241, E501
    "browInnerUp"        : (44, "Brow Inner Up",          [["brow", "inner", "up"]],    [],                  [""],              [""]     ),  # noqa: E202, E203, E241, E501
    "browOuterUpLeft"    : (45, "Brow Outer Up Left",     [["brow", "outer", "up"]],    [],                  ["left"],          ["right"]),  # noqa: E202, E203, E241, E501
    "browOuterUpRight"   : (46, "Brow Outer Up Right",    [["brow", "outer", "up"]],    [],                  ["right"],         ["left"] ),  # noqa: E202, E203, E241, E501
    "cheekPuff"          : (47, "Cheek Puff",             [["cheek", "puff"]],          [],                  [""],              [""]     ),  # noqa: E202, E203, E241, E501
    "cheekSquintLeft"    : (48, "Cheek Squint Left",      [["cheek", "squint"]],        [],                  ["left"],          ["right"]),  # noqa: E202, E203, E241, E501
    "cheekSquintRight"   : (49, "Cheek Squint Right",     [["cheek", "squint"]],        [],                  ["right"],         ["left"] ),  # noqa: E202, E203, E241, E501
    "noseSneerLeft"      : (50, "Nose Sneer Left",        [["nose", "sneer"]],          [],                  ["left"],          ["right"]),  # noqa: E202, E203, E241, E501
    "noseSneerRight"     : (51, "Nose Sneer Right",       [["nose", "sneer"]],          [],                  ["right"],         ["left"] ),  # noqa: E202, E203, E241, E501
    "tongueOut"          : (52, "Tongue Out",             [["tongue", "out"]],          [],                  [],                []       ),  # noqa: E202, E203, E241, E501
}
