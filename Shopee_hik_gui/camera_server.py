# -*- coding: utf-8 -*-
"""
Hikrobot Multi-Camera Capture Server + GUI Integration
- Receive OCR text via Socket
- Accept ONLY Shopee Order No (14 chars, alphanumeric, not digit-only)
- Capture 1 image per camera per order
- Send images to GUI for display
"""

import socket
import os
import sys
import re
import time
from datetime import datetime
from ctypes import *
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtGui import QImage, QPixmap
from config import COLORS, OUTPUT_DIR

# =============================
# IMPORT HIKROBOT SDK
# =============================
sys.path.append(".")
try:
    from MvImport.MvCameraControl_class import *
    SDK_AVAILABLE = True
except ImportError:
    print("⚠️ Cannot import MvCameraControl_class.py - Using simulation mode")
    SDK_AVAILABLE = False

# =============================
# CONFIG
# =============================
PORT = 5020
TRIGGER_TIMEOUT_MS = 3000
CAPTURE_DELAY_SECONDS = 3  # ⏱️ Delay 3 วินาทีหลังเจอ Order ID

# 🔒 Shopee Order No = 14 chars ONLY
ORDER_PATTERN = re.compile(
    r"Shopee\s*Order\s*No\.?\s*([A-Z0-9]{14})",
    re.I
)

# =============================
# CAMERA MANAGER
# =============================
class HikCameraManager:
    def __init__(self, log_callback=None):
        self.cameras = []
        self.log_callback = log_callback
    
    def log(self, msg):
        if self.log_callback:
            self.log_callback(msg)
        else:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")
    
    def init_cameras(self):
        if not SDK_AVAILABLE:
            self.log("⚠️ SDK not available - Simulation mode")
            return False
        
        device_list = MV_CC_DEVICE_INFO_LIST()
        ret = MvCamera.MV_CC_EnumDevices(
            MV_GIGE_DEVICE | MV_USB_DEVICE,
            device_list
        )
        
        if ret != 0 or device_list.nDeviceNum == 0:
            self.log("⚠️ No camera found")
            return False
        
        self.log(f"📷 Found {device_list.nDeviceNum} camera(s)")
        
        for i in range(device_list.nDeviceNum):
            cam = MvCamera()
            st_dev = device_list.pDeviceInfo[i].contents
            
            if cam.MV_CC_CreateHandle(st_dev) != 0:
                continue
            if cam.MV_CC_OpenDevice(MV_ACCESS_Control, 0) != 0:
                cam.MV_CC_DestroyHandle()
                continue
            
            # GigE packet size
            if st_dev.nTLayerType == MV_GIGE_DEVICE:
                pkt = cam.MV_CC_GetOptimalPacketSize()
                if pkt > 0:
                    cam.MV_CC_SetIntValue("GevSCPSPacketSize", pkt)
            
            # Trigger config
            cam.MV_CC_SetEnumValue("TriggerMode", 1)
            cam.MV_CC_SetEnumValue("TriggerSource", 7)
            cam.MV_CC_SetBoolValue("AcquisitionFrameRateEnable", False)
            
            cam.MV_CC_StartGrabbing()
            self.cameras.append(cam)
        
        self.log(f"✅ Cameras ready: {len(self.cameras)}")
        return True
    
    def capture_all(self, order_no):
        """ถ่ายรูปทุกกล้อง และ return list ของ image paths"""
        folder = os.path.join(OUTPUT_DIR, order_no)
        os.makedirs(folder, exist_ok=True)
        
        image_paths = []
        
        for idx, cam in enumerate(self.cameras):
            cam.MV_CC_SetCommandValue("TriggerSoftware")
            image_path = self._grab_and_save(cam, folder, idx + 1, order_no)
            if image_path:
                image_paths.append(image_path)
        
        return image_paths
    
    def capture_single(self, order_no, camera_index):
        """ถ่ายรูปกล้องเดียว (สำหรับ retake)"""
        if camera_index >= len(self.cameras):
            self.log(f"⚠️ Camera index {camera_index} out of range")
            return None
        
        folder = os.path.join(OUTPUT_DIR, order_no)
        os.makedirs(folder, exist_ok=True)
        
        cam = self.cameras[camera_index]
        cam.MV_CC_SetCommandValue("TriggerSoftware")
        image_path = self._grab_and_save(cam, folder, camera_index + 1, order_no)
        
        return image_path
    
    def _grab_and_save(self, cam, folder, cam_idx, order_no):
        """Capture และ save ภาพ (รองรับ replace)"""
        frame = MV_FRAME_OUT()
        memset(byref(frame), 0, sizeof(frame))
        
        ret = cam.MV_CC_GetImageBuffer(frame, TRIGGER_TIMEOUT_MS)
        if ret != 0:
            return None
        
        buf_size = frame.stFrameInfo.nWidth * frame.stFrameInfo.nHeight * 4 + 2048
        param = MV_SAVE_IMAGE_PARAM_EX()
        memset(byref(param), 0, sizeof(param))
        
        param.enImageType = MV_Image_Jpeg
        param.nJpgQuality = 90
        param.nWidth = frame.stFrameInfo.nWidth
        param.nHeight = frame.stFrameInfo.nHeight
        param.enPixelType = frame.stFrameInfo.enPixelType
        param.pData = frame.pBufAddr
        param.nDataLen = frame.stFrameInfo.nFrameLen
        param.nBufferSize = buf_size
        param.pImageBuffer = (c_ubyte * buf_size)()
        
        image_path = None
        
        if cam.MV_CC_SaveImageEx2(param) == 0:
            # ลบไฟล์เก่าของกล้องนี้ก่อน (ถ้ามี)
            for old_file in os.listdir(folder):
                if old_file.startswith(f"cam{cam_idx}_") and old_file.endswith(".jpg"):
                    old_path = os.path.join(folder, old_file)
                    try:
                        os.remove(old_path)
                        self.log(f"🗑️ Removed old: {old_file}")
                    except:
                        pass
            
            # บันทึกไฟล์ใหม่
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            image_path = os.path.join(folder, f"cam{cam_idx}_{ts}.jpg")
            with open(image_path, "wb") as f:
                f.write(string_at(param.pImageBuffer, param.nImageLen))
            self.log(f"📸 Saved {image_path}")
        
        cam.MV_CC_FreeImageBuffer(frame)
        return image_path
    
    def close_all(self):
        """ปิดกล้องทั้งหมด"""
        for cam in self.cameras:
            try:
                cam.MV_CC_StopGrabbing()
                cam.MV_CC_CloseDevice()
                cam.MV_CC_DestroyHandle()
            except:
                pass

# =============================
# OCR SERVER THREAD
# =============================
class CameraServerThread(QThread):
    """Thread สำหรับรับ OCR และถ่ายรูป"""
    order_received = pyqtSignal(str)  # ส่ง Order No
    countdown_update = pyqtSignal(int)  # ส่ง countdown (3, 2, 1, 0)
    images_captured = pyqtSignal(list)  # ส่ง list ของ image paths
    image_retaken = pyqtSignal(str)  # ส่ง path ของภาพที่ถ่ายใหม่
    log_message = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.running = True
        self.cam_mgr = None
        self.current_order_no = None  # 🆕 เก็บ Order No ปัจจุบัน
    
    def log(self, msg):
        self.log_message.emit(msg)
    
    def folder_has_images(self, path):
        if not os.path.exists(path):
            return False
        return any(f.lower().endswith(".jpg") for f in os.listdir(path))
    
    def run(self):
        # เริ่ม Camera Manager
        self.cam_mgr = HikCameraManager(log_callback=self.log)
        
        if not self.cam_mgr.init_cameras():
            self.log("❌ Cannot initialize cameras - Server will run but won't capture")
        
        # เริ่ม Socket Server
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(("0.0.0.0", PORT))
        server.listen(1)
        
        self.log(f"📡 Camera Server Listening on port {PORT}")
        
        while self.running:
            server.settimeout(1.0)
            try:
                conn, addr = server.accept()
            except socket.timeout:
                continue
            except:
                break
            
            self.log(f"🟢 OCR connected: {addr[0]}")
            
            with conn:
                while self.running:
                    try:
                        data = conn.recv(1024)
                        if not data:
                            break
                        
                        text = data.decode("utf-8", errors="ignore")
                        for line in text.splitlines():
                            match = ORDER_PATTERN.search(line)
                            if not match:
                                continue
                            
                            order_no = match.group(1).upper()
                            
                            # 🔒 Validation
                            if order_no.isdigit():
                                self.log(f"⚠️ Ignore (digit only): {order_no}")
                                continue
                            
                            folder = os.path.join(OUTPUT_DIR, order_no)
                            if self.folder_has_images(folder):
                                self.log(f"⏭️ Skip (already captured): {order_no}")
                                continue
                            
                            # 🔔 New Order Detected
                            self.log(f"🔔 New Order: {order_no}")
                            self.current_order_no = order_no  # 🆕 เก็บไว้สำหรับ retake
                            self.order_received.emit(order_no)
                            
                            # ⏱️ Countdown 3 วินาที
                            for i in range(CAPTURE_DELAY_SECONDS, 0, -1):
                                self.countdown_update.emit(i)
                                time.sleep(1)
                            
                            self.countdown_update.emit(0)
                            
                            # 📸 Capture!
                            if self.cam_mgr and len(self.cam_mgr.cameras) > 0:
                                image_paths = self.cam_mgr.capture_all(order_no)
                                self.images_captured.emit(image_paths)
                                self.log(f"✅ Captured {len(image_paths)} images")
                            else:
                                self.log("⚠️ No cameras available")
                    except:
                        break
            
            self.log("Disconnected")
        
        # Cleanup
        if self.cam_mgr:
            self.cam_mgr.close_all()
        server.close()
    
    def stop(self):
        self.running = False
        self.wait()
    
    def retake_camera(self, camera_index):
        """ถ่ายรูปใหม่แค่กล้องเดียว"""
        if not self.current_order_no:
            self.log("⚠️ No current order")
            return
        
        if not self.cam_mgr or len(self.cam_mgr.cameras) == 0:
            self.log("⚠️ No cameras available")
            return
        
        self.log(f"🔄 Retaking camera {camera_index + 1}...")
        image_path = self.cam_mgr.capture_single(self.current_order_no, camera_index)
        
        if image_path:
            self.image_retaken.emit(image_path)
            self.log(f"✅ Retaken: {image_path}")
    
    def retake_all(self):
        """ถ่ายรูปใหม่ทั้งหมด"""
        if not self.current_order_no:
            self.log("⚠️ No current order")
            return
        
        if not self.cam_mgr or len(self.cam_mgr.cameras) == 0:
            self.log("⚠️ No cameras available")
            return
        
        self.log(f"🔄 Retaking all cameras...")
        image_paths = self.cam_mgr.capture_all(self.current_order_no)
        self.images_captured.emit(image_paths)
        self.log(f"✅ Retaken all: {len(image_paths)} images")