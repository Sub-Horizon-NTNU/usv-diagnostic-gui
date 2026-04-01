import time

from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtCore import pyqtSlot, Qt, QTimer

_DARK = """
    CameraWindow, QWidget {
        background-color: #1e1e1e;
        color: #cccccc;
        border: none;
    }
    QLabel { color: #cccccc; background: transparent; border: none; }
    QPushButton {
        background-color: #3c3c3c;
        color: #cccccc;
        border: 1px solid #555555;
        border-radius: 4px;
        padding: 4px 10px;
    }
    QPushButton:hover { background-color: #4a4a4a; }
    QPushButton:checked { background-color: #2a5a8a; border-color: #4a8abf; }
    QSlider::groove:horizontal {
        height: 4px;
        background: #444444;
        border-radius: 2px;
    }
    QSlider::handle:horizontal {
        background: #888888;
        width: 14px;
        height: 14px;
        margin: -5px 0;
        border-radius: 7px;
    }
    QSlider::sub-page:horizontal { background: #4a8abf; border-radius: 2px; }
"""


class CameraWindow(QtWidgets.QWidget):
    def __init__(self, ros_node, parent=None):
        super().__init__(parent)
        self._ros_node = ros_node
        self.setWindowTitle("Camera")
        self.setMinimumSize(640, 540)
        self.setStyleSheet(_DARK)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)

        video_container = QtWidgets.QWidget()
        video_container.setMinimumSize(640, 480)
        video_container.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding
        )

        self._video_label = QtWidgets.QLabel("No video stream", video_container)
        self._video_label.setAlignment(Qt.AlignCenter)
        self._video_label.setStyleSheet(
            "background-color: #1a1a1a; color: #555555; font-size: 16px;"
        )

        _overlay_style = (
            "color: #ffffff;"
            "font-family: sans-serif;"
            "font-size: 18px;"
            "font-weight: bold;"
            "background-color: rgba(180, 0, 0, 210);"
            "padding: 14px 24px;"
            "border-radius: 6px;"
            "letter-spacing: 1px;"
        )

        self._paused_overlay = QtWidgets.QLabel("PAUSED", video_container)
        self._paused_overlay.setAlignment(Qt.AlignCenter)
        self._paused_overlay.setStyleSheet(_overlay_style)
        self._paused_overlay.setAttribute(Qt.WA_TransparentForMouseEvents)
        self._paused_overlay.setFixedSize(self._paused_overlay.sizeHint())

        self._no_signal_overlay = QtWidgets.QLabel("NO SIGNAL", video_container)
        self._no_signal_overlay.setAlignment(Qt.AlignCenter)
        self._no_signal_overlay.setStyleSheet(_overlay_style)
        self._no_signal_overlay.setAttribute(Qt.WA_TransparentForMouseEvents)
        self._no_signal_overlay.setFixedSize(self._no_signal_overlay.sizeHint())
        self._no_signal_overlay.hide()

        layout.addWidget(video_container, stretch=1)
        self._video_container = video_container

        ctrl = QtWidgets.QHBoxLayout()
        ctrl.setSpacing(6)

        ctrl.addWidget(QtWidgets.QLabel("Pan:"))

        self._slider = QtWidgets.QSlider(Qt.Horizontal)
        self._slider.setRange(600, 2400)
        self._slider.setValue(1500)
        self._slider.setTickPosition(QtWidgets.QSlider.TicksBelow)
        self._slider.setTickInterval(300)
        self._slider.valueChanged.connect(self._on_slider)
        ctrl.addWidget(self._slider, stretch=1)

        self._pos_label = QtWidgets.QLabel("1500 µs")
        self._pos_label.setFixedWidth(75)
        ctrl.addWidget(self._pos_label)

        center_btn = QtWidgets.QPushButton("Center")
        center_btn.setFixedWidth(65)
        center_btn.clicked.connect(lambda: self._slider.setValue(1500))
        ctrl.addWidget(center_btn)

        self._pause_btn = QtWidgets.QPushButton("▶ Resume")
        self._pause_btn.setFixedWidth(90)
        self._pause_btn.setCheckable(True)
        self._pause_btn.setChecked(True)
        self._pause_btn.clicked.connect(self._on_pause_toggled)
        ctrl.addWidget(self._pause_btn)

        self._fs_btn = QtWidgets.QPushButton("⛶")
        self._fs_btn.setFixedWidth(32)
        self._fs_btn.setCheckable(True)
        self._fs_btn.setToolTip("Fullscreen (Esc to exit)")
        self._fs_btn.setStyleSheet(
            "QPushButton { background: transparent; border: none; color: #666666; font-size: 16px; }"
            "QPushButton:hover { color: #aaaaaa; }"
            "QPushButton:checked { color: #4a8abf; }"
        )
        self._fs_btn.clicked.connect(self._toggle_fullscreen)
        ctrl.addWidget(self._fs_btn)

        layout.addLayout(ctrl)

        self._last_frame_time = 0.0
        self._stale_timer = QTimer(self)
        self._stale_timer.setSingleShot(True)
        self._stale_timer.setInterval(3000)
        self._stale_timer.timeout.connect(lambda: self._no_signal_overlay.setVisible(True))

        # Start paused
        ros_node.set_stream_paused(True)
        ros_node.image_updated.connect(self._on_image)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._video_label.setGeometry(self._video_container.rect())
        r = self._video_container.rect()
        for overlay in (self._paused_overlay, self._no_signal_overlay):
            s = overlay.size()
            overlay.move(
                (r.width()  - s.width())  // 2,
                (r.height() - s.height()) // 2,
            )

    @pyqtSlot(bytes)
    def _on_image(self, jpeg_bytes: bytes):
        now = time.monotonic()
        if now - self._last_frame_time < 1 / 30:
            return
        self._last_frame_time = now
        self._no_signal_overlay.hide()
        self._stale_timer.start()
        pixmap = QtGui.QPixmap()
        pixmap.loadFromData(jpeg_bytes, 'JPEG')
        scaled = pixmap.scaled(
            self._video_label.size(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )
        self._video_label.setPixmap(scaled)

    def _on_pause_toggled(self, checked: bool):
        self._pause_btn.setText("⏸ Pause" if not checked else "▶ Resume")
        self._paused_overlay.setVisible(checked)
        if checked:
            self._stale_timer.stop()
            self._no_signal_overlay.hide()
        else:
            self._stale_timer.start()
        self._ros_node.set_stream_paused(checked)

    def _toggle_fullscreen(self, checked):
        if checked:
            self.showFullScreen()
        else:
            self.showNormal()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape and self.isFullScreen():
            self._fs_btn.setChecked(False)
            self.showNormal()
        super().keyPressEvent(event)

    def _on_slider(self, value: int):
        self._pos_label.setText(f"{value} µs")
        self._ros_node.send_servo(value)
