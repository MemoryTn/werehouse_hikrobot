# -*- coding: utf-8 -*-
import cv2
import numpy as np
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtGui import QImage
from config import COLORS
import time

class RTSPThread(QThread):
    """Thread สำหรับดึง RTSP stream จากกล้อง"""
    frame_received = pyqtSignal(QImage)
    status_changed = pyqtSignal(str, str, str)  # (text, color, border_color)
    log_message = pyqtSignal(str)
    
    def __init__(self, rtsp_url, camera_name="Camera"):
        super().__init__()
        self.rtsp_url = rtsp_url
        self.camera_name = camera_name
        self.running = True
        self.cap = None
        
    def run(self):
        retry_count = 0
        max_retries = 5
        
        while self.running:
            try:
                # เชื่อมต่อ RTSP
                self.log_message.emit(f"🔗 Connecting to {self.camera_name}...")
                self.status_changed.emit("CONNECTING", COLORS['warning'], COLORS['warning'])
                
                self.cap = cv2.VideoCapture(self.rtsp_url)
                
                # ตั้งค่า timeout และ buffer
                self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                
                if not self.cap.isOpened():
                    raise Exception(f"Cannot open RTSP stream: {self.rtsp_url}")
                
                self.log_message.emit(f"✅ {self.camera_name} Connected!")
                self.status_changed.emit("LIVE", COLORS['success'], COLORS['success'])
                retry_count = 0
                
                # ลูปอ่านภาพ
                while self.running:
                    ret, frame = self.cap.read()
                    
                    if not ret:
                        self.log_message.emit(f"⚠️ {self.camera_name}: Lost connection")
                        break
                    
                    # แปลง BGR -> RGB
                    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    h, w, ch = rgb_frame.shape
                    bytes_per_line = ch * w
                    
                    # สร้าง QImage - ต้อง copy data เพื่อป้องกัน crash
                    rgb_copy = rgb_frame.copy()
                    qt_image = QImage(rgb_copy.data, w, h, bytes_per_line, QImage.Format_RGB888).copy()
                    self.frame_received.emit(qt_image)
                    
                    # ลดภาระ CPU
                    time.sleep(0.033)  # ~30 FPS
                    
            except Exception as e:
                self.log_message.emit(f"❌ {self.camera_name} Error: {str(e)}")
                self.status_changed.emit("ERROR", COLORS['error'], COLORS['error'])
                
                retry_count += 1
                if retry_count >= max_retries:
                    self.log_message.emit(f"❌ {self.camera_name}: Max retries reached")
                    break
                
                # รอก่อน retry
                time.sleep(3)
                
            finally:
                if self.cap:
                    self.cap.release()
                    self.cap = None
        
        self.status_changed.emit("OFFLINE", COLORS['text_dim'], COLORS['border'])
    
    def stop(self):
        """หยุด thread"""
        self.running = False
        if self.cap:
            self.cap.release()
        self.wait()


class SimulatedRTSPThread(QThread):
    """Thread จำลอง RTSP สำหรับ testing (ไม่มีกล้องจริง)"""
    frame_received = pyqtSignal(QImage)
    status_changed = pyqtSignal(str, str, str)
    log_message = pyqtSignal(str)
    
    def __init__(self, camera_name="Sim Camera"):
        super().__init__()
        self.camera_name = camera_name
        self.running = True
        self.frame_count = 0
        
    def run(self):
        self.log_message.emit(f"🔧 {self.camera_name}: Simulation Mode")
        self.status_changed.emit("SIMULATION", COLORS['processing'], COLORS['processing'])
        
        while self.running:
            try:
                # สร้างภาพจำลอง
                img = np.zeros((480, 640, 3), dtype=np.uint8)
                
                # พื้นหลังสีเทา
                img[:] = (40, 40, 40)
                
                # เพิ่ม noise
                noise = np.random.randint(0, 30, (480, 640, 3), dtype=np.uint8)
                img = cv2.add(img, noise)
                
                # ข้อความ
                text = f"{self.camera_name} - SIMULATION"
                cv2.putText(img, text, (50, 240), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 0), 2)
                
                # Frame counter
                frame_text = f"Frame: {self.frame_count}"
                cv2.putText(img, frame_text, (50, 280), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 1)
                
                self.frame_count += 1
                
                # แปลงเป็น QImage - copy เพื่อป้องกัน crash
                h, w, ch = img.shape
                img_copy = img.copy()
                qt_image = QImage(img_copy.data, w, h, ch * w, QImage.Format_RGB888).copy()
                self.frame_received.emit(qt_image)
                
                time.sleep(0.033)  # ~30 FPS
            except Exception as e:
                self.log_message.emit(f"❌ {self.camera_name} Simulation Error: {str(e)}")
                time.sleep(0.1)
    
    def stop(self):
        self.running = False
        self.wait()