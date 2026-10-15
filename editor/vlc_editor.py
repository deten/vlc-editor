"""VLC Editor: trim, crop and slow-mo the video that is open in VLC.

Usage:
    pythonw vlc_editor.py [<path or file:// uri> | --hexuri <hex-encoded uri>] [--time <ms>]

With no file argument a file picker is shown.
"""
from __future__ import annotations

import ctypes
import glob
import json
import os
import shutil
import subprocess
import sys
import threading
import traceback
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path

import vlc
from PySide6.QtCore import QObject, QPointF, QProcess, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QImage, QKeySequence, QPainter, QPainterPath, QPen, QShortcut
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QFileDialog, QHBoxLayout, QLabel, QMainWindow, QMessageBox,
    QProgressDialog, QPushButton, QSizePolicy, QVBoxLayout, QWidget,
)

# packaged build: the folder holding "VLC Editor.exe"; from source: this script's folder
APP_DIR = Path(sys.executable if getattr(sys, "frozen", False) else __file__).resolve().parent
CONFIG_FILE = APP_DIR / "config.json"
ERROR_LOG = APP_DIR / "last_error.log"
PREVIEW_MAX = 1280       # longest side of the preview frames VLC renders for us
MIN_CLIP_MS = 200
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)

ACCENT = QColor("#ffc83d")   # trim handles / crop
SLOW = QColor("#9b7bff")     # slow-mo range

STYLE = """
QWidget { background: #181818; color: #e8e8e8; font-size: 10pt; }
QPushButton { background: #2b2b2b; border: 1px solid #3a3a3a; border-radius: 6px; padding: 6px 12px; }
QPushButton:hover { background: #353535; }
QPushButton:checked { background: #ffc83d; color: #1a1a1a; border-color: #ffc83d; }
QPushButton#slow:checked { background: #9b7bff; color: #ffffff; border-color: #9b7bff; }
QPushButton#save { background: #2f7cf6; border-color: #2f7cf6; color: white; font-weight: 600; padding: 6px 22px; }
QPushButton#save:hover { background: #4a8ff8; }
QPushButton#play { font-size: 12pt; min-width: 36px; }
QComboBox { background: #2b2b2b; border: 1px solid #3a3a3a; border-radius: 6px; padding: 5px 8px; }
QComboBox QAbstractItemView { background: #2b2b2b; selection-background-color: #3d3d3d; }
QLabel#muted { color: #9a9a9a; }
"""


# ---------------------------------------------------------------- helpers

def load_config() -> dict:
    try:
        return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def find_tool(name: str) -> str | None:
    """Locate ffmpeg / ffprobe / vlc: config.json, bundled copy, PATH, then the usual install folders."""
    configured = load_config().get(name)
    if configured and Path(configured).is_file():
        return configured
    bundled = APP_DIR / "ffmpeg" / (name + ".exe")    # shipped with the packaged build
    if bundled.is_file():
        return str(bundled)
    found = shutil.which(name)
    if found:
        return found
    local = os.environ.get("LOCALAPPDATA", "")
    program_files = os.environ.get("ProgramFiles", r"C:\Program Files")
    patterns = [
        os.path.join(local, "Microsoft", "WinGet", "Packages", "Gyan.FFmpeg*", "*", "bin", name + ".exe"),
        os.path.join(program_files, "VideoLAN", "VLC", name + ".exe"),
    ]
    for pattern in patterns:
        hits = glob.glob(pattern)
        if hits:
            return hits[0]
    return None


def to_local_path(source: str) -> str:
    """Accept a plain path or a file:// URI (as VLC reports it) and return a local path."""
    if "://" not in source:
        return source
    parsed = urllib.parse.urlparse(source)
    if parsed.scheme.lower() != "file":
        raise ValueError(f"Only local files can be edited (this is a {parsed.scheme}:// stream).")
    path = urllib.request.url2pathname(parsed.path)
    if parsed.netloc and parsed.netloc.lower() != "localhost":
        path = "\\\\" + parsed.netloc + path
    return path


def parse_args(argv: list[str]) -> tuple[str | None, int]:
    source, start_ms = None, 0
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg == "--hexuri" and i + 1 < len(argv):
            source = bytes.fromhex(argv[i + 1]).decode("utf-8", errors="replace")
            i += 2
        elif arg == "--time" and i + 1 < len(argv):
            try:
                start_ms = max(0, int(float(argv[i + 1])))
            except ValueError:
                pass
            i += 2
        else:
            source = arg
            i += 1
    return (to_local_path(source) if source else None), start_ms


def fmt_time(ms: float) -> str:
    tenths_total = max(0, int(ms)) // 100
    seconds, tenths = divmod(tenths_total, 10)
    minutes, seconds = divmod(seconds, 60)
    return f"{minutes}:{seconds:02d}.{tenths}"


def clamp(value, low, high):
    return max(low, min(high, value))


@dataclass
class MediaInfo:
    width: int          # display size, i.e. after the phone's rotation flag is applied
    height: int
    duration_ms: int
    fps: str            # ffmpeg rate string, e.g. "30000/1001"
    has_audio: bool


def probe(ffprobe: str, path: str) -> MediaInfo:
    result = subprocess.run(
        [ffprobe, "-v", "error", "-print_format", "json", "-show_streams", "-show_format", path],
        capture_output=True, creationflags=NO_WINDOW)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.decode(errors="replace").strip() or "ffprobe failed")
    data = json.loads(result.stdout)
    streams = data.get("streams", [])
    video = next((s for s in streams if s.get("codec_type") == "video"
                  and not s.get("disposition", {}).get("attached_pic")), None)
    if video is None:
        raise RuntimeError("No video stream found in this file.")

    rotation = 0
    for side in video.get("side_data_list", []):
        if "rotation" in side:
            rotation = int(round(float(side["rotation"])))
    if not rotation:
        rotation = int(video.get("tags", {}).get("rotate", 0) or 0)
    width, height = int(video["width"]), int(video["height"])
    if abs(rotation) % 180 == 90:
        width, height = height, width

    duration = float(data.get("format", {}).get("duration") or video.get("duration") or 0)
    fps = video.get("avg_frame_rate") or "0/0"
    num, _, den = fps.partition("/")
    try:
        if not 1 <= float(num) / float(den or 1) <= 1000:
            fps = "30"
    except (ValueError, ZeroDivisionError):
        fps = "30"
    has_audio = any(s.get("codec_type") == "audio" for s in streams)
    return MediaInfo(width, height, int(duration * 1000), fps, has_audio)


# ---------------------------------------------------------------- export

@dataclass
class EditSpec:
    start_ms: int
    end_ms: int
    crop: tuple[int, int, int, int] | None = None   # w, h, x, y in display pixels
    slow: tuple[int, int] | None = None              # absolute ms range
    speed: float = 1.0
    mute_slow: bool = True
    smooth: bool = False

    def output_ms(self) -> int:
        length = self.end_ms - self.start_ms
        if self.slow:
            length += (self.slow[1] - self.slow[0]) * (1 / self.speed - 1)
        return int(length)


def atempo_chain(speed: float) -> str:
    # atempo only goes down to 0.5 per instance, so chain it for slower speeds
    parts = []
    while speed < 0.5 - 1e-9:
        parts.append("atempo=0.5")
        speed /= 0.5
    parts.append(f"atempo={speed:g}")
    return ",".join(parts)


def build_ffmpeg_args(spec: EditSpec, info: MediaInfo, src: str, dst: str) -> list[str]:
    start = spec.start_ms / 1000
    length = (spec.end_ms - spec.start_ms) / 1000
    args = ["-hide_banner", "-y", "-ss", f"{start:.3f}", "-t", f"{length:.3f}", "-i", src]

    base = "crop={0}:{1}:{2}:{3}".format(*spec.crop) if spec.crop else "null"
    audio = info.has_audio

    segments = [(0.0, length, 1.0)]
    if spec.slow:
        s0 = clamp(spec.slow[0] / 1000 - start, 0, length)
        s1 = clamp(spec.slow[1] / 1000 - start, 0, length)
        factor = 1 / spec.speed
        segments = [(a, b, f) for a, b, f in ((0.0, s0, 1.0), (s0, s1, factor), (s1, length, 1.0))
                    if b - a > 0.01]

    if len(segments) == 1 and segments[0][2] == 1:
        graph = f"[0:v]{base}[vout]"
        if audio:
            graph += ";[0:a]anull[aout]"
    else:
        n = len(segments)
        chains = [f"[0:v]{base},split={n}" + "".join(f"[v{i}]" for i in range(n))]
        if audio:
            chains.append(f"[0:a]asplit={n}" + "".join(f"[a{i}]" for i in range(n)))
        for i, (a, b, f) in enumerate(segments):
            v = f"[v{i}]trim=start={a:.3f}:end={b:.3f},setpts=(PTS-STARTPTS)*{f:g}"
            if f != 1 and spec.smooth:
                v += f",minterpolate=fps={info.fps}:mi_mode=mci"
            chains.append(v + f"[vs{i}]")
            if audio:
                aud = f"[a{i}]atrim=start={a:.3f}:end={b:.3f},asetpts=PTS-STARTPTS"
                if f != 1:
                    aud += "," + atempo_chain(spec.speed)
                    if spec.mute_slow:
                        aud += ",volume=0"
                chains.append(aud + f"[as{i}]")
        pads = "".join(f"[vs{i}]" + (f"[as{i}]" if audio else "") for i in range(n))
        chains.append(f"{pads}concat=n={n}:v=1:a={int(audio)}[vout]" + ("[aout]" if audio else ""))
        graph = ";".join(chains)

    args += ["-filter_complex", graph, "-map", "[vout]"]
    args += ["-map", "[aout]", "-c:a", "aac", "-b:a", "192k"] if audio else ["-an"]
    args += ["-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
             "-r", info.fps, "-movflags", "+faststart",
             "-progress", "pipe:1", "-nostats", "-loglevel", "error", dst]
    return args


def unique_output_path(src: str) -> str:
    p = Path(src)
    candidate = p.with_name(f"{p.stem}_edit.mp4")
    n = 2
    while candidate.exists():
        candidate = p.with_name(f"{p.stem}_edit{n}.mp4")
        n += 1
    return str(candidate)


# ---------------------------------------------------------------- video frames from libvlc

class FrameSink(QObject):
    """Has libvlc decode into our own buffer so Qt can paint the frame and draw on top of it."""
    frame_ready = Signal()

    def __init__(self, player: vlc.MediaPlayer, width: int, height: int):
        super().__init__()
        self.width, self.height, self.pitch = width, height, width * 4
        self._buf = (ctypes.c_ubyte * (self.pitch * height))()
        self._addr = ctypes.addressof(self._buf)
        self._lock = threading.Lock()
        self._latest: bytes | None = None
        # keep references so the ctypes callbacks are not garbage collected
        self._lock_cb = vlc.CallbackDecorators.VideoLockCb(self._on_lock)
        self._unlock_cb = vlc.CallbackDecorators.VideoUnlockCb(self._on_unlock)
        self._display_cb = vlc.CallbackDecorators.VideoDisplayCb(self._on_display)
        player.video_set_callbacks(self._lock_cb, self._unlock_cb, self._display_cb, None)
        player.video_set_format("RV32", width, height, self.pitch)

    def _on_lock(self, opaque, planes):
        self._lock.acquire()
        planes[0] = self._addr
        return None

    def _on_unlock(self, opaque, picture, planes):
        self._lock.release()

    def _on_display(self, opaque, picture):
        with self._lock:
            self._latest = bytes(self._buf)
        self.frame_ready.emit()

    def take_image(self) -> QImage | None:
        data, self._latest = self._latest, None
        if data is None:
            return None
        return QImage(data, self.width, self.height, self.pitch, QImage.Format.Format_RGB32).copy()


class ThumbLoader(QObject):
    thumb_ready = Signal(int, QImage)

    def start(self, ffmpeg: str, path: str, duration_ms: int, count: int):
        threading.Thread(target=self._run, args=(ffmpeg, path, duration_ms, count), daemon=True).start()

    def _run(self, ffmpeg, path, duration_ms, count):
        for i in range(count):
            t = (i + 0.5) * duration_ms / count / 1000
            result = subprocess.run(
                [ffmpeg, "-v", "error", "-ss", f"{t:.3f}", "-i", path, "-frames:v", "1",
                 "-vf", "scale=-2:96", "-f", "image2pipe", "-c:v", "png", "-"],
                capture_output=True, creationflags=NO_WINDOW)
            image = QImage.fromData(result.stdout, "PNG")
            if not image.isNull():
                self.thumb_ready.emit(i, image)


# ---------------------------------------------------------------- video view with crop overlay

class VideoView(QWidget):
    crop_changed = Signal()
    HANDLE = 14
    MIN_SIZE = 0.05
    MARGIN = 14
    CURSORS = {
        "tl": Qt.CursorShape.SizeFDiagCursor, "br": Qt.CursorShape.SizeFDiagCursor,
        "tr": Qt.CursorShape.SizeBDiagCursor, "bl": Qt.CursorShape.SizeBDiagCursor,
        "l": Qt.CursorShape.SizeHorCursor, "r": Qt.CursorShape.SizeHorCursor,
        "t": Qt.CursorShape.SizeVerCursor, "b": Qt.CursorShape.SizeVerCursor,
        "move": Qt.CursorShape.SizeAllCursor,
    }

    def __init__(self, src_w: int, src_h: int):
        super().__init__()
        self.src_w, self.src_h = src_w, src_h
        self.image: QImage | None = None
        self.crop_mode = False
        self.crop = QRectF(0, 0, 1, 1)       # normalised to the full frame
        self.aspect: float | None = None     # locked width/height in pixels, None = free
        self._drag: str | None = None
        self._press = QPointF()
        self._orig = QRectF()
        self.setMouseTracking(True)
        self.setMinimumSize(320, 220)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    # -- geometry
    def _fit(self, w: float, h: float) -> QRectF:
        m = self.MARGIN
        avail = QRectF(self.rect()).adjusted(m, m, -m, -m)
        scale = min(avail.width() / w, avail.height() / h)
        c = avail.center()
        return QRectF(c.x() - w * scale / 2, c.y() - h * scale / 2, w * scale, h * scale)

    def frame_rect(self) -> QRectF:
        return self._fit(self.src_w, self.src_h)

    def crop_rect_px(self) -> QRectF:
        fr, c = self.frame_rect(), self.crop
        return QRectF(fr.x() + c.x() * fr.width(), fr.y() + c.y() * fr.height(),
                      c.width() * fr.width(), c.height() * fr.height())

    def is_cropped(self) -> bool:
        return self.crop.width() < 0.999 or self.crop.height() < 0.999

    def crop_pixels(self) -> tuple[int, int, int, int] | None:
        if not self.is_cropped():
            return None
        c = self.crop
        w = max(2, int(round(c.width() * self.src_w)) // 2 * 2)
        h = max(2, int(round(c.height() * self.src_h)) // 2 * 2)
        x = clamp(int(round(c.x() * self.src_w)), 0, self.src_w - w)
        y = clamp(int(round(c.y() * self.src_h)), 0, self.src_h - h)
        return w, h, x, y

    # -- public
    def set_image(self, image: QImage):
        self.image = image
        self.update()

    def set_crop_mode(self, on: bool):
        self.crop_mode = on
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self.update()

    def set_aspect(self, aspect: float | None):
        self.aspect = aspect
        if aspect is not None:
            ratio = aspect * self.src_h / self.src_w     # normalised width / height
            w, h = (1.0, 1.0 / ratio) if ratio >= 1 else (ratio, 1.0)
            center = self.crop.center()
            x = clamp(center.x() - w / 2, 0, 1 - w)
            y = clamp(center.y() - h / 2, 0, 1 - h)
            self.crop = QRectF(x, y, w, h)
            self.crop_changed.emit()
        self.update()

    def reset_crop(self):
        self.crop = QRectF(0, 0, 1, 1)
        self.aspect = None
        self.crop_changed.emit()
        self.update()

    # -- painting
    def paintEvent(self, event):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor("#0e0e0e"))
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        if not self.crop_mode and self.is_cropped():
            # show the result: just the cropped area, scaled to fit
            c = self.crop
            target = self._fit(c.width() * self.src_w, c.height() * self.src_h)
            if self.image is not None:
                iw, ih = self.image.width(), self.image.height()
                source = QRectF(c.x() * iw, c.y() * ih, c.width() * iw, c.height() * ih)
                p.drawImage(target, self.image, source)
            return

        fr = self.frame_rect()
        if self.image is not None:
            p.drawImage(fr, self.image)
        if not self.crop_mode:
            return

        cr = self.crop_rect_px()
        shade = QPainterPath()
        shade.setFillRule(Qt.FillRule.OddEvenFill)
        shade.addRect(fr)
        shade.addRect(cr)
        p.fillPath(shade, QColor(0, 0, 0, 160))

        p.setPen(QPen(QColor(255, 255, 255, 90), 1))
        for i in (1, 2):
            x = cr.left() + cr.width() * i / 3
            y = cr.top() + cr.height() * i / 3
            p.drawLine(QPointF(x, cr.top()), QPointF(x, cr.bottom()))
            p.drawLine(QPointF(cr.left(), y), QPointF(cr.right(), y))
        p.setPen(QPen(QColor("white"), 2))
        p.drawRect(cr)

        # corner brackets
        p.setPen(QPen(ACCENT, 4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.SquareCap))
        L = min(22.0, cr.width() / 3, cr.height() / 3)
        for corner, sx, sy in ((cr.topLeft(), 1, 1), (cr.topRight(), -1, 1),
                               (cr.bottomLeft(), 1, -1), (cr.bottomRight(), -1, -1)):
            p.drawLine(corner, corner + QPointF(L * sx, 0))
            p.drawLine(corner, corner + QPointF(0, L * sy))
        if self.aspect is None:
            p.setPen(QPen(ACCENT, 4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            h = min(10.0, cr.width() / 6, cr.height() / 6)
            mid = cr.center()
            p.drawLine(QPointF(mid.x() - h, cr.top()), QPointF(mid.x() + h, cr.top()))
            p.drawLine(QPointF(mid.x() - h, cr.bottom()), QPointF(mid.x() + h, cr.bottom()))
            p.drawLine(QPointF(cr.left(), mid.y() - h), QPointF(cr.left(), mid.y() + h))
            p.drawLine(QPointF(cr.right(), mid.y() - h), QPointF(cr.right(), mid.y() + h))

        w, h, _, _ = self.crop_pixels() or (self.src_w, self.src_h, 0, 0)
        p.setPen(QColor("white"))
        p.drawText(cr.adjusted(6, 4, -6, -4), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop,
                   f"{w}×{h}")

    # -- mouse
    def _hit(self, pos: QPointF) -> str | None:
        if not self.crop_mode:
            return None
        r, t = self.crop_rect_px(), self.HANDLE
        corners = {"tl": r.topLeft(), "tr": r.topRight(), "bl": r.bottomLeft(), "br": r.bottomRight()}
        for key, pt in corners.items():
            if abs(pos.x() - pt.x()) <= t and abs(pos.y() - pt.y()) <= t:
                return key
        if self.aspect is None:
            if r.top() < pos.y() < r.bottom():
                if abs(pos.x() - r.left()) <= t:
                    return "l"
                if abs(pos.x() - r.right()) <= t:
                    return "r"
            if r.left() < pos.x() < r.right():
                if abs(pos.y() - r.top()) <= t:
                    return "t"
                if abs(pos.y() - r.bottom()) <= t:
                    return "b"
        if r.contains(pos):
            return "move"
        return None

    def mousePressEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton:
            return
        self._drag = self._hit(event.position())
        self._press = event.position()
        self._orig = QRectF(self.crop)

    def mouseReleaseEvent(self, event):
        self._drag = None

    def mouseMoveEvent(self, event):
        pos = event.position()
        if self._drag is None:
            self.setCursor(self.CURSORS.get(self._hit(pos), Qt.CursorShape.ArrowCursor))
            return
        fr, o, d = self.frame_rect(), self._orig, self._drag
        nx = (pos.x() - fr.x()) / fr.width()
        ny = (pos.y() - fr.y()) / fr.height()
        if d == "move":
            dx = (pos.x() - self._press.x()) / fr.width()
            dy = (pos.y() - self._press.y()) / fr.height()
            x = clamp(o.x() + dx, 0, 1 - o.width())
            y = clamp(o.y() + dy, 0, 1 - o.height())
            self.crop = QRectF(x, y, o.width(), o.height())
        elif self.aspect is None:
            left, top, right, bottom = o.left(), o.top(), o.right(), o.bottom()
            if "l" in d:
                left = clamp(nx, 0, right - self.MIN_SIZE)
            if "r" in d:
                right = clamp(nx, left + self.MIN_SIZE, 1)
            if "t" in d:
                top = clamp(ny, 0, bottom - self.MIN_SIZE)
            if "b" in d:
                bottom = clamp(ny, top + self.MIN_SIZE, 1)
            self.crop = QRectF(QPointF(left, top), QPointF(right, bottom))
        else:
            self.crop = self._resize_locked(d, nx, ny)
        self.crop_changed.emit()
        self.update()

    def _resize_locked(self, corner: str, nx: float, ny: float) -> QRectF:
        o = self._orig
        ax = o.right() if "l" in corner else o.left()     # anchored opposite corner
        ay = o.bottom() if "t" in corner else o.top()
        sx = -1 if "l" in corner else 1
        sy = -1 if "t" in corner else 1
        ratio = self.aspect * self.src_h / self.src_w     # normalised width / height
        w = max((nx - ax) * sx, (ny - ay) * sy * ratio, self.MIN_SIZE)
        max_w = ax if sx < 0 else 1 - ax
        max_h = ay if sy < 0 else 1 - ay
        w = min(w, max_w, max_h * ratio)
        h = w / ratio
        return QRectF(ax - w if sx < 0 else ax, ay - h if sy < 0 else ay, w, h)


# ---------------------------------------------------------------- timeline with trim + slow-mo handles

class Timeline(QWidget):
    seek_requested = Signal(int)
    range_changed = Signal()
    MARGIN = 20
    STRIP_TOP, STRIP_H = 8, 56
    BAND_GAP, BAND_H = 10, 18
    GRIP = 13
    THUMBS = 10

    def __init__(self, duration_ms: int):
        super().__init__()
        self.duration = max(1, duration_ms)
        self.start, self.end, self.pos = 0, self.duration, 0
        self.slow_enabled = False
        self.slow_start = self.slow_end = 0
        self.slow_label = ""
        self.thumbs: dict[int, QImage] = {}
        self._drag: str | None = None
        self._drag_offset = 0
        self.setMouseTracking(True)
        self.setFixedHeight(self.STRIP_TOP + self.STRIP_H + self.BAND_GAP + self.BAND_H + 8)

    # -- geometry
    def track(self) -> QRectF:
        return QRectF(self.MARGIN, self.STRIP_TOP, self.width() - 2 * self.MARGIN, self.STRIP_H)

    def band(self) -> QRectF:
        tr = self.track()
        return QRectF(tr.left(), tr.bottom() + self.BAND_GAP, tr.width(), self.BAND_H)

    def x_of(self, ms: float) -> float:
        tr = self.track()
        return tr.left() + ms / self.duration * tr.width()

    def ms_of(self, x: float) -> float:
        tr = self.track()
        return clamp((x - tr.left()) / tr.width(), 0, 1) * self.duration

    # -- state
    def set_pos(self, ms: int):
        if ms != self.pos:
            self.pos = ms
            self.update()

    def set_thumb(self, index: int, image: QImage):
        self.thumbs[index] = image
        self.update()

    def set_slow_enabled(self, on: bool):
        self.slow_enabled = on
        if on and self.slow_end - self.slow_start < MIN_CLIP_MS:
            third = (self.end - self.start) / 3
            self.slow_start, self.slow_end = int(self.start + third), int(self.end - third)
        self._fit_slow()
        self.update()

    def slow_whole_clip(self):
        self.slow_start, self.slow_end = self.start, self.end
        self.range_changed.emit()
        self.update()

    def set_trim(self, start: int | None = None, end: int | None = None):
        if start is not None:
            self.start = int(clamp(start, 0, self.end - MIN_CLIP_MS))
        if end is not None:
            self.end = int(clamp(end, self.start + MIN_CLIP_MS, self.duration))
        self._fit_slow()
        self.range_changed.emit()
        self.update()

    def _fit_slow(self):
        self.slow_start = int(clamp(self.slow_start, self.start, self.end))
        self.slow_end = int(clamp(self.slow_end, self.start, self.end))
        if self.slow_end - self.slow_start < MIN_CLIP_MS:
            self.slow_start, self.slow_end = self.start, self.end

    # -- painting
    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        tr = self.track()
        p.fillRect(tr, QColor("#2a2a2a"))

        cell_w = tr.width() / self.THUMBS
        for i, img in self.thumbs.items():
            cell = QRectF(tr.left() + i * cell_w, tr.top(), cell_w, tr.height())
            # centre-crop the thumbnail to the cell's shape
            iw, ih = img.width(), img.height()
            cell_ratio = cell.width() / cell.height()
            if iw / ih > cell_ratio:
                sw = ih * cell_ratio
                source = QRectF((iw - sw) / 2, 0, sw, ih)
            else:
                sh = iw / cell_ratio
                source = QRectF(0, (ih - sh) / 2, iw, sh)
            p.drawImage(cell, img, source)

        xs, xe = self.x_of(self.start), self.x_of(self.end)
        dim = QColor(0, 0, 0, 175)
        p.fillRect(QRectF(tr.left(), tr.top(), xs - tr.left(), tr.height()), dim)
        p.fillRect(QRectF(xe, tr.top(), tr.right() - xe, tr.height()), dim)

        p.setPen(QPen(ACCENT, 3))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRect(QRectF(xs, tr.top() + 1.5, xe - xs, tr.height() - 3))
        for x, left in ((xs, True), (xe, False)):
            grip = QRectF(x - self.GRIP if left else x, tr.top() - 2, self.GRIP, tr.height() + 4)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(ACCENT)
            p.drawRoundedRect(grip, 4, 4)
            p.setPen(QPen(QColor("#6b5000"), 2))
            c = grip.center()
            p.drawLine(QPointF(c.x(), c.y() - 9), QPointF(c.x(), c.y() + 9))

        if self.slow_enabled:
            b = self.band()
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor("#2e2e2e"))
            p.drawRoundedRect(QRectF(xs, b.top(), xe - xs, b.height()), 5, 5)
            s0, s1 = self.x_of(self.slow_start), self.x_of(self.slow_end)
            rng = QRectF(s0, b.top(), max(2.0, s1 - s0), b.height())
            p.setBrush(SLOW)
            p.drawRoundedRect(rng, 5, 5)
            p.setBrush(QColor("white"))
            for x in (s0, s1):
                p.drawRoundedRect(QRectF(x - 3, b.top() - 2, 6, b.height() + 4), 3, 3)
            if rng.width() > 50:
                p.setPen(QColor("white"))
                p.drawText(rng, Qt.AlignmentFlag.AlignCenter, f"slow {self.slow_label}")

        x = self.x_of(self.pos)
        p.setPen(QPen(QColor("white"), 2))
        p.drawLine(QPointF(x, tr.top() - 5), QPointF(x, tr.bottom() + 5))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor("white"))
        p.drawEllipse(QPointF(x, tr.top() - 5), 4.5, 4.5)

    # -- mouse
    def _hit(self, pos: QPointF) -> str | None:
        tr = self.track()
        xs, xe = self.x_of(self.start), self.x_of(self.end)
        if tr.top() - 6 <= pos.y() <= tr.bottom() + 6:
            if xs - self.GRIP - 3 <= pos.x() <= xs + 3:
                return "start"
            if xe - 3 <= pos.x() <= xe + self.GRIP + 3:
                return "end"
            return "scrub"
        if self.slow_enabled:
            b = self.band()
            if b.top() - 5 <= pos.y() <= b.bottom() + 5:
                s0, s1 = self.x_of(self.slow_start), self.x_of(self.slow_end)
                if abs(pos.x() - s0) <= 8:
                    return "slow_start"
                if abs(pos.x() - s1) <= 8:
                    return "slow_end"
                if s0 < pos.x() < s1:
                    return "slow_move"
        return None

    def mousePressEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton:
            return
        self._drag = self._hit(event.position())
        # keep the grab point under the cursor so a handle doesn't jump when picked up
        anchor = {"start": self.start, "end": self.end, "slow_start": self.slow_start,
                  "slow_end": self.slow_end, "slow_move": self.slow_start}.get(self._drag)
        self._drag_offset = self.ms_of(event.position().x()) - anchor if anchor is not None else 0
        if self._drag == "scrub":
            self.mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._drag = None

    def mouseMoveEvent(self, event):
        pos = event.position()
        d = self._drag
        if d is None:
            cursor = {"start": Qt.CursorShape.SizeHorCursor, "end": Qt.CursorShape.SizeHorCursor,
                      "slow_start": Qt.CursorShape.SizeHorCursor, "slow_end": Qt.CursorShape.SizeHorCursor,
                      "slow_move": Qt.CursorShape.OpenHandCursor,
                      "scrub": Qt.CursorShape.PointingHandCursor}.get(self._hit(pos), Qt.CursorShape.ArrowCursor)
            self.setCursor(cursor)
            return
        ms = self.ms_of(pos.x()) - self._drag_offset
        if d == "scrub":
            self.seek_requested.emit(int(clamp(ms, 0, self.duration)))
            return
        if d == "start":
            self.set_trim(start=ms)
            self.seek_requested.emit(self.start)
        elif d == "end":
            self.set_trim(end=ms)
            self.seek_requested.emit(self.end)
        elif d == "slow_start":
            self.slow_start = int(clamp(ms, self.start, self.slow_end - MIN_CLIP_MS))
            self.seek_requested.emit(self.slow_start)
        elif d == "slow_end":
            self.slow_end = int(clamp(ms, self.slow_start + MIN_CLIP_MS, self.end))
            self.seek_requested.emit(self.slow_end)
        elif d == "slow_move":
            length = self.slow_end - self.slow_start
            self.slow_start = int(clamp(ms, self.start, self.end - length))
            self.slow_end = self.slow_start + length
            self.seek_requested.emit(self.slow_start)
        self.range_changed.emit()
        self.update()


# ---------------------------------------------------------------- main window

class EditorWindow(QMainWindow):
    def __init__(self, path: str, start_ms: int, info: MediaInfo, ffmpeg: str):
        super().__init__()
        path = os.path.normpath(path)    # libvlc refuses paths with forward slashes
        self.path, self.info, self.ffmpeg = path, info, ffmpeg
        self.setWindowTitle(f"Edit Video - {Path(path).name}")
        self.pos = start_ms
        self._pending: tuple[int, bool] | None = None    # (seek ms, keep playing) once VLC is running
        self._rate = 1.0
        self._loop = True     # loop the clip; off when playing from outside it
        self._muted = False
        self._export: QProcess | None = None

        # -- player
        self.instance = vlc.Instance(["--quiet", "--no-video-title-show", "--no-sub-autodetect-file", "--no-osd"])
        self.player = self.instance.media_player_new()
        scale = min(1.0, PREVIEW_MAX / max(info.width, info.height))
        pw = max(2, int(info.width * scale) // 2 * 2)
        ph = max(2, int(info.height * scale) // 2 * 2)
        self.sink = FrameSink(self.player, pw, ph)
        self.sink.frame_ready.connect(self._on_frame)
        self.player.set_media(self.instance.media_new_path(path))

        # -- widgets
        self.view = VideoView(info.width, info.height)
        self.view.crop_changed.connect(self._update_labels)
        self.timeline = Timeline(info.duration_ms)
        self.timeline.seek_requested.connect(self.seek)
        self.timeline.range_changed.connect(self._update_labels)

        self.play_btn = self._button("▶", self.toggle_play, name="play")
        self.time_label = QLabel()
        self.time_label.setObjectName("muted")

        self.crop_btn = self._button("Crop", self._toggle_crop, checkable=True)
        self.aspect_combo = QComboBox()
        for label, value in (("Free", None), ("Original", info.width / info.height), ("16:9", 16 / 9),
                             ("9:16", 9 / 16), ("1:1", 1.0), ("4:3", 4 / 3), ("3:4", 3 / 4)):
            self.aspect_combo.addItem(label, value)
        self.aspect_combo.currentIndexChanged.connect(
            lambda: self.view.set_aspect(self.aspect_combo.currentData()))
        self.reset_crop_btn = self._button("Reset", self._reset_crop)

        self.slow_btn = self._button("Slow-mo", self._toggle_slow, checkable=True, name="slow")
        self.speed_combo = QComboBox()
        for label, value in (("½×", 0.5), ("¼×", 0.25), ("⅛×", 0.125)):
            self.speed_combo.addItem(label, value)
        self.speed_combo.currentIndexChanged.connect(self._update_labels)
        self.whole_btn = self._button("Whole clip", self.timeline.slow_whole_clip)
        self.audio_combo = QComboBox()
        self.audio_combo.addItem("Mute slow part", True)
        self.audio_combo.addItem("Slow the audio too", False)
        self.audio_combo.setVisible(info.has_audio)
        self.smooth_chk = QCheckBox("Smooth motion (slower to save)")
        self.smooth_chk.setToolTip("Generates in-between frames so slow-mo isn't choppy.\n"
                                   "Takes much longer to save, especially for 4K.")

        self.info_label = QLabel()
        self.info_label.setObjectName("muted")
        self.save_btn = self._button("Save", self.save, name="save")

        for w in (self.aspect_combo, self.speed_combo, self.audio_combo, self.smooth_chk):
            w.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        top = QHBoxLayout()
        top.addWidget(self.play_btn)
        top.addWidget(self.time_label)
        top.addSpacing(12)
        self.start_here_btn = self._button("⇤ Start here", self.start_here)
        self.start_here_btn.setToolTip("Start the clip at the current frame (I)")
        self.end_here_btn = self._button("End here ⇥", self.end_here)
        self.end_here_btn.setToolTip("End the clip at the current frame (O)")
        top.addWidget(self.start_here_btn)
        top.addWidget(self.end_here_btn)
        top.addStretch(1)
        self.crop_tools = [self.aspect_combo, self.reset_crop_btn]
        self.slow_tools = [self.speed_combo, self.whole_btn, self.audio_combo, self.smooth_chk]
        for w in [self.crop_btn, *self.crop_tools, self.slow_btn, *self.slow_tools]:
            top.addWidget(w)

        bottom = QHBoxLayout()
        bottom.addWidget(self.info_label)
        bottom.addStretch(1)
        hint = QLabel("Space play/pause · ←/→ seek · I / O start / end here")
        hint.setObjectName("muted")
        bottom.addWidget(hint)
        bottom.addSpacing(16)
        bottom.addWidget(self.save_btn)

        root = QWidget()
        layout = QVBoxLayout(root)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.addWidget(self.view, 1)
        layout.addLayout(top)
        layout.addWidget(self.timeline)
        layout.addLayout(bottom)
        self.setCentralWidget(root)
        self._set_tools_visible()

        shortcuts = {
            "Space": self.toggle_play,
            "Left": lambda: self.step(-1000), "Right": lambda: self.step(1000),
            "Shift+Left": lambda: self.step(-100), "Shift+Right": lambda: self.step(100),
            "I": self.start_here,
            "O": self.end_here,
            "Ctrl+S": self.save,
        }
        for key, slot in shortcuts.items():
            QShortcut(QKeySequence(key), self, slot, context=Qt.ShortcutContext.ApplicationShortcut)

        self.thumbs = ThumbLoader()
        self.thumbs.thumb_ready.connect(self.timeline.set_thumb)
        self.thumbs.start(ffmpeg, path, info.duration_ms, Timeline.THUMBS)

        self._update_labels()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(30)
        self._restart(start_ms, play=False)

    def _button(self, text, slot, checkable=False, name=None) -> QPushButton:
        b = QPushButton(text)
        b.setCheckable(checkable)
        b.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        if name:
            b.setObjectName(name)
        b.clicked.connect(slot)
        return b

    # -- playback
    def _set_mute(self, mute: bool):
        if mute != self._muted:
            self.player.audio_set_mute(mute)
            self._muted = mute

    def _restart(self, ms: int, play: bool):
        """(Re)start VLC, then seek once it is running (VLC can't seek a stopped/ended player)."""
        self.player.stop()
        self._muted = None
        self._set_mute(True)
        self.player.play()
        self._pending = (int(ms), play)

    def _on_frame(self):
        image = self.sink.take_image()
        if image is not None:
            self.view.set_image(image)

    def _tick(self):
        state = self.player.get_state()
        if self._pending is not None:
            if state in (vlc.State.Playing, vlc.State.Paused):
                ms, play = self._pending
                self._pending = None
                self.player.set_time(ms)
                self.pos = ms
                if not play:
                    self.player.set_pause(1)
                self._set_mute(False)
            elif state == vlc.State.Error:
                self._pending = None
                QMessageBox.critical(self, "VLC Editor", "VLC could not play this file.")
            return

        tl = self.timeline
        if state == vlc.State.Ended:
            self._loop = True
            self._restart(tl.start, play=True)    # loop the trimmed clip
            return
        playing = self.player.is_playing()
        if playing:
            t = self.player.get_time()
            if t >= 0:
                self.pos = t
            if self._loop and self.pos >= tl.end - 30:
                self.seek(tl.start)
            self._update_slow_preview()
        tl.set_pos(self.pos)
        self.play_btn.setText("❚❚" if playing else "▶")
        self.time_label.setText(f"{fmt_time(self.pos)} / {fmt_time(self.info.duration_ms)}")

    def _update_slow_preview(self):
        tl = self.timeline
        inside = tl.slow_enabled and tl.slow_start <= self.pos < tl.slow_end
        rate = self.speed_combo.currentData() if inside else 1.0
        if rate != self._rate:
            self.player.set_rate(rate)
            self._rate = rate
        self._set_mute(inside and self.audio_combo.currentData())

    def seek(self, ms: int):
        ms = int(ms)
        if self._pending is not None:
            self._pending = (ms, self._pending[1])
        elif self.player.get_state() in (vlc.State.Ended, vlc.State.Stopped):
            self._restart(ms, play=False)
        else:
            self.player.set_time(ms)
        self.pos = ms
        self.timeline.set_pos(ms)

    def start_here(self):
        tl = self.timeline
        if self.pos > tl.end - MIN_CLIP_MS:
            tl.set_trim(end=tl.duration)    # new start is past the old end: release the end
        tl.set_trim(start=self.pos)

    def end_here(self):
        tl = self.timeline
        if self.pos < tl.start + MIN_CLIP_MS:
            tl.set_trim(start=0)            # new end is before the old start: release the start
        tl.set_trim(end=self.pos)
        if self.player.is_playing():
            self.player.set_pause(1)        # otherwise it would loop straight back to the start

    def step(self, delta: int):
        self.seek(clamp(self.pos + delta, 0, self.timeline.duration))

    def toggle_play(self):
        if self._pending is not None:
            return
        if self.player.is_playing():
            self.player.set_pause(1)
            return
        tl = self.timeline
        target = self.pos
        if abs(self.pos - tl.end) <= 50 or self.pos >= tl.duration - 50:
            target = tl.start    # sitting on the clip's end: replay the clip
        # play the clip on a loop, unless starting outside it (e.g. hunting for a new start/end)
        self._loop = tl.start <= target < tl.end
        if self.player.get_state() in (vlc.State.Ended, vlc.State.Stopped):
            self._restart(target, play=True)
            return
        if target != self.pos:
            self.seek(target)
        self.player.set_pause(0)

    # -- tools
    def _set_tools_visible(self):
        for w in self.crop_tools:
            w.setVisible(self.crop_btn.isChecked())
        for w in self.slow_tools:
            w.setVisible(self.slow_btn.isChecked() and (w is not self.audio_combo or self.info.has_audio))

    def _toggle_crop(self):
        self.view.set_crop_mode(self.crop_btn.isChecked())
        self._set_tools_visible()

    def _reset_crop(self):
        self.aspect_combo.blockSignals(True)
        self.aspect_combo.setCurrentIndex(0)
        self.aspect_combo.blockSignals(False)
        self.view.reset_crop()

    def _toggle_slow(self):
        self.timeline.set_slow_enabled(self.slow_btn.isChecked())
        self._set_tools_visible()
        self._update_labels()

    def current_spec(self) -> EditSpec:
        tl = self.timeline
        slow = (tl.slow_start, tl.slow_end) if tl.slow_enabled else None
        return EditSpec(tl.start, tl.end, self.view.crop_pixels(), slow,
                        self.speed_combo.currentData(), bool(self.audio_combo.currentData()),
                        self.smooth_chk.isChecked())

    def _update_labels(self):
        self.timeline.slow_label = self.speed_combo.currentText()
        self.timeline.update()
        spec = self.current_spec()
        text = f"Clip {fmt_time(spec.end_ms - spec.start_ms)}"
        if spec.slow:
            text += f"  →  {fmt_time(spec.output_ms())} with slow-mo"
        w, h = spec.crop[:2] if spec.crop else (self.info.width, self.info.height)
        text += f"   ·   {w}×{h}" + ("  (cropped)" if spec.crop else "")
        self.info_label.setText(text)

    # -- export
    def save(self):
        if self._export is not None:
            return
        spec = self.current_spec()
        dst, _ = QFileDialog.getSaveFileName(self, "Save edited video", unique_output_path(self.path),
                                             "MP4 video (*.mp4)")
        if not dst:
            return
        if os.path.normcase(os.path.abspath(dst)) == os.path.normcase(os.path.abspath(self.path)):
            QMessageBox.warning(self, "VLC Editor", "Choose a different name - the original can't be overwritten.")
            return
        if self.player.is_playing():
            self.player.set_pause(1)

        total_ms = max(1, spec.output_ms())
        dialog = QProgressDialog("Saving…", "Cancel", 0, 1000, self)
        dialog.setWindowTitle("VLC Editor")
        dialog.setWindowModality(Qt.WindowModality.WindowModal)
        dialog.setMinimumDuration(0)
        dialog.setAutoClose(False)
        dialog.setAutoReset(False)
        dialog.setValue(0)

        proc = QProcess(self)
        self._export = proc
        cancelled = []

        def on_output():
            for line in bytes(proc.readAllStandardOutput()).decode(errors="replace").splitlines():
                key, _, value = line.partition("=")
                if key == "out_time_us" and value.strip().isdigit():
                    done = int(value) / 1000
                    dialog.setValue(int(clamp(done / total_ms, 0, 1) * 1000))
                    dialog.setLabelText(f"Saving…  {fmt_time(done)} / {fmt_time(total_ms)}")

        def on_cancel():
            cancelled.append(True)
            proc.kill()

        def on_finished(code, status):
            errors = bytes(proc.readAllStandardError()).decode(errors="replace").strip()
            dialog.canceled.disconnect()
            dialog.hide()
            dialog.deleteLater()
            self._export = None
            if cancelled:
                try:
                    os.remove(dst)
                except OSError:
                    pass
            elif code == 0 and status == QProcess.ExitStatus.NormalExit:
                self._saved(dst, spec)
            else:
                QMessageBox.critical(self, "VLC Editor", "Saving failed.\n\n" + errors[-1500:])

        proc.readyReadStandardOutput.connect(on_output)
        proc.finished.connect(on_finished)
        dialog.canceled.connect(on_cancel)
        proc.start(self.ffmpeg, build_ffmpeg_args(spec, self.info, self.path, dst))

    def _saved(self, dst: str, spec: EditSpec):
        box = QMessageBox(self)
        box.setWindowTitle("Saved")
        box.setText(f"Saved {Path(dst).name}  ({fmt_time(spec.output_ms())})")
        open_btn = box.addButton("Open in VLC", QMessageBox.ButtonRole.AcceptRole)
        folder_btn = box.addButton("Show in folder", QMessageBox.ButtonRole.ActionRole)
        box.addButton("Close", QMessageBox.ButtonRole.RejectRole)
        box.exec()
        if box.clickedButton() is open_btn:
            vlc_exe = find_tool("vlc")
            if vlc_exe:
                subprocess.Popen([vlc_exe, dst])
            else:
                os.startfile(dst)
        elif box.clickedButton() is folder_btn:
            subprocess.Popen(f'explorer /select,"{dst}"')

    def closeEvent(self, event):
        if self._export is not None:
            self._export.kill()
            self._export.waitForFinished(3000)
        self.timer.stop()
        self.player.stop()
        self.player.release()
        self.instance.release()
        super().closeEvent(event)


# ---------------------------------------------------------------- entry point

def _excepthook(exc_type, exc, tb):
    text = "".join(traceback.format_exception(exc_type, exc, tb))
    try:
        ERROR_LOG.write_text(text, encoding="utf-8")
    except OSError:
        pass
    QMessageBox.critical(None, "VLC Editor error", text[-2000:])


def _fail(message: str) -> int:
    QMessageBox.critical(None, "VLC Editor", message)
    return 1


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("VLC Editor")
    app.setStyleSheet(STYLE)
    sys.excepthook = _excepthook

    try:
        path, start_ms = parse_args(sys.argv[1:])
    except ValueError as e:
        return _fail(str(e))
    ffmpeg, ffprobe = find_tool("ffmpeg"), find_tool("ffprobe")
    if not (ffmpeg and ffprobe):
        return _fail("ffmpeg was not found. Run install.ps1 again, or add ffmpeg to config.json.")
    if not path:
        path, _ = QFileDialog.getOpenFileName(
            None, "Choose a video to edit", "",
            "Videos (*.mp4 *.mov *.mkv *.avi *.webm *.m4v *.3gp *.wmv *.mts);;All files (*)")
        if not path:
            return 0
    if not os.path.isfile(path):
        return _fail(f"File not found:\n{path}")
    try:
        info = probe(ffprobe, path)
    except Exception as e:  # noqa: BLE001 - anything ffprobe chokes on is reported the same way
        return _fail(f"Couldn't read this video:\n{e}")

    window = EditorWindow(path, min(start_ms, max(0, info.duration_ms - MIN_CLIP_MS)), info, ffmpeg)
    window.resize(1180, 800)
    window.show()
    window.raise_()
    window.activateWindow()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
