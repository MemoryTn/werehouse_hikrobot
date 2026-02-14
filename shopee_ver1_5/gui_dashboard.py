# -*- coding: utf-8 -*-
import sys
import json
import base64
import cv2
import socket
import threading
import numpy as np
from PyQt5.QtWidgets import *
from PyQt5.QtGui import QImage, QPixmap, QFont, QColor
from PyQt5.QtCore import Qt, pyqtSignal, QThread, QObject, QTimer
import config

# ================= RTSP WORKER (Integrated) =================
class RTSPWorker(QThread):
    change_pixmap_signal = pyqtSignal(np.ndarray)

    def __init__(self, url):
        super().__init__()
        self.url = url
        self.running = True

    def run(self):
        cap = cv2.VideoCapture(self.url)
        while self.running:
            ret, frame = cap.read()
            if ret:
                self.change_pixmap_signal.emit(frame)
            else:
                time.sleep(1) # Reconnect delay
                cap = cv2.VideoCapture(self.url)
        cap.release()

    def stop(self):
        self.running = False
        self.wait()

# ================= BACKEND LISTENER =================
class BackendListener(QThread):
    data_signal = pyqtSignal(dict)
    
    def run(self):
        while True:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.connect(("127.0.0.1", config.GUI_BROADCAST_PORT))
                print("✅ GUI: Connected to Backend")
                
                buffer = ""
                while True:
                    data = sock.recv(4096)
                    if not data: break
                    buffer += data.decode('utf-8', errors='ignore')
                    
                    while '\n' in buffer:
                        line, buffer = buffer.split('\n', 1)
                        try:
                            msg = json.loads(line)
                            self.data_signal.emit(msg)
                        except: pass
            except:
                time.sleep(2) # Retry connect

# ================= MAIN WINDOW =================
class Dashboard(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Shopee Express Sorting v3.0 (Unified)")
        self.resize(1200, 800)
        self.setStyleSheet("background-color: #1e1e1e; color: white;")
        
        self.setup_ui()
        self.start_threads()

    def setup_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QHBoxLayout(main_widget)

        # Left: Cameras
        cam_layout = QVBoxLayout()
        
        # SC2000 View
        self.lbl_sc2000 = QLabel("SC2000 Waiting...")
        self.lbl_sc2000.setStyleSheet("border: 2px solid #00ff00; background: black;")
        self.lbl_sc2000.setFixedSize(640, 360)
        self.lbl_sc2000.setAlignment(Qt.AlignCenter)
        cam_layout.addWidget(QLabel("📹 SC2000 AI Camera"))
        cam_layout.addWidget(self.lbl_sc2000)
        
        # RTSP View
        self.lbl_rtsp = QLabel("CCTV Connecting...")
        self.lbl_rtsp.setStyleSheet("border: 2px solid #ff9900; background: black;")
        self.lbl_rtsp.setFixedSize(640, 360)
        self.lbl_rtsp.setAlignment(Qt.AlignCenter)
        cam_layout.addWidget(QLabel("📹 Hikvision Overview (RTSP)"))
        cam_layout.addWidget(self.lbl_rtsp)
        
        layout.addLayout(cam_layout)

        # Right: Info & Logs
        info_layout = QVBoxLayout()
        
        self.lbl_order = QLabel("ORDER: --")
        self.lbl_order.setFont(QFont("Arial", 24, QFont.Bold))
        self.lbl_order.setStyleSheet("color: #00ff00; border: 1px solid gray; padding: 10px;")
        
        self.lbl_status = QLabel("STATUS: Standby")
        self.lbl_status.setFont(QFont("Arial", 14))
        
        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setStyleSheet("font-family: Consolas;")
        
        info_layout.addWidget(self.lbl_order)
        info_layout.addWidget(self.lbl_status)
        info_layout.addWidget(QLabel("📝 System Logs:"))
        info_layout.addWidget(self.log_box)
        
        layout.addLayout(info_layout)

    def start_threads(self):
        # 1. Listen to Backend
        self.backend = BackendListener()
        self.backend.data_signal.connect(self.process_backend_data)
        self.backend.start()
        
        # 2. RTSP Stream (ถ้ามีกล้องจริงให้เปิดบรรทัดล่าง)
        # self.rtsp = RTSPWorker(config.RTSP_URL)
        # self.rtsp.change_pixmap_signal.connect(self.update_rtsp_image)
        # self.rtsp.start()

    def process_backend_data(self, msg):
        mtype = msg.get("type")
        data = msg.get("data", {})
        
        if mtype == "live_image":
            self.update_sc2000_image(data["image"])
        elif mtype == "ocr_result":
            text = data["text"]
            conf = data["confidence"]
            color = "#00ff00" if data["is_valid"] else "#ff0000"
            self.log(f"OCR: {text} ({conf:.1%})", color)
        elif mtype == "process_step":
            step = data["step"]
            if step == "new_order":
                self.lbl_order.setText(f"ORDER: {data['order_no']}")
            self.lbl_status.setText(f"Processing: {step}...")
        elif mtype == "job_complete":
            self.lbl_status.setText("✅ COMPLETED")

    def update_sc2000_image(self, b64_str):
        try:
            img_data = base64.b64decode(b64_str)
            qimg = QImage.fromData(img_data)
            self.lbl_sc2000.setPixmap(QPixmap.fromImage(qimg).scaled(640, 360, Qt.KeepAspectRatio))
        except: pass

    def update_rtsp_image(self, cv_img):
        rgb_img = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_img.shape
        bytes_per_line = ch * w
        qimg = QImage(rgb_img.data, w, h, bytes_per_line, QImage.Format_RGB888)
        self.lbl_rtsp.setPixmap(QPixmap.fromImage(qimg).scaled(640, 360, Qt.KeepAspectRatio))

    def log(self, text, color="white"):
        self.log_box.append(f"<span style='color:{color}'>{text}</span>")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = Dashboard()
    window.show()
    sys.exit(app.exec_())