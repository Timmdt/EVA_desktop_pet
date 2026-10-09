from __future__ import annotations

import json
import math
import random
import subprocess
import sys
import time
import asyncio
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread

from PySide6.QtCore import QPoint, QTimer, Qt, Signal
from PIL import Image
from PySide6.QtGui import QAction, QIcon, QImage, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QLabel,
    QMenu,
    QSystemTrayIcon,
    QWidget,
)
from sprite_animation import aligned_grid_frames, intermediate_frames
from motion_stabilization import stabilize_frames
from animation_clock import frame_index_at
#BUG: allways on top didnt work corretly

# TODO: ordered from easiest to most difficult:
# 3. Make EVA react to the time of day, such as being more active during the
#    day and sleeping at night.
# 4. Add food that EVA can eat.
# 5. Add clothing and accessories for EVA, such as hats, glasses, and outfits.
# 6. Make EVA react to user activity, such as being more active while the user
#    is active and sleeping while the user is inactive.
# 7. Add more animations for local weather conditions, such as rain, snow, and
#    sunshine.
# 8. Let EVA walk around the screen and interact with the user, such as
#    following the mouse cursor or responding to clicks.
# 9. Let EVA interact with other pets, such as playing together or fighting.
# 10. Let EVA learn new behaviors and tricks over time, such as fetching
#     objects or performing tricks.


# ============================================================
# Paths
# ============================================================

APP_DIR = Path(__file__).resolve().parent
ASSET_DIR = APP_DIR / "assets"

STATE_FILE = APP_DIR / "pet_state.json"
COMMAND_FILE = APP_DIR / "pet_command.json"


# ============================================================
# Animation settings
# ============================================================

FRAMES_PER_SHEET = 4
INTERMEDIATE_FRAMES = 3
# Use more movement samples only where a slowly animated character needs them.
# Eight original poses remain eight original poses: in-betweens do NOT accelerate the animation.
STATE_INTERMEDIATES = {
    "idle": 7,
    "happy": 5,
    "curious": 5,
    "sad": 5,
    "dancing": 7,
    "sleeping": 5,
    "nervously": 5,
    "hide": 7,
}
# Keep deliberate sideways moves in display/watching; stabilize small frame jitter elsewhere.
STABILIZE_STATES = {
    "idle", "happy", "curious", "sad", "dancing", "sleeping", "nervously", "hide",
}
# Original-pose cadence; in-betweens increase rendering FPS, not motion speed.
ANIMATION_SPEED = 0.65

# Only these original poses are short blinks, not sustained expressions.
BLINK_POSES = {"idle": {2, 6}, "hide": {1, 5}}
# Eye-only patches in the original 543 x 724 frames. Keep the mouth,
# visor highlight, ears and hands outside the patches.
EYE_REGIONS = {
    "idle": [
        ((192, 354, 296, 466), (357, 402, 444, 500)),
        ((187, 331, 286, 445), (347, 390, 439, 480)),
        ((189, 345, 291, 450), (348, 392, 442, 490)),
        ((189, 339, 288, 451), (348, 391, 443, 500)),
        ((189, 346, 305, 475), (357, 410, 454, 513)),
        ((183, 322, 302, 439), (354, 386, 455, 498)),
        ((181, 345, 303, 457), (356, 403, 455, 501)),
        ((206, 351, 313, 468), (365, 416, 464, 520)),
    ],
    "hide": [
        ((196, 428, 302, 526), (346, 450, 437, 541)),
        ((189, 430, 292, 518), (349, 454, 441, 539)),
        ((190, 425, 299, 529), (336, 432, 433, 531)),
        ((188, 485, 300, 560), (340, 496, 435, 560)),
        ((195, 468, 302, 559), (345, 475, 442, 560)),
        ((209, 473, 310, 557), (366, 490, 463, 560)),
        ((203, 468, 310, 561), (356, 475, 453, 561)),
        ((212, 535, 312, 595), (362, 540, 456, 595)),
    ],
}

# Sprite animation:
# Gesicht / Ohren / Ausdruck
STATE_FPS = {
    "idle": 5,
    "happy": 7,
    "curious": 5,
    "sad": 4,
    "display": 4,
}


DEFAULT_WIDTH = 190
MIN_WIDTH = 80
MAX_WIDTH = 450
MOTION_FPS = 60

# Platz, damit das Pet beim Schweben nicht abgeschnitten wird
BOB_MARGIN = 10

STATE_BOB = {
    "idle": {
        "amplitude": 3.0,
        "speed": 1.4,
    },

    "happy": {
        "amplitude": 4.0,
        "speed": 1.8,
    },

    "curious": {
        "amplitude": 1.5,
        "speed": 2.6,
    },

    "sad": {
        "amplitude": 1.8,
        "speed": 0.8,
    },

    "display": {
        "amplitude": 1.5,
        "speed": 0.9,
    },

    "dancing": {
        "amplitude": 5.0,
        "speed": 3.0,
    }, 

    "sleeping": {
        "amplitude": 1.0,
        "speed": 0.5,
    },

    "nervously": {
        "amplitude": 3.0,
        "speed": 2.5,
    },

    "hide": {
        "amplitude": 1.0,
        "speed": 0.5,
    },
}

# ============================================================
# Sprite sheets
# ============================================================

SPRITES = {
    "idle": [
        ASSET_DIR / "idle_1.png",
        ASSET_DIR / "idle_2.png",
    ],

    "happy": [
        ASSET_DIR / "happy_1.png",
        ASSET_DIR / "happy_2.png",
    ],

    "curious": [
        ASSET_DIR / "curious_1.png",
        ASSET_DIR / "curious_2.png",
    ],

    "sad": [
        ASSET_DIR / "sad_1.png",
        ASSET_DIR / "sad_2.png",
    ],

    "display": [
        ASSET_DIR / "display_1.png",
        ASSET_DIR / "display_2.png",
    ],

    "dancing": [
        ASSET_DIR / "dancing_v2.png",
    ],

    "sleeping": [
        ASSET_DIR / "sleeping_1.png",
        ASSET_DIR / "sleeping_2.png",
    ],

    "nervously": [
        ASSET_DIR / "nervously_1.png",
        ASSET_DIR / "nervously_2.png",
    ],

    "hide": [
        ASSET_DIR / "hide_1.png",
        ASSET_DIR / "hide_2.png",
    ],

    "watching": [
        ASSET_DIR / "watching_1.png",
        ASSET_DIR / "watching_2.png",
    ],
}


STATE_LABELS = {
    "idle": "Idle",
    "happy": "Fröhlich",
    "curious": "Neugierig",
    "sad": "Traurig",
    "display": "Zum Display schauen",
    "dancing": "Tanzen",
    "sleeping": "Schlafen",
    "nervously": "Nervös",
    "hide": "Verstecken",
    "watching": "Video schauen",
}


# ============================================================
# Settings
# ============================================================

@dataclass
class Settings:
    width: int = DEFAULT_WIDTH

    x: int | None = None
    y: int | None = None

    always_on_top: bool = True
    auto_mode: bool = True

    @classmethod
    def load(cls) -> "Settings":

        if not STATE_FILE.exists():
            return cls()

        try:
            data = json.loads(
                STATE_FILE.read_text(
                    encoding="utf-8"
                )
            )

            return cls(
                width=max(
                    MIN_WIDTH,
                    min(
                        MAX_WIDTH,
                        int(
                            data.get(
                                "width",
                                DEFAULT_WIDTH,
                            )
                        ),
                    ),
                ),

                x=data.get("x"),
                y=data.get("y"),

                always_on_top=bool(
                    data.get(
                        "always_on_top",
                        True,
                    )
                ),

                auto_mode=bool(
                    data.get(
                        "auto_mode",
                        True,
                    )
                ),
            )

        except Exception:
            return cls()

    def save(self) -> None:

        data = {
            "width": self.width,
            "x": self.x,
            "y": self.y,
            "always_on_top": self.always_on_top,
            "auto_mode": self.auto_mode,
        }

        STATE_FILE.write_text(
            json.dumps(
                data,
                indent=2,
            ),
            encoding="utf-8",
        )


# ============================================================
# EVA Desktop Pet
# ============================================================

MEDIA_SERVER_HOST = "127.0.0.1"
MEDIA_SERVER_PORT = 8765


class EvaMediaRequestHandler(BaseHTTPRequestHandler):

    def _send_status(self, status: int):
        self.send_response(status)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.end_headers()

    def do_OPTIONS(self):
        self._send_status(204)

    def do_POST(self):
        if self.path != "/media-state":
            self._send_status(404)
            return

        try:
            content_length = int(self.headers.get("Content-Length", "0"))

            if content_length < 1 or content_length > 1024:
                raise ValueError("Ungültige Nachrichtengröße")

            payload = json.loads(
                self.rfile.read(content_length).decode("utf-8")
            )

            playing = payload.get("video_playing")

            if not isinstance(playing, bool):
                raise ValueError("video_playing muss true oder false sein")

            self.server.state_callback(playing)
        except (ValueError, UnicodeDecodeError, json.JSONDecodeError):
            self._send_status(400)
            return

        self._send_status(204)

    def log_message(self, format, *args):
        return


class EvaMediaServer(ThreadingHTTPServer):

    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, state_callback):
        super().__init__(
            (MEDIA_SERVER_HOST, MEDIA_SERVER_PORT),
            EvaMediaRequestHandler,
        )
        self.state_callback = state_callback

class EvaPet(QWidget):

    music_state_ready = Signal(str)
    music_check_failed = Signal(str)
    video_state_ready = Signal(bool)

    def __init__(self):

        super().__init__()

        self.settings = Settings.load()

        # ----------------------------------------------------
        # Animation state
        # ----------------------------------------------------

        self.current_state = "idle"

        self.current_frame = 0

        self.frames: dict[
            str,
            list[QPixmap]
        ] = {}

        # Cache scaled pixmaps for the selected window size; avoid resizing on every tick.
        self._scaled_frames: dict[str, list[QPixmap]] = {}
        self._animation_epoch = time.perf_counter()
        self._bob_offset = 0

        # ----------------------------------------------------
        # Smooth motion
        # ----------------------------------------------------

        self.motion_start = time.perf_counter()

        # ----------------------------------------------------
        # Dragging
        # ----------------------------------------------------

        self.drag_offset: QPoint | None = None

        self.drag_start_global: QPoint | None = None

        self.was_dragged = False

        # ----------------------------------------------------
        # Automatic emotions
        # ----------------------------------------------------

        self.manual_state = False

        self.temporary_until = 0.0

        # ----------------------------------------------------
        # External command interface
        # ----------------------------------------------------

        self.last_command_mtime = 0.0

        # ----------------------------------------------------
        # UI
        # ----------------------------------------------------

        self.label = QLabel(self)

        self.label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        self.label.setAttribute(
            Qt.WidgetAttribute.WA_TranslucentBackground
        )

        # ----------------------------------------------------
        # Startup
        # ----------------------------------------------------

        self._setup_window()

        self._load_all_sprites()

        self._resize_pet(
            self.settings.width
        )

        self._restore_position()

        self._setup_timers()

        self._music_check_running = False
        self._music_playing = False
        self._video_playing = False
        self._media_reaction_active = False
        self._media_server = None

        self.music_state_ready.connect(self._apply_music_state)
        self.music_check_failed.connect(self._disable_music_detection)
        self.video_state_ready.connect(self._apply_video_state)

        self._start_media_server()

        self.music_timer = QTimer(self)

        self.music_timer.timeout.connect(self._start_apple_music_check)

        self.music_timer.start(2000)

        self._setup_tray()

        self.set_state(
            "idle",
            manual=False,
        )


    # ========================================================
    # Window
    # ========================================================

    def _setup_window(self):

        flags = (
            Qt.WindowType.FramelessWindowHint
            |
            Qt.WindowType.Tool
        )

        if self.settings.always_on_top:

            flags |= (
                Qt.WindowType.WindowStaysOnTopHint
            )

        self.setWindowFlags(flags)

        self.setAttribute(
            Qt.WidgetAttribute.WA_TranslucentBackground
        )

        self.setAutoFillBackground(False)


    # ========================================================
    # Sprite loading
    # ========================================================

    def _load_all_sprites(self):

        for state, sheets in SPRITES.items():

            original_frames: list[Image.Image] = []

            for sheet_path in sheets:

                if not sheet_path.exists():

                    raise FileNotFoundError(
                        f"\nSprite fehlt:\n"
                        f"{sheet_path}\n"
                    )

                with Image.open(sheet_path) as source:
                    sheet = source.convert("RGBA")

                if state == "dancing":
                    original_frames.extend(
                        aligned_grid_frames(sheet, 4, 2, (543, 724))
                    )
                    continue

                # --------------------------------------------
                # Sicherheit:
                # Das Sheet muss exakt durch 4 teilbar sein.
                # --------------------------------------------

                if (
                    sheet.width
                    % FRAMES_PER_SHEET
                    != 0
                ):

                    raise RuntimeError(
                        f"\nUngültiges Sprite-Sheet:\n"
                        f"{sheet_path}\n\n"
                        f"Breite: {sheet.width} px\n"
                        f"Die Breite muss durch "
                        f"{FRAMES_PER_SHEET} "
                        f"teilbar sein.\n"
                    )

                frame_width = (
                    sheet.width
                    //
                    FRAMES_PER_SHEET
                )

                frame_height = (
                    sheet.height
                )

                for i in range(
                    FRAMES_PER_SHEET
                ):

                    frame = sheet.crop(
                        (
                            i * frame_width,
                            0,
                            (i + 1) * frame_width,
                            frame_height,
                        )
                    )

                    original_frames.append(
                        frame
                    )

            if state in STABILIZE_STATES:
                original_frames = stabilize_frames(original_frames)

            intermediate_count = STATE_INTERMEDIATES.get(state, INTERMEDIATE_FRAMES)
            state_frames: list[QPixmap] = []

            for index, current_frame in enumerate(original_frames):

                next_index = (index + 1) % len(original_frames)
                next_frame = original_frames[next_index]
                blink_poses = BLINK_POSES.get(state, set())
                eye_regions = None
                open_eye_source = None
                if index in blink_poses or next_index in blink_poses:
                    eye_regions = (EYE_REGIONS[state][index], EYE_REGIONS[state][next_index])
                    open_eye_source = 1 if index in blink_poses else 0

                state_frames.append(
                    self._pil_image_to_pixmap(current_frame)
                )

                for intermediate in intermediate_frames(
                    current_frame,
                    next_frame,
                    intermediate_count,
                    eye_regions=eye_regions,
                    open_eye_source=open_eye_source,
                ):

                    state_frames.append(
                        self._pil_image_to_pixmap(intermediate)
                    )

            self.frames[state] = (
                state_frames
            )

            print(
                f"[EVA PET] "
                f"{state}: "
                f"{len(state_frames)} Frames geladen"
            )

    @staticmethod
    def _pil_image_to_pixmap(image: Image.Image) -> QPixmap:

        rgba_image = image.convert("RGBA")
        image_data = rgba_image.tobytes("raw", "RGBA")

        qimage = QImage(
            image_data,
            rgba_image.width,
            rgba_image.height,
            rgba_image.width * 4,
            QImage.Format.Format_RGBA8888,
        ).copy()

        pixmap = QPixmap.fromImage(qimage)
        # Maximum visible size is MAX_WIDTH. Avoid keeping ~1 GB of oversize
        # pixmaps after increasing the number of generated in-betweens.
        if pixmap.width() > MAX_WIDTH:
            pixmap = pixmap.scaledToWidth(
                MAX_WIDTH, Qt.TransformationMode.FastTransformation
            )
        return pixmap


    # ========================================================
    # Scaling
    # ========================================================

    def _scaled_state_frames(self, state: str) -> list[QPixmap]:
        cached = self._scaled_frames.get(state)
        if cached is None:
            cached = [self._scaled_frame(frame) for frame in self.frames[state]]
            self._scaled_frames[state] = cached
        return cached

    def _scaled_frame(
        self,
        pixmap: QPixmap,
    ) -> QPixmap:

        return pixmap.scaledToWidth(
            self.settings.width,

            # Pixel-Art:
            # FastTransformation hält die Pixel scharf
            Qt.TransformationMode.FastTransformation,
        )


    def _resize_pet(
        self,
        width: int,
    ):

        self.settings.width = max(
            MIN_WIDTH,
            min(
                MAX_WIDTH,
                width,
            ),
        )

        self._scaled_frames.clear()
        sample = self._scaled_state_frames(self.current_state)[0]

        window_width = (
            sample.width()
        )

        window_height = (
            sample.height()
            +
            (BOB_MARGIN * 2)
        )

        self.resize(
            window_width,
            window_height,
        )

        self.label.resize(
            sample.size()
        )

        self._show_frame()

        self.settings.save()


    # ========================================================
    # Frame rendering
    # ========================================================

    def _show_frame(self):

        frames = self._scaled_state_frames(self.current_state)
        pixmap = frames[self.current_frame % len(frames)]

        self.label.setPixmap(
            pixmap
        )

        self.label.resize(
            pixmap.size()
        )

        # horizontal zentrieren
        x = (
            self.width()
            -
            pixmap.width()
        ) // 2

        # Preserve the current hover offset instead of resetting it at each
        # sprite change. This used to create a visible vertical jump.
        self.label.move(x, BOB_MARGIN + self._bob_offset)

    def _refresh_tray_icon(self):
        # A QSystemTrayIcon update for every sprite frame is unnecessarily
        # expensive on Windows; update only when the emotion/size changes.
        if hasattr(self, "tray"):
            self.tray.setIcon(QIcon(self._scaled_state_frames(self.current_state)[0]))


    # ========================================================
    # Sprite animation
    # ========================================================

    def _next_frame(self):
        # Derive the pose from elapsed time, not from the number of QTimer calls.
        # Skipped Qt ticks cannot make the animation run permanently behind.
        frame_count = len(self.frames[self.current_state])
        intermediate_count = STATE_INTERMEDIATES.get(
            self.current_state, INTERMEDIATE_FRAMES
        )
        new_frame = frame_index_at(
            time.perf_counter() - self._animation_epoch,
            frame_count,
            STATE_FPS.get(self.current_state, 5),
            intermediate_count,
            ANIMATION_SPEED,
        )
        if new_frame != self.current_frame:
            self.current_frame = new_frame
            self._show_frame()
        self._update_motion()


    # ========================================================
    # Smooth 60 FPS hover movement
    # ========================================================

    def _update_motion(self):

        elapsed = (
            time.perf_counter()
            -
            self.motion_start
        )

        bob = STATE_BOB.get(
            self.current_state,
            STATE_BOB["idle"],
        )

        amplitude = bob["amplitude"]
        speed = bob["speed"] * ANIMATION_SPEED

        offset = math.sin(
            elapsed * speed
        ) * amplitude

        self._bob_offset = round(offset)
        pixmap = self.label.pixmap()

        if pixmap is None:
            return

        x = (
            self.width()
            -
            self.label.width()
        ) // 2

        y = (
            BOB_MARGIN
            +
            self._bob_offset
        )

        self.label.move(
            x,
            y,
        )


    # ========================================================
    # Position
    # ========================================================

    def _restore_position(self):

        screen = (
            QApplication
            .primaryScreen()
            .availableGeometry()
        )

        if (
            self.settings.x is None
            or
            self.settings.y is None
        ):

            x = (
                screen.right()
                -
                self.width()
                -
                30
            )

            y = (
                screen.bottom()
                -
                self.height()
                -
                30
            )

        else:

            x = int(
                self.settings.x
            )

            y = int(
                self.settings.y
            )

        x = max(
            screen.left(),

            min(
                x,
                screen.right()
                -
                self.width(),
            ),
        )

        y = max(
            screen.top(),

            min(
                y,
                screen.bottom()
                -
                self.height(),
            ),
        )

        self.move(
            x,
            y,
        )


    def _save_position(self):

        self.settings.x = (
            self.x()
        )

        self.settings.y = (
            self.y()
        )

        self.settings.save()

    def _update_animation_speed(self):
        # Called when the state changes. Rendering stays at 60 Hz regardless
        # of the chosen sprite playback speed.
        self._animation_epoch = time.perf_counter()


    # ========================================================
    # Timers
    # ========================================================

    def _setup_timers(self):

        # --------------------------------------------
        # Sprite frames
        # --------------------------------------------

        self.animation_timer = QTimer(
            self
        )

        self.animation_timer.timeout.connect(
            self._next_frame
        )

        self.animation_timer.setTimerType(Qt.TimerType.PreciseTimer)
        self._update_animation_speed()
        self.animation_timer.start(round(1000 / MOTION_FPS))

        # --------------------------------------------
        # Random behavior
        # --------------------------------------------

        self.auto_timer = QTimer(
            self
        )

        self.auto_timer.timeout.connect(
            self._auto_tick
        )

        self.auto_timer.start(
            1000
        )

        # --------------------------------------------
        # External commands
        # --------------------------------------------

        self.command_timer = QTimer(
            self
        )

        self.command_timer.timeout.connect(
            self._check_external_command
        )

        self.command_timer.start(
            250
        )


    # ========================================================
    # State / Emotion
    # ========================================================

    def set_state(
        self,
        state: str,
        *,
        manual: bool = False,
        duration: float | None = None,
    ):

        if state not in self.frames:
            return

        if (
            self.current_state
            ==
            state
        ):

            # Nicht jedes Mal Animation resetten
            # wenn Zustand bereits aktiv ist.
            return

        self.current_state = state

        self.current_frame = 0

        self._update_animation_speed()

        self.motion_start = (
            time.perf_counter()
        )

        self.manual_state = (
            manual
        )

        if duration is not None:

            self.temporary_until = (
                time.monotonic()
                +
                max(
                    0.1,
                    duration,
                )
            )

            self.manual_state = False

        else:

            self.temporary_until = 0.0

        self._show_frame()
        self._refresh_tray_icon()


    # ========================================================
    # Automatic behavior
    # ========================================================

    def _auto_tick(self):

        now = time.monotonic()

        # --------------------------------------------
        # temporary emotion ended
        # --------------------------------------------

        if (
            self.temporary_until
            and
            now
            >=
            self.temporary_until
        ):

            self.temporary_until = 0.0

            self.set_state(
                "idle",
                manual=False,
            )

            return

        if not self.settings.auto_mode:
            return

        if self.manual_state:
            return

        if self.temporary_until:
            return

        # ungefähr alle 15–30 Sekunden
        # gelegentlich eine kleine Aktion
        if random.random() < 0.045:

            state = random.choices(

                [
                    "curious",
                    "display",
                    "happy",
                    "dancing",
                    "sleeping",
                    "nervously",
                    "hide",
                    "watching",
                ],

                weights=[
                    45,
                    30,
                    25,
                    15,
                    10,
                    10,
                    5,
                    20,
                    
                ],

                k=1,

            )[0]

            durations = {

                "curious":
                    random.uniform(
                        4.0,
                        7.0,
                    ),

                "display":
                    random.uniform(
                        5.0,
                        9.0,
                    ),

                "happy":
                    random.uniform(
                        2.5,
                        4.5,
                    ),
                "dancing":
                    random.uniform(
                        3.0,
                        6.0,
                    ),
                "sleeping":
                    random.uniform(
                        10.0,
                        15.0,
                    ),
                "nervously":
                    random.uniform(
                        2.0,
                        5.0,
                    ),
                "hide":
                    random.uniform(
                        1.0,
                        3.0,
                    ),
                "watching":
                    random.uniform(
                        5.0,
                        10.0,
                    ),
            }

            self.set_state(

                state,

                manual=False,

                duration=
                durations[state],
            )


    # ========================================================
    # External command interface
    # ========================================================

    def _check_external_command(self):

        try:

            if not COMMAND_FILE.exists():
                return

            mtime = (
                COMMAND_FILE
                .stat()
                .st_mtime
            )

            if (
                mtime
                <=
                self.last_command_mtime
            ):

                return

            self.last_command_mtime = (
                mtime
            )

            data = json.loads(

                COMMAND_FILE.read_text(
                    encoding="utf-8"
                )
            )

            state = str(
                data.get(
                    "state",
                    "",
                )
            ).lower()

            duration = data.get(
                "duration"
            )

            if state not in self.frames:
                return

            if duration is None:

                self.set_state(
                    state,
                    manual=True,
                )

            else:

                self.set_state(
                    state,
                    manual=False,
                    duration=float(
                        duration
                    ),
                )

        except Exception as exc:

            print(
                "[EVA PET] "
                "Command Fehler:",
                exc,
            )


    # ========================================================
    # Context menu
    # ========================================================

    def _make_context_menu(
        self,
    ) -> QMenu:

        menu = QMenu()

        # --------------------------------------------
        # Emotionen
        # --------------------------------------------

        for state in (
            "idle",
            "happy",
            "curious",
            "sad",
            "display",
            "dancing",
            "sleeping",
            "nervously",
            "hide",
        ):

            action = QAction(
                STATE_LABELS[state],
                self,
            )

            action.triggered.connect(

                lambda checked=False,
                s=state:
                    self.set_state(
                        s,
                        manual=True,
                    )
            )

            menu.addAction(
                action
            )

        menu.addSeparator()

        # --------------------------------------------
        # Automatic mode
        # --------------------------------------------

        auto_action = QAction(
            "Auto-Emotionen",
            self,
        )

        auto_action.setCheckable(
            True
        )

        auto_action.setChecked(
            self.settings.auto_mode
        )

        def toggle_auto(
            value: bool,
        ):

            self.settings.auto_mode = (
                value
            )

            self.manual_state = (
                not value
            )

            if value:

                self.set_state(
                    "idle",
                    manual=False,
                )

            self.settings.save()

        auto_action.toggled.connect(
            toggle_auto
        )

        menu.addAction(
            auto_action
        )

        # --------------------------------------------
        # Always on top
        # --------------------------------------------

        top_action = QAction(
            "Immer im Vordergrund",
            self,
        )

        top_action.setCheckable(
            True
        )

        top_action.setChecked(
            self.settings.always_on_top
        )

        top_action.toggled.connect(
            self._toggle_always_on_top
        )

        menu.addAction(
            top_action
        )

        menu.addSeparator()

        # --------------------------------------------
        # Reset
        # --------------------------------------------

        reset_action = QAction(
            "Position zurücksetzen",
            self,
        )

        reset_action.triggered.connect(
            self._reset_position
        )

        menu.addAction(
            reset_action
        )

        # --------------------------------------------
        # Hide
        # --------------------------------------------

        hide_action = QAction(
            "Pet verstecken",
            self,
        )

        hide_action.triggered.connect(
            self.hide
        )

        menu.addAction(
            hide_action
        )

        menu.addSeparator()

        # --------------------------------------------
        # Quit
        # --------------------------------------------

        quit_action = QAction(
            "EVA Pet beenden",
            self,
        )

        quit_action.triggered.connect(
            QApplication.quit
        )

        menu.addAction(
            quit_action
        )

        return menu


    def contextMenuEvent(
        self,
        event,
    ):

        menu = (
            self._make_context_menu()
        )

        menu.exec(
            event.globalPos()
        )


    # ========================================================
    # System tray
    # ========================================================

    def _setup_tray(self):

        icon = self._scaled_frame(
            self.frames[
                "idle"
            ][0]
        )

        self.tray = QSystemTrayIcon(
            QIcon(icon),
            self,
        )

        self.tray.setToolTip(
            "EVA Desktop Pet"
        )

        self.tray.setContextMenu(
            self._make_context_menu()
        )

        self.tray.activated.connect(
            self._tray_activated
        )

        self.tray.show()


    def _tray_activated(
        self,
        reason,
    ):

        if (
            reason
            ==
            QSystemTrayIcon
            .ActivationReason
            .DoubleClick
        ):

            self.show()

            self.raise_()

            self.activateWindow()


    # ========================================================
    # Always on top
    # ========================================================

    def _toggle_always_on_top(
        self,
        enabled: bool,
    ):

        self.settings.always_on_top = (
            enabled
        )

        old_position = (
            self.pos()
        )

        self.hide()

        self._setup_window()

        self.show()

        self.move(
            old_position
        )

        self.settings.save()


    # ========================================================
    # Reset position
    # ========================================================

    def _reset_position(
        self,
    ):

        self.settings.x = None
        self.settings.y = None

        self._restore_position()

        self._save_position()


    # ========================================================
    # Snap to screen edges
    # ========================================================

    def _snap_to_edge(
        self,
    ):

        screen = QApplication.screenAt(
            self.frameGeometry().center()
        )

        if screen is None:

            screen = (
                QApplication
                .primaryScreen()
            )

        rect = (
            screen
            .availableGeometry()
        )

        pos = self.pos()

        snap_distance = 45

        x = pos.x()
        y = pos.y()

        if abs(
            x
            -
            rect.left()
        ) < snap_distance:

            x = rect.left()

        elif abs(
            (
                x
                +
                self.width()
            )
            -
            rect.right()
        ) < snap_distance:

            x = (
                rect.right()
                -
                self.width()
            )

        if abs(
            y
            -
            rect.top()
        ) < snap_distance:

            y = rect.top()

        elif abs(
            (
                y
                +
                self.height()
            )
            -
            rect.bottom()
        ) < snap_distance:

            y = (
                rect.bottom()
                -
                self.height()
            )

        self.move(
            x,
            y,
        )


    # ========================================================
    # Mouse dragging
    # ========================================================

    def mousePressEvent(
        self,
        event,
    ):

        if (
            event.button()
            ==
            Qt.MouseButton.LeftButton
        ):

            self.drag_start_global = (
                event
                .globalPosition()
                .toPoint()
            )

            self.drag_offset = (

                event
                .globalPosition()
                .toPoint()

                -

                self
                .frameGeometry()
                .topLeft()
            )

            self.was_dragged = False

            event.accept()

            return

        super().mousePressEvent(
            event
        )


    def mouseMoveEvent(
        self,
        event,
    ):

        if (

            event.buttons()
            &
            Qt.MouseButton.LeftButton

            and

            self.drag_offset
            is not None
        ):

            current = (
                event
                .globalPosition()
                .toPoint()
            )

            if (
                self.drag_start_global
                is not None
            ):

                distance = (
                    current
                    -
                    self.drag_start_global
                ).manhattanLength()

                if distance > 4:

                    self.was_dragged = (
                        True
                    )

            self.move(

                current
                -
                self.drag_offset
            )

            event.accept()

            return

        super().mouseMoveEvent(
            event
        )


    def mouseReleaseEvent(
        self,
        event,
    ):

        if (
            event.button()
            ==
            Qt.MouseButton.LeftButton
        ):

            if self.was_dragged:

                self._snap_to_edge()

                self._save_position()

            else:

                # EVA freut sich,
                # wenn man sie anklickt :)
                self.set_state(
                    "happy",
                    manual=False,
                    duration=2.2,
                )

            self.drag_offset = None

            self.drag_start_global = None

            self.was_dragged = False

            event.accept()

            return

        super().mouseReleaseEvent(
            event
        )


    # ========================================================
    # Mouse wheel = resize
    # ========================================================

    def wheelEvent(
        self,
        event,
    ):

        if (
            event
            .angleDelta()
            .y()
            >
            0
        ):

            delta = 12

        else:

            delta = -12

        self._resize_pet(
            self.settings.width
            +
            delta
        )

        event.accept()


    # ========================================================
    # Shutdown
    # ========================================================

    def closeEvent(
        self,
        event,
    ):

        self._save_position()

        if hasattr(
            self,
            "tray",
        ):

            self.tray.hide()

        if self._media_server is not None:
            self._media_server.shutdown()
            self._media_server.server_close()

        event.accept()

    def _start_media_server(self):
        try:
            self._media_server = EvaMediaServer(
                self.video_state_ready.emit
            )
        except OSError as error:
            if sys.stdout is not None:
                print(f"Video-Erkennung nicht gestartet: {error}")
            return

        Thread(
            target=self._media_server.serve_forever,
            daemon=True,
        ).start()

    def _start_apple_music_check(self):
        if self._music_check_running:
            return

        self._music_check_running = True

        Thread(
            target=self._check_apple_music,
            daemon=True,
        ).start()

    def _check_apple_music(self):
        try:
            creation_flags = getattr(
                subprocess,
                "CREATE_NO_WINDOW",
                0,
            )

            python_executable = Path(sys.executable)

            if python_executable.name.lower() == "pythonw.exe":
                python_executable = python_executable.with_name("python.exe")

            result = subprocess.run(
                [
                    str(python_executable),
                    str(Path(__file__).resolve()),
                    "--check-apple-music",
                ],
                capture_output=True,
                text=True,
                timeout=10,
                creationflags=creation_flags,
            )

            if result.returncode != 0:
                message = result.stderr.strip() or "Unbekannter Medienfehler"
                self.music_check_failed.emit(message)
                return

            state = result.stdout.strip()

            if state not in {"idle", "dancing"}:
                self.music_check_failed.emit(
                    f"Ungültiger Musikstatus: {state!r}"
                )
                return
        except Exception as error:
            self.music_check_failed.emit(str(error))
        else:
            self.music_state_ready.emit(state)
        finally:
            self._music_check_running = False

    def _apply_music_state(self, state: str):
        self._music_playing = state == "dancing"
        self._update_media_reaction()

    def _apply_video_state(self, playing: bool):
        self._video_playing = playing
        self._update_media_reaction()

    def _update_media_reaction(self):
        if self._music_playing:
            target_state = "dancing"
        elif self._video_playing:
            # Bis Popcorn-Sprites vorhanden sind, nutzt EVA "display".
            target_state = "watching"
        else:
            if self._media_reaction_active:
                self._media_reaction_active = False
                self.set_state("idle", manual=False)
            return

        self._media_reaction_active = True

        if self.current_state == target_state:
            self.manual_state = True
            self.temporary_until = 0.0
            return

        self.set_state(target_state, manual=True)

    def _disable_music_detection(self, message: str):
        self.music_timer.stop()

        if sys.stdout is not None:
            print(f"Apple-Music-Erkennung deaktiviert: {message}")


async def get_apple_music_state() -> str:
    from winrt.windows.media.control import (
        GlobalSystemMediaTransportControlsSessionManager,
    )

    manager = await (
        GlobalSystemMediaTransportControlsSessionManager.request_async()
    )

    for session in manager.get_sessions():
        app_id = session.source_app_user_model_id.lower()

        if "applemusic" not in app_id:
            continue

        playback_info = session.get_playback_info()
        status_code = playback_info.playback_status

        # 4 bedeutet „Playing“
        return "dancing" if status_code == 4 else "idle"

    return "idle"

# ============================================================
# Main
# ============================================================

def main() -> int:

    app = QApplication(
        sys.argv
    )

    # Wichtig:
    # App bleibt auch aktiv,
    # wenn Pet versteckt wird.
    app.setQuitOnLastWindowClosed(
        False
    )

    app.setApplicationName(
        "EVA Desktop Pet"
    )

    pet = EvaPet()

    pet.show()

    return app.exec()


if __name__ == "__main__":
    if "--check-apple-music" in sys.argv:
        try:
            detected_state = asyncio.run(get_apple_music_state())
        except Exception as error:
            print(str(error), file=sys.stderr)
            raise SystemExit(1)

        print(detected_state)
        raise SystemExit(0)

    raise SystemExit(
        main()
    )
