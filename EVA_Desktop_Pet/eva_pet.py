from __future__ import annotations

import json
import math
import random
import sys
import time
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QPoint, QTimer, Qt
from PySide6.QtGui import QAction, QIcon, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QLabel,
    QMenu,
    QSystemTrayIcon,
    QWidget,
)


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
}


STATE_LABELS = {
    "idle": "Idle",
    "happy": "Fröhlich",
    "curious": "Neugierig",
    "sad": "Traurig",
    "display": "Zum Display schauen",
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

class EvaPet(QWidget):

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

            state_frames = []

            for sheet_path in sheets:

                if not sheet_path.exists():

                    raise FileNotFoundError(
                        f"\nSprite fehlt:\n"
                        f"{sheet_path}\n"
                    )

                sheet = QPixmap(
                    str(sheet_path)
                )

                if sheet.isNull():

                    raise RuntimeError(
                        f"Sprite konnte nicht geladen werden:\n"
                        f"{sheet_path}"
                    )

                # --------------------------------------------
                # Sicherheit:
                # Das Sheet muss exakt durch 4 teilbar sein.
                # --------------------------------------------

                if (
                    sheet.width()
                    % FRAMES_PER_SHEET
                    != 0
                ):

                    raise RuntimeError(
                        f"\nUngültiges Sprite-Sheet:\n"
                        f"{sheet_path}\n\n"
                        f"Breite: {sheet.width()} px\n"
                        f"Die Breite muss durch "
                        f"{FRAMES_PER_SHEET} "
                        f"teilbar sein.\n"
                    )

                frame_width = (
                    sheet.width()
                    //
                    FRAMES_PER_SHEET
                )

                frame_height = (
                    sheet.height()
                )

                for i in range(
                    FRAMES_PER_SHEET
                ):

                    frame = sheet.copy(
                        i * frame_width,
                        0,
                        frame_width,
                        frame_height,
                    )

                    state_frames.append(
                        frame
                    )

            self.frames[state] = (
                state_frames
            )

            print(
                f"[EVA PET] "
                f"{state}: "
                f"{len(state_frames)} Frames geladen"
            )


    # ========================================================
    # Scaling
    # ========================================================

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

        sample = self._scaled_frame(
            self.frames[
                self.current_state
            ][0]
        )

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

        frames = self.frames[
            self.current_state
        ]

        pixmap = self._scaled_frame(
            frames[
                self.current_frame
                %
                len(frames)
            ]
        )

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

        self.label.move(
            x,
            BOB_MARGIN,
        )

        if hasattr(
            self,
            "tray",
        ):

            self.tray.setIcon(
                QIcon(pixmap)
            )


    # ========================================================
    # Sprite animation
    # ========================================================

    def _next_frame(self):

        frame_count = len(
            self.frames[
                self.current_state
            ]
        )

        self.current_frame = (
            self.current_frame + 1
        ) % frame_count

        self._show_frame()


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
        speed = bob["speed"]

        offset = math.sin(
            elapsed * speed
        ) * amplitude

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
            int(offset)
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

        fps = STATE_FPS.get(
            self.current_state,
            5,
        )

        interval = int(
            1000 / fps
        )

        self.animation_timer.setInterval(
            interval
        )


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

        self._update_animation_speed()
        self.animation_timer.start()

        # --------------------------------------------
        # Smooth movement
        # --------------------------------------------

        self.motion_timer = QTimer(
            self
        )

        self.motion_timer.timeout.connect(
            self._update_motion
        )

        self.motion_timer.start(
            int(
                1000
                /
                MOTION_FPS
            )
        )

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
                ],

                weights=[
                    45,
                    30,
                    25,
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

        event.accept()


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

    raise SystemExit(
        main()
    )