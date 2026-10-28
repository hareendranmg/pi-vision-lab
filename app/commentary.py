"""Decides what the presenter says, from what the vision pipeline sees.

Offline and rule-based: each event type has a bank of lines, a cooldown and a
priority, so she reacts to new things without chattering. Lines are returned
as (text, gesture) where gesture names a presenter clip.
"""
import random
import time

INTRO = {
    "home": ["Hi, I'm Rajaram, your AI guide! Raise your hand and pinch to pick a demo.",
             "Welcome to Pi Vision Lab! Everything here runs on this little Raspberry Pi. Pinch a tile to start.",
             "Hello! Try the air cursor: point with your hand, pinch to click."],
    "objects": ["Show me something! I know 80 kinds of everyday objects.",
                "Object Finder is on. Hold up a cup, a phone, a bottle... anything!"],
    "face": ["Let's play with your face! Pick an effect at the bottom.",
             "Face Magic! I track 478 points on your face, live."],
    "color": ["Hold something colourful inside the circle and I'll name the colour.",
              "Colour Finder ready. Bring me your brightest thing!"],
}

HELLO = ["Oh hi there! Pinch to click, make a fist to go home.",
         "Hello! I see your hand. Point at something and pinch.",
         "Welcome! Want to try Face Magic? It's my favourite."]

EFFECT = {
    "masquerade": ["Ooh, mysterious! Very Venice carnival.", "A masked guest! Who could you be?"],
    "crown": ["Your Majesty! That crown really suits you.", "All hail the ruler of the demo booth!"],
    "shades": ["Too cool for school.", "Those shades are seriously stylish."],
    "glam": ["Red carpet ready! Lipstick, blush and liner, all virtual.", "Glam mode: no brushes required."],
    "iceeyes": ["Those icy eyes are mesmerising.", "Whoa, ice-blue eyes! I'm recolouring just your irises."],
    "mesh": ["This is what I really see: a mesh of 478 points following your face.",
             "Here's the AI's view. Every dot is a tracked point on your face."],
    "none": ["Back to the natural look. Looking good!"],
}

MOOD = {
    "happy": ["Love that smile!", "Now that's a happy face!", "Your smile just made my day."],
    "surprised": ["Whoa, did I surprise you?", "Eyebrows up! Something exciting?"],
    "winking": ["Did you just wink at me?", "Smooth wink!"],
    "sleepy": ["Hey, no sleeping in the demo!", "Eyes closed? I can still see you!"],
    "talking": ["I can't hear you, there's no microphone, but I can see you talking!"],
}

GESTURE = {
    "thumbs up": ["Thumbs up right back at you!", "Glad you like it!"],
    "peace": ["Peace! Nice sign.", "Peace and love from the Pi!"],
    "rock on": ["Rock on! \\m/"],
    "ok": ["OK sign spotted. Perfect!"],
}

OBJECT_FACTS = {
    "person": "Hello, human!",
    "cell phone": "Phones are tiny supercomputers. I'm running on a Pi though!",
    "cup": "Coffee or tea? I run on electricity myself.",
    "bottle": "Stay hydrated!",
    "laptop": "A laptop! That's a much bigger computer than me.",
    "book": "A book! Reading is still the best upgrade.",
    "keyboard": "Clickety-clack!",
    "mouse": "A mouse. Not the squeaky kind.",
    "remote": "A remote. Sadly I don't have a TV.",
    "scissors": "Careful with those scissors!",
    "backpack": "Ready for an adventure?",
    "chair": "Have a seat, the demo is better relaxed.",
    "clock": "Time flies when you're having AI fun.",
    "umbrella": "Expecting rain indoors?",
    "tie": "Looking sharp with that tie.",
    "handbag": "Nice bag!",
    "banana": "A banana! Great for scale.",
    "apple": "An apple a day keeps the bugs away.",
    "teddy bear": "Aww, a teddy bear!",
    "tv": "A screen! I live on one of those.",
}

COLOR_FLAVOUR = {
    "Red": "the colour of energy", "Crimson": "deep and dramatic", "Pink": "sweet and playful",
    "Hot Pink": "impossible to ignore", "Orange": "warm and cheerful", "Coral": "very tropical",
    "Gold": "fancy!", "Yellow": "like sunshine", "Lime": "zesty", "Green": "fresh and natural",
    "Teal": "calm and cool", "Turquoise": "like tropical water", "Cyan": "electric",
    "Sky Blue": "like a clear sky", "Blue": "classic and calm", "Navy": "smart and serious",
    "Purple": "royal", "Violet": "dreamy", "Lavender": "soft and soothing", "Magenta": "bold!",
    "Brown": "earthy", "Black": "sleek", "White": "clean and bright",
}


class Commentator:
    def __init__(self):
        self.last_said = float("-inf")
        self.cooldown = {}           # key -> next allowed time
        self.screen = None
        self.effect = None
        self.face_present = False
        self.face_since = 0.0
        self.mood = "neutral"
        self.mood_since = 0.0
        self.seen_labels = {}
        self.color_name, self.color_since, self.color_said = None, 0.0, None
        self.gesture, self.gesture_since = "", 0.0
        self.hand_seen = 0.0
        self.recent = []

    def _pick(self, lines):
        fresh = [l for l in lines if l not in self.recent] or lines
        line = random.choice(fresh)
        self.recent = (self.recent + [line])[-8:]
        return line

    def _ok(self, key, cooldown, gap=5.0, now=None):
        now = time.monotonic() if now is None else now
        return now - self.last_said > gap and now >= self.cooldown.get(key, 0.0)

    def _say(self, key, cooldown, text, gesture):
        now = time.monotonic()
        self.last_said = now
        self.cooldown[key] = now + cooldown
        return text, gesture

    def on_screen(self, screen):
        self.screen = screen
        self.seen_labels.clear()
        self.color_said = None
        if self._ok("screen:" + screen, 20, gap=0):
            return self._say("screen:" + screen, 20, self._pick(INTRO[screen]),
                             "wave" if screen == "home" else "present")
        return None

    def on_effect(self, effect):
        if effect == self.effect:
            return None
        self.effect = effect
        if self._ok("effect:" + effect, 6, gap=1.5):
            return self._say("effect:" + effect, 6, self._pick(EFFECT[effect]), "excited")
        return None

    def on_vision(self, v):
        """Called for every vision state; returns a line to say or None."""
        now = time.monotonic()
        mode = v.get("mode")

        hand = bool((v.get("hand") or {}).get("present"))
        if hand:
            if now - self.hand_seen > 15 and self._ok("hello", 30, gap=2):
                self.hand_seen = now
                return self._say("hello", 30, self._pick(HELLO), "wave")
            self.hand_seen = now

        g = (v.get("hand") or {}).get("gesture", "")
        if g != self.gesture:
            self.gesture, self.gesture_since = g, now
        elif g in GESTURE and now - self.gesture_since > 0.6 and self._ok("g:" + g, 25):
            return self._say("g:" + g, 25, self._pick(GESTURE[g]), "excited")

        if mode == "face":
            f = v.get("face") or {}
            present = bool(f.get("present"))
            if present != self.face_present:
                self.face_present, self.face_since = present, now
            elif present and f.get("emotion") != self.mood:
                self.mood, self.mood_since = f.get("emotion"), now
            elif present and self.mood in MOOD and now - self.mood_since > 0.8 and self._ok("m:" + self.mood, 20):
                return self._say("m:" + self.mood, 20, self._pick(MOOD[self.mood]), "talk")
            if not present and now - self.face_since > 4 and self._ok("lostface", 30):
                return self._say("lostface", 30, "Where did you go? Look at the camera!", "talk")

        if mode == "objects":
            counts = {}
            for o in v.get("objects", []):
                counts[o["label"]] = counts.get(o["label"], 0) + 1
            for label, n in counts.items():
                first = self.seen_labels.setdefault(label, now)
                if now - first > 1.0 and self._ok("o:" + label, 45):
                    fact = OBJECT_FACTS.get(label, "")
                    if label == "person" and n > 1:
                        text = f"I count {n} people. Welcome, everyone!"
                    else:
                        text = f"I spot {'a ' if n == 1 else str(n) + ' '}{label}{'' if n == 1 else 's'}! {fact}".strip()
                    return self._say("o:" + label, 45, text, "present")
            for label in list(self.seen_labels):
                if label not in counts:
                    del self.seen_labels[label]

        if mode == "color":
            c = v.get("color") or {}
            name = c.get("name")
            if name != self.color_name:
                self.color_name, self.color_since = name, now
            elif name and name != self.color_said and now - self.color_since > 1.2 and self._ok("c:" + name, 12, gap=3):
                self.color_said = name
                flavour = COLOR_FLAVOUR.get(name)
                text = f"That's {name}{', ' + flavour if flavour else ''}!"
                return self._say("c:" + name, 12, text, "present")
        return None
