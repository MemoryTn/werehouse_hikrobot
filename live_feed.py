# -*- coding: utf-8 -*-
"""
live_feed.py – Dual Live Feed (Shared Memory + RTSP)
=====================================
• SC2000 → ดึงภาพจาก Shared Memory ที่กล้องหลักสร้างไว้ให้ (ไม่บล็อกกันเอง)
• Hikvision → ใช้ OpenCV RTSP แบบ Thread แยก (ปลอดภัย ลื่นไหล ไม่ทำให้ GUI ค้างเวลาสายหลุด)
"""

import os
import time
import threading
import numpy as np
import cv2
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtGui import QImage
import config
from config import HIKVISION_RTSP_URL

# ปรับ OpenCV ไม่ให้ Block นานเวลา Timeout
os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp|analyzeduration;1000000|probesize;1000000"

# ── helpers ───────────────────────────────────────────────────────────────────

def _bgr_to_qimage(frame: np.ndarray) -> QImage:
    h, w, _ = frame.shape
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    return QImage(rgb.tobytes(), w, h, w * 3, QImage.Format_RGB888).copy()

def _sim_frame(label: str, color_bgr: tuple, tick: int) -> QImage:
    w, h = 960, 540
    arr = np.zeros((h, w, 3), dtype=np.uint8)
    b, g, r = color_bgr
    shift = (tick * 3) % 50
    arr[:, :] = [min(255, b + shift), min(255, g + shift), min(255, r + shift)]
    line = (tick * 6) % h
    arr[line:min(line + 5, h - 1), :] = [180, 180, 180]
    cv2.putText(arr, f"{label} - NO SIGNAL", (40, h // 2 - 20),
                cv2.FONT_HERSHEY_SIMPLEX, 1.2, (220, 220, 220), 2, cv2.LINE_AA)
    cv2.putText(arr, "Waiting for stream...", (40, h // 2 + 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (160, 160, 160), 1, cv2.LINE_AA)
    rgb = cv2.cvtColor(arr, cv2.COLOR_BGR2RGB)
    return QImage(rgb.tobytes(), w, h, w * 3, QImage.Format_RGB888).copy()

# ── RTSP Reader (Hikvision) รัน Background เพื่อกันค้าง ────────────────────────
class _RtspReader:
    def __init__(self, url: str, label: str, log_fn):
        self.url = url
        self.label = label
        self.log = log_fn
        self._cap = None
        self._sim = True
        self._fail = 0
        self.current_frame = None
        self.running = False
        self.thread = None
        self.lock = threading.Lock()

    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self._update_loop, daemon=True)
        self.thread.start()

    def _update_loop(self):
        while self.running:
            if self._sim:
                if not self.url:
                    time.sleep(2)
                    continue
                self.log(f"📡 [{self.label}] Connecting RTSP...")
                cap = cv2.VideoCapture(self.url, cv2.CAP_FFMPEG)
                cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                if cap.isOpened():
                    self._cap = cap
                    self._sim = False
                    self._fail = 0
                    self.log(f"✅ [{self.label}] RTSP Connected")
                else:
                    cap.release()
                    time.sleep(5.0)  # รอ 5 วิก่อนต่อใหม่ถ้าไม่ติด
                continue

            if self._cap:
                ret, frame = self._cap.read()
                if ret and frame is not None:
                    self._fail = 0
                    with self.lock:
                        self.current_frame = frame
                else:
                    self._fail += 1
                    if self._fail >= 30:
                        self.log(f"⚠️ [{self.label}] RTSP Stream lost - Reconnecting...")
                        self._cap.release()
                        self._cap = None
                        self._sim = True
                        self._fail = 0
                        with self.lock:
                            self.current_frame = None

    def get_qimage(self) -> QImage:
        """ดึงเฟรมล่าสุดทันที (ไม่บล็อก)"""
        with self.lock:
            if self.current_frame is not None:
                return _bgr_to_qimage(self.current_frame)
        return None

    def close(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=1.0)
        if self._cap:
            self._cap.release()

# ── Thread หลักสำหรับพ่นเฟรมให้ GUI (ไม่บล็อกแล้ว!) ────────────────────────────
class LiveFeedThread(QThread):
    sc2000_frame    = pyqtSignal(QImage)
    hikvision_frame = pyqtSignal(QImage)
    cameras_ready   = pyqtSignal(object)
    log_message     = pyqtSignal(str)

    def __init__(self, num_cams: int = 4, fps_limit: int = 20):
        super().__init__()
        self._fps      = fps_limit
        self._running  = True
        self._paused   = False

    def _log(self, msg): self.log_message.emit(msg)
    def pause(self):     self._paused = True
    def resume(self):    self._paused = False
    def stop(self):
        self._running = False
        self.wait()

    def run(self):
        interval = 1.0 / self._fps
        tick = 0

        # รัน RTSP Reader บน Thread แยก
        hik = _RtspReader(HIKVISION_RTSP_URL, "Hikvision", self._log)
        hik.start()

        self.cameras_ready.emit([])

        while self._running:
            t0 = time.perf_counter()

            if not self._paused:
                # =======================================================
                # 1. โหลดเฟรม SC2000 สดๆ จากหน่วยความจำของ CameraServer 
                # =======================================================
                sc2000_qimg = None
                if hasattr(config, 'SHARED_SC2000_FRAME') and config.SHARED_SC2000_FRAME is not None:
                    try:
                        # 📌 ทำการ Copy ภาพมาก่อน เพื่อไม่ให้กระทบภาพต้นฉบับที่จะเซฟ
                        arr = config.SHARED_SC2000_FRAME.copy()
                        h, w, _ = arr.shape
                        
                        # 📌 วาดเส้น Visual Line (Crosshair) ตรงกลางจอ สีเขียว
                        cx, cy = w // 2, h // 2
                        cv2.line(arr, (690, h-600), (690, h), (255, 255, 0), 5)  # เส้นแนวตั้ง1
                        cv2.line(arr, (1050, h-600), (1050, h), (255, 255, 0), 5)  # เส้นแนวตั้ง2
                        
                        # (ทางเลือก) ถ้าอยากวาดเป็นกรอบสี่เหลี่ยม ROI แทน ให้เอา # ด้านล่างออก
                        # cv2.rectangle(arr, (cx - 200, cy - 150), (cx + 200, cy + 150), (0, 255, 255), 2)

                        sc2000_qimg = QImage(arr.data, w, h, w * 3, QImage.Format_RGB888).copy()
                    except Exception:
                        pass

                if sc2000_qimg is not None:
                    self.sc2000_frame.emit(sc2000_qimg)
                else:
                    self.sc2000_frame.emit(_sim_frame("SC2000 (192.168.1.13)", (60, 30, 30), tick))

                # =======================================================
                # 2. โหลดเฟรม Hikvision จาก Background Thread (แบบไม่บล็อก)
                # =======================================================
                hik_qimg = hik.get_qimage()
                if hik_qimg is not None:
                    self.hikvision_frame.emit(hik_qimg)
                else:
                    self.hikvision_frame.emit(_sim_frame("Hikvision CCTV", (30, 50, 60), tick))

            tick += 1
            elapsed = time.perf_counter() - t0
            sleep_t = interval - elapsed
            if sleep_t > 0:
                time.sleep(sleep_t)

        hik.close()
        self._log("🛑 [LiveFeed] Stopped")