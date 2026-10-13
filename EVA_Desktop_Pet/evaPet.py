from __future__ import annotations
import os
import json
import sys
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QPoint, QRect, QSize, QTimer, Qt
from PySide6.QtGui import QAction, QCloseEvent, QContextMenuEvent, QMouseEvent, QPixmap, QResizeEvent, QWheelEvent
from PySide6.QtWidgets import QApplication, QLabel, QMenu, QMessageBox, QWidget


APP_DIR = Path(__file__).resolve().parent
STATE_FILE = APP_DIR / "petState.json"
MODEL_FILE = APP_DIR / "assets" / "models" / "sleep_bed_v2.png"
FRAME_DIR = APP_DIR / "assets" / "frames"

DEFAULT_WIDTH = 190
MIN_WIDTH = 80
MAX_WIDTH = 450
ANIMATION_FPS = 12


@dataclass
class Settings:
    width: int = DEFAULT_WIDTH
    x: int | None = None
    y: int | None = None

    # Diese Schalter sind schon fuer spaetere Funktionen vorgesehen.
    alwaysOnTop: bool = True
    autoMode: bool = True
    intelligentMode: bool = False
    agentMode: bool = False
    voiceMode: bool = False
    proactiveMode: bool = False
    debugMode: bool = False

    @classmethod
    def load(cls) -> "Settings":
        if not STATE_FILE.exists():
            return cls()

        try:
            data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
            return cls(
                width=max(MIN_WIDTH, min(MAX_WIDTH, int(data.get("width", DEFAULT_WIDTH)))),
                x=_optional_int(data.get("x")),
                y=_optional_int(data.get("y")),
                alwaysOnTop=bool(data.get("alwaysOnTop", True)),
                autoMode=bool(data.get("autoMode", True)),
                intelligentMode=bool(data.get("intelligentMode", False)),
                agentMode=bool(data.get("agentMode", False)),
                voiceMode=bool(data.get("voiceMode", False)),
                proactiveMode=bool(data.get("proactiveMode", False)),
                debugMode=bool(data.get("debugMode", False)),
            )
        except (OSError, TypeError, ValueError, json.JSONDecodeError):
            return cls()

    def save(self) -> None:
        data = {
            "width": self.width,
            "x": self.x,
            "y": self.y,
            "alwaysOnTop": self.alwaysOnTop,
            "autoMode": self.autoMode,
            "intelligentMode": self.intelligentMode,
            "agentMode": self.agentMode,
            "voiceMode": self.voiceMode,
            "proactiveMode": self.proactiveMode,
            "debugMode": self.debugMode,
        }
        STATE_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _optional_int(value: object) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def prepare_idle_frames() -> list[Path]:
    """Erzeugt fehlende Frames aus dem Sprite-Sheet und gibt sie sortiert zurueck."""
    from initializeFrames import FRAME_LAYOUT_VERSION, VERSION_FILE_NAME, extract_spritesheet

    frame_paths = sorted(FRAME_DIR.glob("idle_*.png"))
    version_file = FRAME_DIR / VERSION_FILE_NAME
    try:
        layout_is_current = version_file.read_text(encoding="utf-8") == FRAME_LAYOUT_VERSION
    except OSError:
        layout_is_current = False

    if len(frame_paths) != 32 or not layout_is_current:
        if not MODEL_FILE.exists():
            raise FileNotFoundError(f"Sprite-Sheet nicht gefunden: {MODEL_FILE}")
        frame_paths = extract_spritesheet(MODEL_FILE, FRAME_DIR)

    if len(frame_paths) != 32:
        raise RuntimeError(f"32 Idle-Frames erwartet, aber {len(frame_paths)} gefunden.")
    return frame_paths


class EvaPet(QWidget):
    def __init__(self, frame_paths: list[Path]) -> None:
        super().__init__()
        self.settings = Settings.load()
        self.frames = [QPixmap(str(path)) for path in frame_paths]
        if any(frame.isNull() for frame in self.frames):
            raise RuntimeError("Mindestens ein Animationsbild konnte nicht geladen werden.")

        self.frame_index = 0
        self.drag_offset: QPoint | None = None

        self.setWindowTitle("EVA Desktop Pet")
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setCursor(Qt.CursorShape.OpenHandCursor)

        self.image_label = QLabel(self)
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.image_label.setStyleSheet("background: transparent;")

        self._apply_window_flags()
        self._set_pet_size(self.settings.width)
        self._restore_position()
        self._show_current_frame()

        self.animation_timer = QTimer(self)
        self.animation_timer.timeout.connect(self._next_frame)
        self.animation_timer.start(round(1000 / ANIMATION_FPS))

    def _apply_window_flags(self) -> None:
        flags = Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool
        if self.settings.alwaysOnTop:
            flags |= Qt.WindowType.WindowStaysOnTopHint
        self.setWindowFlags(flags)

    def _restore_position(self) -> None:
        desired = QPoint(
            self.settings.x if self.settings.x is not None else 100,
            self.settings.y if self.settings.y is not None else 100,
        )
        screen = QApplication.screenAt(desired) or QApplication.primaryScreen()
        if screen is None:
            self.move(desired)
            return

        area = screen.availableGeometry()
        x = max(area.left(), min(desired.x(), area.right() - self.width() + 1))
        y = max(area.top(), min(desired.y(), area.bottom() - self.height() + 1))
        self.move(x, y)

    def _set_pet_size(self, width: int) -> None:
        width = max(MIN_WIDTH, min(MAX_WIDTH, width))
        self.settings.width = width
        self.setFixedSize(QSize(width, width))
        self.image_label.setGeometry(self.rect())
        self._show_current_frame()

    def _show_current_frame(self) -> None:
        if not self.frames:
            return
        pixmap = self.frames[self.frame_index].scaled(
            self.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.image_label.setPixmap(pixmap)

    def _next_frame(self) -> None:
        self.frame_index = (self.frame_index + 1) % len(self.frames)
        self._show_current_frame()

    def _save_position(self) -> None:
        self.settings.x = self.x()
        self.settings.y = self.y()
        self.settings.save()

    def _toggle_always_on_top(self, enabled: bool) -> None:
        position = self.pos()
        self.settings.alwaysOnTop = enabled
        self._apply_window_flags()
        self.move(position)
        self.show()
        self.settings.save()

    def resizeEvent(self, event: QResizeEvent) -> None:
        self.image_label.setGeometry(QRect(QPoint(0, 0), event.size()))
        self._show_current_frame()
        super().resizeEvent(event)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self.drag_offset is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self.drag_offset)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_offset = None
            self.setCursor(Qt.CursorShape.OpenHandCursor)
            self._save_position()
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def wheelEvent(self, event: QWheelEvent) -> None:
        step = 10 if event.angleDelta().y() > 0 else -10
        self._set_pet_size(self.settings.width + step)
        self.settings.save()
        event.accept()

    def contextMenuEvent(self, event: QContextMenuEvent) -> None:
        menu = QMenu(self)

        top_action = QAction("Immer im Vordergrund", menu)
        top_action.setCheckable(True)
        top_action.setChecked(self.settings.alwaysOnTop)
        top_action.toggled.connect(self._toggle_always_on_top)
        menu.addAction(top_action)

        size_menu = menu.addMenu("Groesse")
        for label, width in (("Klein", 120), ("Normal", DEFAULT_WIDTH), ("Gross", 280)):
            action = size_menu.addAction(label)
            action.triggered.connect(lambda checked=False, value=width: self._set_and_save_size(value))

        menu.addSeparator()
        quit_action = menu.addAction("EVA beenden")
        quit_action.triggered.connect(self.close)
        menu.exec(event.globalPos())

    def _set_and_save_size(self, width: int) -> None:
        self._set_pet_size(width)
        self.settings.save()

    def closeEvent(self, event: QCloseEvent) -> None:
        self._save_position()
        for file in os.listdir("assets/frames"):
            if file.endswith(".png"):
                os.remove(os.path.join("assets/frames", file))
        super().closeEvent(event)


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("EVA Desktop Pet")

    try:
        frame_paths = prepare_idle_frames()
        pet = EvaPet(frame_paths)
    except Exception as error:
        QMessageBox.critical(None, "EVA konnte nicht starten", str(error))
        return 1

    pet.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
