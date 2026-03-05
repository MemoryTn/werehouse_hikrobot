# -*- coding: utf-8 -*-
"""
Hikrobot Multi-Camera Capture Server + GUI Integration
- รับข้อมูลจาก SC2000 ผ่าน Socket และ Manual Trigger จาก GUI
- จัดการดึงภาพ Live Feed จาก SC2000 เข้าหน่วยความจำกลาง
- Capture 4 ภาพ (ผูก IP ตรงตำแหน่ง) + 1 Snapshot จาก SC2000
"""

import socket
import os
import sys
import re
import time
import threading
import cv2
import numpy as np
from datetime import datetime
from ctypes import *
from PyQt5.QtCore import QThread, pyqtSignal
import config

# =============================
# IMPORT CONFIG
# =============================
from config import OUTPUT_DIR, SC2000_IP, CAM_DICT, HIKROBOT_IPS

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

PORT = 5020
TRIGGER_TIMEOUT_MS = 3000
CAPTURE_DELAY_SECONDS = 2

ORDER_PATTERN = re.compile(r"Shopee\s*Order\s*No\.?\s*([A-Z0-9]{14})", re.I)

config.SHARED_SC2000_FRAME = None

# =============================
# CAMERA MANAGER
# =============================
class HikCameraManager:
    def __init__(self, log_callback=None):
        self.cameras = [] # จะถูกจองที่ (Allocate) ใน init_cameras
        self.log_callback = log_callback
        self.sc2000_cam = None
        self.sc2000_running = False
        self.sc2000_thread = None
    
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
        ret = MvCamera.MV_CC_EnumDevices(MV_GIGE_DEVICE | MV_USB_DEVICE, device_list)
        
        if ret != 0 or device_list.nDeviceNum == 0:
            self.log("⚠️ No camera found for capture")
            return False
        
        # 📌 1. เตรียม List ว่างไว้ตามจำนวนกล้องใน Config เพื่อให้ Index ตรงกับ UI
        self.cameras = [None] * len(HIKROBOT_IPS)
        
        for i in range(device_list.nDeviceNum):
            st_dev = cast(device_list.pDeviceInfo[i], POINTER(MV_CC_DEVICE_INFO)).contents
            
            ip_int = 0
            ip_str = ""
            if st_dev.nTLayerType == MV_GIGE_DEVICE:
                ip_int = st_dev.SpecialInfo.stGigEInfo.nCurrentIp
                ip_str = f"{(ip_int >> 24) & 255}.{(ip_int >> 16) & 255}.{(ip_int >> 8) & 255}.{ip_int & 255}"

            cam = MvCamera()
            if cam.MV_CC_CreateHandle(st_dev) != 0:
                continue
            if cam.MV_CC_OpenDevice(MV_ACCESS_Control, 0) != 0:
                cam.MV_CC_DestroyHandle()
                continue
            
            if st_dev.nTLayerType == MV_GIGE_DEVICE:
                pkt = cam.MV_CC_GetOptimalPacketSize()
                if pkt > 0:
                    cam.MV_CC_SetIntValue("GevSCPSPacketSize", pkt)
            
            # 📌 2. เช็คว่าเป็น SC2000 (Live Feed) หรือไม่
            if ip_str == SC2000_IP:
                cam.MV_CC_SetEnumValue("TriggerMode", 0)  # Continuous
                cam.MV_CC_SetEnumValue("PixelFormat", 0x02180014) # RGB8_Packed
                cam.MV_CC_StartGrabbing()
                
                self.sc2000_cam = cam
                self.sc2000_running = True
                self.sc2000_thread = threading.Thread(target=self._sc2000_worker, daemon=True)
                self.sc2000_thread.start()
                
                # 📌 เพิ่มการเช็คว่า SC2000 เป็นกล้องเดียวกับตำแหน่งใน UI หรือไม่ (เช่น FRONT)
                if ip_str in HIKROBOT_IPS:
                    target_index = HIKROBOT_IPS.index(ip_str)
                    self.log(f"✅ SC2000 ({ip_str}) started Continuous Stream AND mapped to Camera {target_index+1}")
                else:
                    self.log(f"✅ SC2000 ({ip_str}) started Continuous Stream")
                continue # ข้ามกระบวนการด้านล่างไปดูกล้องตัวถัดไป
                
            # 📌 3. เช็คว่ากล้องตรงกับ HIKROBOT_IPS ใน Config หรือไม่ (เพื่อจัด Index)
            if ip_str in HIKROBOT_IPS:
                target_index = HIKROBOT_IPS.index(ip_str)
                cam.MV_CC_SetEnumValue("TriggerMode", 1)  # Trigger On
                cam.MV_CC_SetEnumValue("TriggerSource", 7) # Software Trigger
                cam.MV_CC_SetBoolValue("AcquisitionFrameRateEnable", False)
                cam.MV_CC_StartGrabbing()
                
                # นำ object กล้องไปใส่ในช่อง List ที่ตรงกัน
                self.cameras[target_index] = cam
                view_names = ["FRONT", "LEFT", "RIGHT", "BACK"]
                view_name = view_names[target_index] if target_index < 4 else f"IDX-{target_index}"
                self.log(f"✅ Camera {view_name} mapped to {ip_str}")
            else:
                self.log(f"⚠️ Found unconfigured camera IP: {ip_str}, ignoring...")
                cam.MV_CC_DestroyHandle()
        
        # 📌 4. สรุปผลการเชื่อมต่อกล้อง Snapshot
        connected_count = sum(1 for c in self.cameras if c is not None)
        self.log(f"✅ Capture Cameras ready: {connected_count}/{len(HIKROBOT_IPS)} + SC2000")
        return True

    def _sc2000_worker(self):
        stOutFrame = MV_FRAME_OUT()
        memset(byref(stOutFrame), 0, sizeof(MV_FRAME_OUT))
        
        while self.sc2000_running and self.sc2000_cam:
            ret = self.sc2000_cam.MV_CC_GetImageBuffer(stOutFrame, 1000)
            if ret == 0 and stOutFrame.pBufAddr:
                try:
                    w = stOutFrame.stFrameInfo.nWidth
                    h = stOutFrame.stFrameInfo.nHeight
                    data = string_at(stOutFrame.pBufAddr, stOutFrame.stFrameInfo.nFrameLen)
                    arr = np.frombuffer(data, dtype=np.uint8)
                    
                    if len(arr) == w * h * 3:
                        arr = arr.reshape((h, w, 3))
                    elif len(arr) == w * h:
                        arr = arr.reshape((h, w))
                        arr = cv2.cvtColor(arr, cv2.COLOR_GRAY2RGB)
                    
                    config.SHARED_SC2000_FRAME = arr.copy()
                except Exception:
                    pass
                self.sc2000_cam.MV_CC_FreeImageBuffer(stOutFrame)
            else:
                time.sleep(0.01)
    
    def capture_all(self, order_no):
        folder = os.path.join(OUTPUT_DIR, order_no)
        os.makedirs(folder, exist_ok=True)
        
        # 📌 สร้าง List ว่างไว้ 4 ช่อง (ใส่ "" กัน Error) เพื่อให้ Index ตรงกับ GUI
        image_paths = [""] * len(self.cameras)
        
        # 📌 วนลูปถ่ายภาพ (พร้อมระบบป้องกันกล้อง None)
        for idx, cam in enumerate(self.cameras):
            if cam is None:
                # 📌 ถ้านี่คือตำแหน่งของ SC2000 ให้ดึงภาพจาก Live Feed มาใช้แทนการ Trigger
                if HIKROBOT_IPS[idx] == SC2000_IP and config.SHARED_SC2000_FRAME is not None:
                    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                    image_path = os.path.join(folder, f"cam{idx+1}_{ts}.jpg")
                    
                    for old_file in os.listdir(folder):
                        if old_file.startswith(f"cam{idx+1}_") and old_file.endswith(".jpg"):
                            try: os.remove(os.path.join(folder, old_file))
                            except: pass
                            
                    bgr = cv2.cvtColor(config.SHARED_SC2000_FRAME, cv2.COLOR_RGB2BGR)
                    cv2.imwrite(image_path, bgr)
                    image_paths[idx] = image_path
                    self.log(f"📸 Saved SC2000 live frame as Camera {idx+1}")
                else:
                    self.log(f"⚠️ Camera {idx+1} is offline. Skipping capture.")
                continue # ข้ามตัวนี้ไปเลย
                
            cam.MV_CC_SetCommandValue("TriggerSoftware")
            image_path = self._grab_and_save(cam, folder, idx + 1, order_no)
            if image_path:
                image_paths[idx] = image_path # 📌 ยัดรูปลงช่องให้ตรง Index (0=Front, 1=Left, 2=Right, 3=Back)

        return image_paths
    
    def capture_single(self, order_no, camera_index):
        folder = os.path.join(OUTPUT_DIR, order_no)
        os.makedirs(folder, exist_ok=True)
        
        if camera_index < len(self.cameras):
            cam = self.cameras[camera_index]
            if cam is None:
                # 📌 ถ้ากด Retake กล้องหน้า (SC2000) ให้ดึงภาพจาก Live Feed มาเซฟใหม่
                if HIKROBOT_IPS[camera_index] == SC2000_IP and config.SHARED_SC2000_FRAME is not None:
                    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                    image_path = os.path.join(folder, f"cam{camera_index+1}_{ts}.jpg")
                    for old_file in os.listdir(folder):
                        if old_file.startswith(f"cam{camera_index+1}_") and old_file.endswith(".jpg"):
                            try: os.remove(os.path.join(folder, old_file))
                            except: pass
                    bgr = cv2.cvtColor(config.SHARED_SC2000_FRAME, cv2.COLOR_RGB2BGR)
                    cv2.imwrite(image_path, bgr)
                    self.log(f"📸 Retaken SC2000 live frame as Camera {camera_index+1}")
                    return image_path
                else:
                    self.log(f"⚠️ Cannot retake, Camera {camera_index+1} is offline.")
                    return None
                
            cam.MV_CC_SetCommandValue("TriggerSoftware")
            return self._grab_and_save(cam, folder, camera_index + 1, order_no)
            
        return None
    
    def _grab_and_save(self, cam, folder, cam_idx, order_no):
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
            for old_file in os.listdir(folder):
                if old_file.startswith(f"cam{cam_idx}_") and old_file.endswith(".jpg"):
                    try: os.remove(os.path.join(folder, old_file))
                    except: pass
            
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            image_path = os.path.join(folder, f"cam{cam_idx}_{ts}.jpg")
            with open(image_path, "wb") as f:
                f.write(string_at(param.pImageBuffer, param.nImageLen))
        
        cam.MV_CC_FreeImageBuffer(frame)
        return image_path
    
    def close_all(self):
        self.sc2000_running = False
        if self.sc2000_thread:
            self.sc2000_thread.join(timeout=1.0)
            
        if self.sc2000_cam:
            try:
                self.sc2000_cam.MV_CC_StopGrabbing()
                self.sc2000_cam.MV_CC_CloseDevice()
                self.sc2000_cam.MV_CC_DestroyHandle()
            except: pass
            
        # 📌 ป้องกัน Error ตอนปิดกล้อง
        for cam in self.cameras:
            if cam is not None:
                try:
                    cam.MV_CC_StopGrabbing()
                    cam.MV_CC_CloseDevice()
                    cam.MV_CC_DestroyHandle()
                except: pass

# =============================
# OCR SERVER THREAD
# =============================
class CameraServerThread(QThread):
    order_received = pyqtSignal(str)
    countdown_update = pyqtSignal(int)
    images_captured = pyqtSignal(list)
    image_retaken = pyqtSignal(str)
    log_message = pyqtSignal(str)
    manual_duplicate = pyqtSignal(str)  # สำหรับแจ้งเตือนเลขซ้ำ
    
    def __init__(self):
        super().__init__()
        self.running = True
        self.cam_mgr = None
        self.current_order_no = None
        self.is_processing = False # Flag ป้องกันการถ่ายทับซ้อนกัน
    
    def log(self, msg): self.log_message.emit(msg)
    
    def folder_has_images(self, path):
        if not os.path.exists(path): return False
        return any(f.lower().endswith(".jpg") for f in os.listdir(path))

    def _run_capture_sequence(self, order_no):
        """แยกกระบวนการ นับถอยหลัง และ สั่งถ่าย ออกมาเป็น Task อิสระ"""
        if self.is_processing:
            self.log(f"⚠️ System is currently processing another order. Skipping {order_no}")
            return
            
        def task():
            self.is_processing = True
            self.current_order_no = order_no
            self.order_received.emit(order_no)
            
            # นับถอยหลังตามที่กำหนดใน Config
            for i in range(CAPTURE_DELAY_SECONDS, 0, -1):
                self.countdown_update.emit(i)
                time.sleep(1)
            self.countdown_update.emit(0)
            
            # สั่งกล้องถ่าย
            if self.cam_mgr:
                image_paths = self.cam_mgr.capture_all(order_no)
                self.images_captured.emit(image_paths)
            
            self.is_processing = False
            
        # รันใน Thread แยกเพื่อไม่ให้บล็อก Socket Loop หรือ GUI Main Thread
        threading.Thread(target=task, daemon=True).start()

    def trigger_manual(self, order_no):
        """รับค่า Manual ID จาก GUI"""
        # 1. เช็คว่าซ้ำกับออเดอร์ที่กำลังทำงานอยู่บนหน้าจอหรือไม่
        if order_no == self.current_order_no:
            msg = f"ออเดอร์ {order_no}\nกำลังประมวลผลอยู่บนหน้าจอขณะนี้"
            self.log(f"⚠️ Manual Input Ignored: {order_no} (Already active)")
            self.manual_duplicate.emit(msg)  
            return
            
        # 2. เช็คว่าเคยถ่ายรูปไปแล้วหรือยัง
        folder = os.path.join(OUTPUT_DIR, order_no)
        if self.folder_has_images(folder):
            msg = f"ออเดอร์ {order_no}\nถูกบันทึกภาพไปแล้วในระบบ"
            self.log(f"⚠️ Manual Input Ignored: {order_no} (Already processed)")
            self.manual_duplicate.emit(msg)  
            return
            
        self.log(f"⌨️ Manual Input Triggered for ID: {order_no}")
        self._run_capture_sequence(order_no)

    def run(self):
        self.cam_mgr = HikCameraManager(log_callback=self.log)
        self.cam_mgr.init_cameras()
        
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(("0.0.0.0", PORT))
        server.listen(1)
        self.log(f"📡 Waiting for OCR (Port {PORT})")
        
        while self.running:
            server.settimeout(1.0)
            try:
                conn, addr = server.accept()
            except socket.timeout: continue
            except: break
            
            with conn:
                while self.running:
                    try:
                        data = conn.recv(1024)
                        if not data: break
                        
                        text = data.decode("utf-8", errors="ignore")
                        for line in text.splitlines():
                            match = ORDER_PATTERN.search(line)
                            if not match: continue
                            
                            order_no = match.group(1).upper()
                            if order_no.isdigit(): continue
                            
                            folder = os.path.join(OUTPUT_DIR, order_no)
                            if self.folder_has_images(folder): continue
                            
                            # เรียกใช้ฟังก์ชัน Task ไม่บล็อกตัวรับ Socket
                            self._run_capture_sequence(order_no)
                            
                    except: break
        if self.cam_mgr: self.cam_mgr.close_all()
        server.close()
    
    def stop(self):
        self.running = False
        self.wait()
    
    def retake_camera(self, camera_index):
        if not self.current_order_no or not self.cam_mgr: return
        image_path = self.cam_mgr.capture_single(self.current_order_no, camera_index)
        if image_path: self.image_retaken.emit(image_path)
    
    def retake_all(self):
        if not self.current_order_no or not self.cam_mgr: return
        image_paths = self.cam_mgr.capture_all(self.current_order_no)
        self.images_captured.emit(image_paths)