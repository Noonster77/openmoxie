"""Safe, curated performance controls for Puppet Mode."""

PUPPET_MOODS = [
    ("neutral", "Natural", "Balanced expression"),
    ("happy", "Happy", "Bright and cheerful"),
    ("positive", "Encouraging", "Warm and supportive"),
    ("curious", "Curious", "Interested and inquisitive"),
    ("surprise", "Surprised", "Excited and amazed"),
    ("shy", "Shy", "Gentle and reserved"),
    ("concerned", "Concerned", "Caring and serious"),
    ("confused", "Confused", "Puzzled and thoughtful"),
    ("sad", "Sad", "Soft and downcast"),
    ("angry", "Angry", "Strong and frustrated"),
    ("afraid", "Afraid", "Worried and cautious"),
    ("embarrassed", "Embarrassed", "Awkward and bashful"),
]

PUPPET_MOOD_NAMES = {value for value, _label, _description in PUPPET_MOODS}

PUPPET_VOCAL_STYLES = [
    ("natural", "Natural", "Normal conversational delivery"),
    ("motivational", "Motivational", "Encouraging emphasis"),
    ("excited", "Excited", "More animated delivery"),
    ("question", "Inquisitive", "Question-like delivery"),
]
PUPPET_VOCAL_GENRES = {
    key: "" if key == "natural" else key
    for key, _label, _description in PUPPET_VOCAL_STYLES
}

# All cues below are marked Default=True in AssetBundleMasterManifest.csv.
# Groups are also used as the pages on the Puppet Mode sound board.
PUPPET_SOUND_GROUPS = [
    ("celebrate", "Celebrate", [
        ("success", "Success", "sfx_successful_command_1"),
        ("tada", "Ta-da!", "sc_places_tada_01"),
        ("applause", "Applause", "audience_clapping_hall_01_crop1_stereo"),
        ("cheer", "Stadium cheer", "sc_places_stadiumcheer_01"),
        ("kids_cheer", "Kids cheering", "sfxgr_childrencheering01"),
        ("drumroll", "Drumroll", "191718__adriann__drumroll"),
        ("party", "Party shaker", "sfxpm_cheerypartyshaker_01"),
    ]),
    ("magic", "Magic & UI", [
        ("chime", "Chime", "sfxgen_door_bellchime_01"),
        ("sparkles", "Sparkles", "SC_sparkles"),
        ("sparkle_rain", "Sparkle rain", "sfx_sparklerain01"),
        ("pop", "Pop", "sfxgbl_pop01"),
        ("boing", "Boing", "sfxb_cartoonboingretrojump01"),
        ("whoosh", "Whoosh", "sfxcax_whooshswishsmallharsh01"),
        ("surprise", "Surprise", "sfxgbl_emotesurprise02"),
        ("incoming", "Attention", "sfxmm_incoming02"),
    ]),
    ("reactions", "Reactions", [
        ("giggle", "Giggle", "sc_laugh_giggle_01"),
        ("laugh", "Laugh", "laugh_small_twohit_2"),
        ("chuckle", "Chuckle", "sc_laugh_chuckle_05"),
        ("mischief", "Mischievous laugh", "sc_laugh_mischief_01"),
        ("nervous", "Nervous laugh", "sc_laugh_nervous_01"),
        ("whistle_up", "Slide whistle up", "sc_places_slidewhistleup_03"),
        ("whistle_down", "Slide whistle down", "sc_places_slidewhistledown_01"),
    ]),
    ("animals", "Animals", [
        ("cat", "Cat meow", "sfxr_catmeow01"),
        ("dog", "Dog bark", "sfxr_dogbark01"),
        ("dragon", "Dragon roar", "dragon_roar"),
    ]),
    ("calm", "Calm", [
        ("wind_chime", "Wind chime", "sfxgmdwindchime_02"),
        ("singing_bowl", "Singing bowl", "sfxyo_singingbowlchime_01"),
    ]),
]
PUPPET_SOUND_CUES = [("none", "No sound", "")] + [
    cue for _key, _label, cues in PUPPET_SOUND_GROUPS for cue in cues
]
PUPPET_SOUND_ASSETS = {key: asset for key, _label, asset in PUPPET_SOUND_CUES}

# These event names are already used by OpenMoxie's automatic gesture engine.
PUPPET_GESTURES = [
    ("auto", "Automatic", "Let Moxie choose conversational gestures"),
    ("celebrate", "Celebrate", "Gesture_Celebrate"),
    ("laugh", "Laugh", "Gesture_Laugh"),
    ("question", "Question", "Gesture_Question"),
    ("me", "Me", "AUTO_GESTURE_ME"),
    ("you", "You", "AUTO_GESTURE_YOU"),
    ("big", "Big", "Gesture_Large"),
    ("small", "Small", "Gesture_Small"),
    ("up", "Up", "Gesture_Higher"),
]
PUPPET_GESTURE_EVENTS = {key: event for key, _label, event in PUPPET_GESTURES}

# Curated, single-shot actions. Multi-step hugs, sleep, wake, and system trees are
# intentionally excluded because they require state or a follow-up action.
PUPPET_ACTION_GROUPS = [
    ("reactions", "Reactions", [
        ("celebrate", "Celebrate", "Cheer with a success sound", "gesture", "Gesture_Celebrate", "success"),
        ("laugh", "Laugh", "Laugh and giggle", "gesture", "Gesture_Laugh", "giggle"),
        ("startled", "Startled", "React with surprise", "behavior", "bht_startled", "surprise"),
        ("confused", "Confused", "Look puzzled", "behavior", "bht_huh_confused", "none"),
        ("shake_off", "Shake it off", "Reset with a shake", "behavior", "bht_shake_it_off", "none"),
        ("relief", "Sigh of relief", "A relieved reaction", "behavior", "bht_sigh_relief", "none"),
        ("yes", "Nod yes", "Nod in agreement", "gesture", "Gesture_Nod", "none"),
        ("no", "Say no", "Gesture disagreement", "gesture", "Gesture_Negation", "none"),
    ]),
    ("gestures", "Gestures", [
        ("wave", "Wave", "Wave both arms", "behavior", "bht_back_and_forth_arm_wave", "none"),
        ("greet", "Greet", "Friendly greeting gesture", "behavior", "bht_gesture_greet", "none"),
        ("bow", "Take a bow", "Perform a short bow", "behavior", "bht_bow", "none"),
        ("question", "Ask", "Make a questioning gesture", "gesture", "Gesture_Question", "none"),
        ("think", "Think", "Make a thinking gesture", "gesture", "Gesture_Think", "none"),
        ("point_left", "Point left", "Point toward Moxie's left", "gesture", "Gesture_Point_Left", "none"),
        ("point_right", "Point right", "Point toward Moxie's right", "gesture", "Gesture_Point_Right", "none"),
        ("self", "Me", "Gesture toward Moxie", "gesture", "Gesture_Self", "none"),
        ("we", "We", "Gesture to include everyone", "gesture", "Gesture_We", "none"),
        ("big", "Show big", "Gesture something large", "gesture", "Gesture_Large", "none"),
        ("small", "Show small", "Gesture something small", "gesture", "Gesture_Small", "none"),
        ("higher", "Higher", "Gesture upward", "gesture", "Gesture_Higher", "none"),
        ("lower", "Lower", "Gesture downward", "gesture", "Gesture_Lower", "none"),
    ]),
    ("poses", "Poses", [
        ("curious", "Curious", "Strike a curious pose", "behavior", "bht_photo_pose_curious", "none"),
        ("silly", "Silly", "Strike a silly pose", "behavior", "bht_photo_pose_silly", "none"),
        ("thoughtful", "Thoughtful", "Strike a thoughtful pose", "behavior", "bht_photo_pose_thoughtful", "none"),
        ("cool", "Cool", "Strike a cool pose", "behavior", "bht_photo_pose_cool", "none"),
        ("cute", "Cute", "Strike a cute pose", "behavior", "bht_photo_pose_cute", "none"),
        ("sly", "Sly", "Strike a sly pose", "behavior", "bht_photo_pose_sly", "none"),
        ("smile", "Smile", "Pose with a smile", "behavior", "bht_photo_pose_smile", "none"),
        ("surprised", "Surprised", "Strike a surprised pose", "behavior", "bht_photo_pose_surprised", "none"),
        ("winky", "Wink", "Strike a winking pose", "behavior", "bht_photo_pose_winky", "none"),
    ]),
    ("dances", "Dances", [
        ("dance", "Dance 1", "Short celebration dance", "behavior", "bht_celebration_dance_01", "none"),
        ("dance_two", "Dance 2", "Second celebration dance", "behavior", "bht_celebration_dance_02", "none"),
        ("dance_three", "Dance 3", "Third celebration dance", "behavior", "bht_celebration_dance_03", "none"),
        ("dance_four", "Dance 4", "Fourth celebration dance", "behavior", "bht_celebration_dance_04", "none"),
    ]),
    ("breathing", "Breathing", [
        ("bear_breath", "Bear breath", "Bear breathing movement", "behavior", "bht_bear_breath", "none"),
        ("bee_breath", "Bee breath", "Bee breathing movement", "behavior", "bht_bee_breath", "none"),
        ("bunny_breath", "Bunny breath", "Bunny breathing movement", "behavior", "bht_bunny_breath", "none"),
        ("cat_breath", "Cat breath", "Cat breathing movement", "behavior", "bht_cat_breath", "none"),
        ("dragon_breath", "Dragon breath", "Dragon breathing movement", "behavior", "bht_dragon_breath", "none"),
        ("lion_breath", "Lion breath", "Lion breathing movement", "behavior", "bht_lion_breath", "none"),
        ("snake_breath", "Snake breath", "Snake breathing movement", "behavior", "bht_snake_breath", "none"),
        ("whale_breath", "Whale breath", "Whale breathing movement", "behavior", "bht_whale_breath", "none"),
        ("wolf_breath", "Wolf breath", "Wolf breathing movement", "behavior", "bht_wolf_breath", "none"),
    ]),
]
PUPPET_ACTIONS = [
    action for _key, _label, actions in PUPPET_ACTION_GROUPS for action in actions
]
PUPPET_ACTION_MAP = {
    key: {"kind": kind, "target": target, "sound": sound}
    for key, _label, _description, kind, target, sound in PUPPET_ACTIONS
}

# Appearance presets intentionally use only the safer Eyes and Face_Colors layers.
PUPPET_FACE_PRESETS = [
    ("default", "Classic", "Original eyes and face color", []),
    ("ocean", "Ocean", "Light-blue eyes and a teal face", [
        "MX_010_Eyes_LightBlue", "MX_020_Face_Colors_Teal",
    ]),
    ("sunshine", "Sunshine", "Gold eyes and a yellow face", [
        "MX_010_Eyes_Gold", "MX_020_Face_Colors_Yellow",
    ]),
    ("forest", "Forest", "Hazel eyes and a green face", [
        "MX_010_Eyes_Hazel", "MX_020_Face_Colors_Green",
    ]),
    ("berry", "Berry", "Purple eyes and a pink face", [
        "MX_010_Eyes_Purple", "MX_020_Face_Colors_Pink",
    ]),
    ("moon", "Moon", "Grey eyes and a purple face", [
        "MX_010_Eyes_Grey", "MX_020_Face_Colors_Purple",
    ]),
]
PUPPET_FACE_OPTIONS = {key: assets for key, _label, _description, assets in PUPPET_FACE_PRESETS}
PUPPET_SAFE_FACE_PREFIXES = ("MX_010_Eyes_", "MX_020_Face_Colors_")


def play_audio_markup(asset):
    if not asset:
        return ""
    return (
        '<mark name="cmd:playaudio,data:{+SoundToPlay+:+%s+,+LoopSound+:false,'
        '+playInBackground+:false,+channel+:1,+ReplaceCurrentSound+:false,'
        '+PlayImmediate+:true,+ForceQueue+:false,+Volume+:1.0,+FadeInTime+:0.0,'
        '+FadeOutTime+:1.0,+AudioTimelineField+:+none+}"/>'
    ) % asset


def gesture_markup(event_name):
    if not event_name:
        return ""
    return (
        '<mark name="cmd:behaviour-tree,data:{+transition+:0.5,+duration+:1.0,'
        '+repeat+:1,+layerBlendInTime+:0.5,+layerBlendOutTime+:0.5,+blocking+:false,'
        '+action+:4,+variableName+:++,+variableValue+:++,+eventName+:+%s+,'
        '+lifetime+:0,+category+:+None+,+behaviour+:++,+Track+:++}"/>'
    ) % event_name


def behavior_tree_markup(behavior_name):
    return (
        '<mark name="cmd:behaviour-tree,data:{+transition+:0.5,+duration+:1.0,'
        '+repeat+:1,+layerBlendInTime+:0.5,+layerBlendOutTime+:0.5,+blocking+:false,'
        '+action+:0,+variableName+:++,+variableValue+:++,+eventName+:+Gesture_None+,'
        '+lifetime+:0,+category+:+None+,+behaviour+:+%s+,+Track+:++}"/>'
    ) % behavior_name


def enhance_puppet_markup(markup, sound="none", gesture="auto", vocal_style="natural"):
    """Add only curated commands to otherwise automatically generated markup."""
    sound_asset = PUPPET_SOUND_ASSETS.get(sound, "")
    gesture_event = PUPPET_GESTURE_EVENTS.get(gesture, "")
    genre = PUPPET_VOCAL_GENRES.get(vocal_style, "")
    spoken_markup = markup or ""
    if genre and spoken_markup:
        spoken_markup = f'<usel genre="{genre}" variant="0">{spoken_markup}</usel>'
    return f"{play_audio_markup(sound_asset)}{gesture_markup(gesture_event)}{spoken_markup}"


def puppet_action_markup(action):
    spec = PUPPET_ACTION_MAP[action]
    movement = (
        gesture_markup(spec["target"])
        if spec["kind"] == "gesture"
        else behavior_tree_markup(spec["target"])
    )
    sound = play_audio_markup(PUPPET_SOUND_ASSETS.get(spec["sound"], ""))
    return f'{sound}{movement}<break time="1s"/>'


def apply_face_preset(existing_options, preset):
    """Replace the safe eye/color layers while preserving all other custom layers."""
    retained = [
        option for option in (existing_options or [])
        if not option.startswith(PUPPET_SAFE_FACE_PREFIXES)
    ]
    return retained + list(PUPPET_FACE_OPTIONS[preset])
