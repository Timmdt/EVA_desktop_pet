from __future__ import annotations
import json
import os
import random
import time
import sys
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

from EVA_Desktop_Pet.initializeFrames import STATE_FILE as stateFile


defaultWidth = 190
minWidth = 80
maxWidth = 450
montionFPS = 60

stateFile = Path(__file__).resolve().parent / "petState.json"

@dataclass
class Settings:
    width: int = defaultWidth

    x: int | None = None
    y: int | None = None

# System modes for the pet
    alwaysOnTop: bool = True
    autoMode: bool = True
    intelligentMode: bool = False
    agentMode: bool = False
    voiceMode: bool = False
    proactiveMode: bool = False
    debugMode: bool = False
    

    @classmethod
    def load(cls) -> "Settings":

        if not stateFile.exists():
            return cls()

        try:
            data = json.loads(
                stateFile.read_text(
                    encoding="utf-8"
                )
            )

            return cls(
                width=max(
                    minWidth,
                    min(
                        maxWidth,
                        int(
                            data.get(
                                "width",
                                defaultWidth,
                            )
                        ),
                    ),
                ),

                x=data.get("x"),
                y=data.get("y"),

                alwaysOnTop=bool(
                    data.get(
                        "alwaysOnTop",
                        True,
                    )
                ),
                autoMode=bool(
                    data.get(
                        "autoMode",
                        True,
                    )
                ),
                intelligentMode=bool(
                    data.get(
                        "intelligentMode",
                        False,
                    )
                ),
                agentMode=bool(
                    data.get(
                        "agentMode",
                        False,
                    )
                ),
                voiceMode=bool(
                    data.get(
                        "voiceMode",
                        False,
                    )
                ),
                proactiveMode=bool(
                    data.get(
                        "proactiveMode",
                        False,
                    )
                ),
                debugMode=bool(
                    data.get(
                        "debugMode",
                        False,
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
            "alwaysOnTop": self.alwaysOnTop,
            "autoMode": self.autoMode,
            "intelligentMode": self.intelligentMode ,
            "agentMode": self.agentMode,
            "voiceMode": self.voiceMode,
            "proactiveMode": self.proactiveMode,
            "debugMode": self.debugMode,
        }

        stateFile.write_text(
            json.dumps(
                data,
                indent=2,
            ),
            encoding="utf-8",
        )

class EvaPet(Qwidget):

    def __init__(self):
        super().__init__()
        self.settings = self.loadSettings()
        self.setWindowTitle("Eva Pet")
        self.setGeometry(self.settings.x or 100, self.settings.y or 100, 400, 400)
