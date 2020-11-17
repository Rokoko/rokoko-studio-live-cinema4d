# These tables hold the strings for automatic rig and face morph detection.

#   nameStudio             : (nameDisplay,                       ,type,[namesMain],                              [nameAttrNeeded],    [nameAttrForbidden],      [nameSideInclude], [nameSideExclude])
STUDIO_NAMES_TO_GUESS = {
    'hip'                  : (0,  'Hips'                         , 1,  [['hip'], ['pelvis']],                    [],                  [],                       [],                []                ),
    'spine'                : (1,  'Spine'                        , 1,  [['spine']],                              [],                  [],                       [],                []                ),
    'chest'                : (2,  'Chest'                        , 1,  [['chest'], ['spine', '4']],              [],                  [],                       [],                []                ),
    'neck'                 : (3,  'Neck'                         , 1,  [['neck']],                               [],                  [],                       [],                []                ),
    'head'                 : (4,  'Head'                         , 1,  [['head']],                               [],                  ['tip', 'end', 'vertex'], [],                []                ),
    'leftShoulder'         : (5,  'Left Shoulder'                , 1,  [['shoulder'], ['collar']],               [],                  [],                       ['left'],          ['right', '___R'] ),
    'leftUpperArm'         : (6,  'Left Upper Arm'               , 1,  [['arm']],                                [],                  ['low', 'fore'],          ['left'],          ['right', '___R'] ),
    'leftLowerArm'         : (7,  'Left Forearm'                 , 1,  [['arm', 'low'], ['forearm']],            [],                  ['up'],                   ['left'],          ['right', '___R'] ),
    'leftHand'             : (8,  'Left Hand'                    , 1,  [['hand']],                               [],                  [],                       ['left'],          ['right', '___R'] ),
    'rightShoulder'        : (9,  'Right Shoulder'               , 1,  [['shoulder'], ['collar']],               [],                  [],                       ['right', '___R'], ['left']          ),
    'rightUpperArm'        : (10, 'Right Upper Arm'              , 1,  [['arm']],                                [],                  ['low', 'fore'],          ['right', '___R'], ['left']          ),
    'rightLowerArm'        : (11, 'Right ForeArm'                , 1,  [['arm', 'low'], ['forearm']],            [],                  ['up'],                   ['right', '___R'], ['left']          ),
    'rightHand'            : (12, 'Right Hand'                   , 1,  [['hand']],                               [],                  [],                       ['right', '___R'], ['left']          ),
    'leftUpLeg'            : (13, 'Left Thigh'                   , 1,  [['leg', 'up'], ['thigh']],               [],                  ['low'],                  ['left'],          ['right', '___R'] ),
    'leftLeg'              : (14, 'Left Shin'                    , 1,  [['shin'], ['leg']],                      [],                  ['up'],                   ['left'],          ['right', '___R'] ),
    'leftFoot'             : (15, 'Left Foot'                    , 1,  [['foot']],                               [],                  [],                       ['left'],          ['right', '___R'] ),
    'leftToe'              : (16, 'Left Toe'                     , 1,  [['toe']],                                [],                  ['end', 'tip'],           ['left'],          ['right', '___R'] ),
    'leftToeEnd'           : (17, 'Left Toe Tip'                 , 1,  [['toe', 'end'], ['toe', 'tip']],         [],                  [],                       ['left'],          ['right', '___R'] ),
    'rightUpLeg'           : (18, 'Right Thigh'                  , 1,  [['leg', 'up'], ['thigh']],               [],                  ['low'],                  ['right', '___R'], ['left']          ),
    'rightLeg'             : (19, 'Right Shin'                   , 1,  [['shin'], ['leg']],                      [],                  ['up'],                   ['right', '___R'], ['left']          ),
    'rightFoot'            : (20, 'Right Foot'                   , 1,  [['foot']],                               [],                  [],                       ['right', '___R'], ['left']          ),
    'rightToe'             : (21, 'Right Toe'                    , 1,  [['toe']],                                [],                  ['end', 'tip'],           ['right', '___R'], ['left']          ),
    'rightToeEnd'          : (22, 'Right Toe Tip'                , 1,  [['toe', 'end'], ['toe', 'tip']],         [],                  [],                       ['right', '___R'], ['left']          ),
    'leftThumbProximal'    : (23, 'Left Thumb Metacarpal'        , 6,  [['thumb'], ['finger', '1']],             ['metacarpal', '0'], [],                       ['left'],          ['right', '___R'] ),
    'leftThumbMedial'      : (24, 'Left Thumb Proximal'          , 6,  [['thumb'], ['finger', '1']],             ['proximal', '1'],   [],                       ['left'],          ['right', '___R'] ),
    'leftThumbDistal'      : (25, 'Left Thumb Distal'            , 6,  [['thumb'], ['finger', '1']],             ['distal', '2'],     [],                       ['left'],          ['right', '___R'] ),
    'leftThumbTip'         : (26, 'Left Thumb Tip'               , 6,  [['thumb'], ['finger', '1']],             ['tip', 'end', '3'], [],                       ['left'],          ['right', '___R'] ),
    'leftIndexProximal'    : (27, 'Left Index Finger Proximal'   , 6,  [['index'], ['finger', '2']],             ['proximal', '1'],   ['metacarpal'],           ['left'],          ['right', '___R'] ),
    'leftIndexMedial'      : (28, 'Left Index Finger Medial'     , 6,  [['index'], ['finger', '2']],             ['medial', '2'],     ['metacarpal'],           ['left'],          ['right', '___R'] ),
    'leftIndexDistal'      : (29, 'Left Index Finger Distal'     , 6,  [['index'], ['finger', '2']],             ['distal', '3'],     ['metacarpal'],           ['left'],          ['right', '___R'] ),
    'leftIndexTip'         : (30, 'Left Index Finger Tip'        , 6,  [['index'], ['finger', '2']],             ['tip', 'end', '4'], ['metacarpal'],           ['left'],          ['right', '___R'] ),
    'leftMiddleProximal'   : (31, 'Left Middle Finger Proximal'  , 6,  [['middle'], ['finger', '3']],            ['proximal', '1'],   ['metacarpal'],           ['left'],          ['right', '___R'] ),
    'leftMiddleMedial'     : (32, 'Left Middle Finger Medial'    , 6,  [['middle'], ['finger', '3']],            ['medial', '2'],     ['metacarpal'],           ['left'],          ['right', '___R'] ),
    'leftMiddleDistal'     : (33, 'Left Middle Finger Distal'    , 6,  [['middle'], ['finger', '3']],            ['distal', '3'],     ['metacarpal'],           ['left'],          ['right', '___R'] ),
    'leftMiddleTip'        : (34, 'Left Middle Finger Tip'       , 6,  [['middle'], ['finger', '3']],            ['tip', 'end', '4'], ['metacarpal'],           ['left'],          ['right', '___R'] ),
    'leftRingProximal'     : (35, 'Left Ring Finger Proximal'    , 6,  [['ring'], ['finger', '4']],              ['proximal', '1'],   ['metacarpal'],           ['left'],          ['right', '___R'] ),
    'leftRingMedial'       : (36, 'Left Ring Finger Medial'      , 6,  [['ring'], ['finger', '4']],              ['medial', '2'],     ['metacarpal'],           ['left'],          ['right', '___R'] ),
    'leftRingDistal'       : (37, 'Left Ring Finger Distal'      , 6,  [['ring'], ['finger', '4']],              ['distal', '3'],     ['metacarpal'],           ['left'],          ['right', '___R'] ),
    'leftRingTip'          : (38, 'Left Ring Finger Tip'         , 6,  [['ring'], ['finger', '4']],              ['tip', 'end', '4'], ['metacarpal'],           ['left'],          ['right', '___R'] ),
    'leftLittleProximal'   : (39, 'Left Little Finger Proximal'  , 6,  [['little'], ['finger', '5'], ['pink']],  ['proximal', '1'],   ['metacarpal'],           ['left'],          ['right', '___R'] ),
    'leftLittleMedial'     : (40, 'Left Little Finger Medial'    , 6,  [['little'], ['finger', '5'], ['pink']],  ['medial', '2'],     ['metacarpal'],           ['left'],          ['right', '___R'] ),
    'leftLittleDistal'     : (41, 'Left Little Finger Distal'    , 6,  [['little'], ['finger', '5'], ['pink']],  ['distal', '3'],     ['metacarpal'],           ['left'],          ['right', '___R'] ),
    'leftLittleTip'        : (42, 'Left Little Finger Tip'       , 6,  [['little'], ['finger', '5'], ['pink']],  ['tip', 'end', '4'], ['metacarpal'],           ['left'],          ['right', '___R'] ),
    'rightThumbProximal'   : (43, 'Right Thumb Metacarpal'       , 10, [['thumb'], ['finger', '1']],             ['metacarpal', '0'], [],                       ['right', '___R'], ['left']          ),
    'rightThumbMedial'     : (44, 'Right Thumb Proximal'         , 10, [['thumb'], ['finger', '1']],             ['proximal', '1'],   ['metacarpal'],           ['right', '___R'], ['left']          ),
    'rightThumbDistal'     : (45, 'Right Thumb Distal'           , 10, [['thumb'], ['finger', '1']],             ['distal', '2'],     ['metacarpal'],           ['right', '___R'], ['left']          ),
    'rightThumbTip'        : (46, 'Right Thumb Tip'              , 10, [['thumb'], ['finger', '1']],             ['tip', 'end', '3'], ['metacarpal'],           ['right', '___R'], ['left']          ),
    'rightIndexProximal'   : (47, 'Right Index Finger Proximal'  , 10, [['index'], ['finger', '2']],             ['proximal', '1'],   ['metacarpal'],           ['right', '___R'], ['left']          ),
    'rightIndexMedial'     : (48, 'Right Index Finger Medial'    , 10, [['index'], ['finger', '2']],             ['medial', '2'],     ['metacarpal'],           ['right', '___R'], ['left']          ),
    'rightIndexDistal'     : (49, 'Right Index Finger Distal'    , 10, [['index'], ['finger', '2']],             ['distal', '3'],     ['metacarpal'],           ['right', '___R'], ['left']          ),
    'rightIndexTip'        : (50, 'Right Index Finger Tip'       , 10, [['index'], ['finger', '2']],             ['tip', 'end', '4'], ['metacarpal'],           ['right', '___R'], ['left']          ),
    'rightMiddleProximal'  : (51, 'Right Middle Finger Proximal' , 10, [['middle'], ['finger', '3']],            ['proximal', '1'],   ['metacarpal'],           ['right', '___R'], ['left']          ),
    'rightMiddleMedial'    : (52, 'Right Middle Finger Medial'   , 10, [['middle'], ['finger', '3']],            ['medial', '2'],     ['metacarpal'],           ['right', '___R'], ['left']          ),
    'rightMiddleDistal'    : (53, 'Right Middle Finger Distal'   , 10, [['middle'], ['finger', '3']],            ['distal', '3'],     ['metacarpal'],           ['right', '___R'], ['left']          ),
    'rightMiddleTip'       : (54, 'Right Middle Finger Tip'      , 10, [['middle'], ['finger', '3']],            ['tip', 'end', '4'], ['metacarpal'],           ['right', '___R'], ['left']          ),
    'rightRingProximal'    : (55, 'Right Ring Finger Proximal'   , 10, [['ring'], ['finger', '4']],              ['proximal', '1'],   ['metacarpal'],           ['right', '___R'], ['left']          ),
    'rightRingMedial'      : (56, 'Right Ring Finger Medial'     , 10, [['ring'], ['finger', '4']],              ['medial', '2'],     ['metacarpal'],           ['right', '___R'], ['left']          ),
    'rightRingDistal'      : (57, 'Right Ring Finger Distal'     , 10, [['ring'], ['finger', '4']],              ['distal', '3'],     ['metacarpal'],           ['right', '___R'], ['left']          ),
    'rightRingTip'         : (58, 'Right Ring Finger Tip'        , 10, [['ring'], ['finger', '4']],              ['tip', 'end', '4'], ['metacarpal'],           ['right', '___R'], ['left']          ),
    'rightLittleProximal'  : (59, 'Right Little Finger Proximal' , 10, [['little'], ['finger', '5'], ['pink']],  ['proximal', '1'],   ['metacarpal'],           ['right', '___R'], ['left']          ),
    'rightLittleMedial'    : (60, 'Right Little Finger Medial'   , 10, [['little'], ['finger', '5'], ['pink']],  ['medial', '2'],     ['metacarpal'],           ['right', '___R'], ['left']          ),
    'rightLittleDistal'    : (61, 'Right Little Finger Distal'   , 10, [['little'], ['finger', '5'], ['pink']],  ['distal', '3'],     ['metacarpal'],           ['right', '___R'], ['left']          ),
    'rightLittleTip'       : (62, 'Right Little Finger Tip'      , 10, [['little'], ['finger', '5'], ['pink']],  ['tip', 'end', '4'], ['metacarpal'],           ['right', '___R'], ['left']          ),
}

#   nameStudio               idx, nameDisplay,                 [namesMain],                      [namesExclude],       [nameSideInclude], [nameSideExclude])
FACE_POSE_NAMES = {
    'eyeBlinkLeft'         : (1, 'Eye Blink Left',             [['eye', 'blink']],               [],                   ['left'],          ['right'] ),
    'eyeLookDownLeft'      : (2, 'Eye Look Down Left',         [['eye', 'look', 'down']],        [],                   ['left'],          ['right'] ),
    'eyeLookInLeft'        : (3, 'Eye Look In Left',           [['eye', 'look', 'in']],          [],                   ['left'],          ['right'] ),
    'eyeLookOutLeft'       : (4, 'Eye Look Out Left',          [['eye', 'look', 'out']],         [],                   ['left'],          ['right'] ),
    'eyeLookUpLeft'        : (5, 'Eye Look Up Left',           [['eye', 'look', 'up']],          [],                   ['left'],          ['right'] ),
    'eyeSquintLeft'        : (6, 'Eye Squint Left',            [['eye', 'squint']],              [],                   ['left'],          ['right'] ),
    'eyeWideLeft'          : (7, 'Eye Wide Left',              [['eye', 'wide']],                [],                   ['left'],          ['right'] ),
    'eyeBlinkRight'        : (8, 'Eye Blink Right',            [['eye', 'blink']],               [],                   ['right'],         ['left']  ),
    'eyeLookDownRight'     : (9, 'Eye Look Down Right',        [['eye', 'look', 'down']],        [],                   ['right'],         ['left']  ),
    'eyeLookInRight'       : (10, 'Eye Look In Right',         [['eye', 'look', 'in']],          [],                   ['right'],         ['left']  ),
    'eyeLookOutRight'      : (11, 'Eye Look Out Right',        [['eye', 'look', 'out']],         [],                   ['right'],         ['left']  ),
    'eyeLookUpRight'       : (12, 'Eye Look Up Right',         [['eye', 'look', 'up']],          [],                   ['right'],         ['left']  ),
    'eyeSquintRight'       : (13, 'Eye Squint Right',          [['eye', 'squint']],              [],                   ['right'],         ['left']  ),
    'eyeWideRight'         : (14, 'Eye Wide Right',            [['eye', 'wide']],                [],                   ['right'],         ['left']  ),
    'jawForward'           : (15, 'Jaw Forward',               [['jaw', 'forward']],             [],                   [],                []        ),
    'jawLeft'              : (16, 'Jaw Left',                  [['jaw']],                        ['forward', 'open'],  ['left'],          ['right'] ),
    'jawRight'             : (17, 'Jaw Right',                 [['jaw']],                        ['forward', 'open'],  ['right'],         ['left']  ),
    'jawOpen'              : (18, 'Jaw Open',                  [['jaw', 'open']],                [],                   [],                []        ),
    'mouthClose'           : (19, 'Mouth Close',               [['mouth', 'close']],             [],                   [],                []        ),
    'mouthFunnel'          : (20, 'Mouth Funnel',              [['mouth', 'funnel']],            [],                   [],                []        ),
    'mouthPucker'          : (21, 'Mouth Pucker',              [['mouth', 'pucker']],            [],                   [],                []        ),
    'mouthLeft'            : (22, 'Mouth Left',                [['mouth']],                      ['close', 'funnel', 'pucker', 'smile', 'frown', 'dimple', 'stretch', 'roll', 'shrug', 'press', 'lower', 'upper'], ['left'], ['right'] ),
    'mouthRight'           : (23, 'Mouth Right',               [['mouth']],                      ['close', 'funnel', 'pucker', 'smile', 'frown', 'dimple', 'stretch', 'roll', 'shrug', 'press', 'lower', 'upper'], ['right'], ['left'] ),
    'mouthSmileLeft'       : (24, 'Mouth Smile Left',          [['mouth', 'smile']],             [],                   ['left'],          ['right'] ),
    'mouthSmileRight'      : (25, 'Mouth Smile Right',         [['mouth', 'smile']],             [],                   ['right'],         ['left']  ),
    'mouthFrownLeft'       : (26, 'Mouth Frown Left',          [['mouth', 'frown']],             [],                   ['left'],          ['right'] ),
    'mouthFrownRight'      : (27, 'Mouth Frown Right',         [['mouth', 'frown']],             [],                   ['right'],         ['left']  ),
    'mouthDimpleLeft'      : (28, 'Mouth Dimple Left',         [['mouth', 'dimple']],            [],                   ['left'],          ['right'] ),
    'mouthDimpleRight'     : (29, 'Mouth Dimple Right',        [['mouth', 'dimple']],            [],                   ['right'],         ['left']  ),
    'mouthStretchLeft'     : (30, 'Mouth Stretch Left',        [['mouth', 'stretch']],           [],                   ['left'],          ['right'] ),
    'mouthStretchRight'    : (31, 'Mouth Stretch Right',       [['mouth', 'stretch']],           [],                   ['right'],         ['left']  ),
    'mouthRollLower'       : (32, 'Mouth Roll Lower',          [['mouth', 'roll']],              [],                   ['lower'],         ['upper'] ),
    'mouthRollUpper'       : (33, 'Mouth Roll Upper',          [['mouth', 'roll']],              [],                   ['upper'],         ['lower'] ),
    'mouthShrugLower'      : (34, 'Mouth Shrug Lower',         [['mouth', 'shrug']],             [],                   ['lower'],         ['upper'] ),
    'mouthShrugUpper'      : (35, 'Mouth Shrug Upper',         [['mouth', 'shrug']],             [],                   ['upper'],         ['lower'] ),
    'mouthPressLeft'       : (36, 'Mouth Press Left',          [['mouth', 'press']],             [],                   ['left'],          ['right'] ),
    'mouthPressRight'      : (37, 'Mouth Press Right',         [['mouth', 'press']],             [],                   ['right'],         ['left']  ),
    'mouthLowerDownLeft'   : (38, 'Mouth Lower Down Left',     [['mouth', 'lower', 'down']],     [],                   ['left'],          ['right'] ),
    'mouthLowerDownRight'  : (39, 'Mouth Lower Down Right',    [['mouth', 'lower', 'down']],     [],                   ['right'],         ['left']  ),
    'mouthUpperUpLeft'     : (40, 'Mouth Upper Up Left',       [['mouth', 'upper', 'up']],       [],                   ['left'],          ['right'] ),
    'mouthUpperUpRight'    : (41, 'Mouth Upper Up Right',      [['mouth', 'upper', 'up']],       [],                   ['right'],         ['left']  ),
    'browDownLeft'         : (42, 'Brow Down Left',            [['brow', 'down']],               [],                   ['left'],          ['right'] ),
    'browDownRight'        : (43, 'Brow Down Right',           [['brow', 'down']],               [],                   ['right'],         ['left']  ),
    'browInnerUp'          : (44, 'Brow Inner Up',             [['brow', 'inner', 'up']],        [],                   [''],              ['']      ),
    'browOuterUpLeft'      : (45, 'Brow Outer Up Left',        [['brow', 'outer', 'up']],        [],                   ['left'],          ['right'] ),
    'browOuterUpRight'     : (46, 'Brow Outer Up Right',       [['brow', 'outer', 'up']],        [],                   ['right'],         ['left']  ),
    'cheekPuff'            : (47, 'Cheek Puff',                [['cheek', 'puff']],              [],                   [''],              ['']      ),
    'cheekSquintLeft'      : (48, 'Cheek Squint Left',         [['cheek', 'squint']],            [],                   ['left'],          ['right'] ),
    'cheekSquintRight'     : (49, 'Cheek Squint Right',        [['cheek', 'squint']],            [],                   ['right'],         ['left']  ),
    'noseSneerLeft'        : (50, 'Nose Sneer Left',           [['nose', 'sneer']],              [],                   ['left'],          ['right'] ),
    'noseSneerRight'       : (51, 'Nose Sneer Right',          [['nose', 'sneer']],              [],                   ['right'],         ['left']  ),
    'tongueOut'            : (52, 'Tongue Out',                [['tongue', 'out']],              [],                   [],                []        ),
}
