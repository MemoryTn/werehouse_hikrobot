# -*- coding: utf-8 -*-
import sys
import time
import cv2
import numpy as np
from ctypes import *
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtGui import QImage
from config import COLORS, OUTPUT_DIR, HIKROBOT_IPS
import os
from datetime import datetime

# พยายาม Import SDK
try:
    sys.path.append(".")
    from MvImport.MvCameraControl_class import *
    SDK_AVAILABLE = True
except ImportError:
    SDK_AVAILABLE = False

class HikrobotCameraThread(QThread):
    """Thread สำหรับกล้อง Hikrobot แต่ละตัว"""
    frame_received = pyqtSignal(QImage)
    status_changed = pyqtSignal(str, str, str)  # (text, color, border_color)
    log_message = pyqtSignal(str)
    
    def __init__(self, camera_index=0, target_ip=None):
        super().__init__()
        self.camera_index = camera_index
        self.target_ip = target_ip
        self.cam = None
        self.running = True
        self.save_request = None
        self.camera_name = f"Hikrobot-{camera_index + 1}"
        
    def run(self):
        if not SDK_AVAILABLE:
            self.run_simulation()
            return
        
        while self.running:
            # เชื่อมต่อกล้อง
            if not self.init_camera():
                self.status_changed.emit("SEARCHING", COLORS['warning'], COLORS['warning'])
                time.sleep(3)
                continue
            
            self.status_changed.emit("LIVE", COLORS['success'], COLORS['success'])
            self.log_message.emit(f"✅ {self.camera_name} Connected")
            
            # Buffer
            data_buf_size = 4096 * 3072 * 3
            data_buf = (c_ubyte * data_buf_size)()
            stFrameInfo = MV_FRAME_OUT_INFO_EX()
            
            # ลูปดึงภาพ
            while self.running:
                ret = self.cam.MV_CC_GetOneFrameTimeout(data_buf, data_buf_size, stFrameInfo, 1000)
                
                if ret == 0:
                    # แปลง Raw -> RGB
                    img_data = np.frombuffer(data_buf, count=stFrameInfo.nFrameLen, dtype=np.uint8)
                    img_color = self.convert_image(img_data, stFrameInfo)
                    
                    if img_color is not None:
                        # บันทึกภาพถ้ามีคำสั่ง
                        if self.save_request:
                            self.save_image(self.save_request, img_color)
                            self.save_request = None
                        
                        # ส่งภาพไป GUI
                        h, w, ch = img_color.shape
                        bytes_per_line = ch * w
                        qt_img = QImage(img_color.data, w, h, bytes_per_line, QImage.Format_RGB888)
                        self.frame_received.emit(qt_img)
                else:
                    pass  # Timeout
            
            self.close_camera()
    
    def convert_image(self, img_data, stFrameInfo):
        """แปลงภาพจาก Raw Format"""
        try:
            if stFrameInfo.enPixelType == PixelType_Gvsp_Mono8:
                img_data = img_data.reshape((stFrameInfo.nHeight, stFrameInfo.nWidth))
                return cv2.cvtColor(img_data, cv2.COLOR_GRAY2RGB)
            
            elif stFrameInfo.enPixelType == PixelType_Gvsp_BayerRG8:
                img_data = img_data.reshape((stFrameInfo.nHeight, stFrameInfo.nWidth))
                return cv2.cvtColor(img_data, cv2.COLOR_BayerRG2RGB)
            
            elif stFrameInfo.enPixelType == PixelType_Gvsp_BayerGB8:
                img_data = img_data.reshape((stFrameInfo.nHeight, stFrameInfo.nWidth))
                return cv2.cvtColor(img_data, cv2.COLOR_BayerGB2RGB)
            
            else:
                img_data = img_data.reshape((stFrameInfo.nHeight, stFrameInfo.nWidth, -1))
                if img_data.shape[2] == 1:
                    return cv2.cvtColor(img_data, cv2.COLOR_GRAY2RGB)
                return img_data
        except:
            return None
    
    def init_camera(self):
        """เชื่อมต่อกล้อง"""
        try:
            device_list = MV_CC_DEVICE_INFO_LIST()
            ret = MvCamera.MV_CC_EnumDevices(MV_GIGE_DEVICE | MV_USB_DEVICE, device_list)
            
            if device_list.nDeviceNum == 0:
                self.log_message.emit(f"❌ {self.camera_name}: No Device Found")
                return False
            
            # เลือกกล้องตาม index หรือ IP
            if self.camera_index < device_list.nDeviceNum:
                st_dev = device_list.pDeviceInfo[self.camera_index]
            else:
                self.log_message.emit(f"❌ {self.camera_name}: Index out of range")
                return False
            
            self.cam = MvCamera()
            
            if self.cam.MV_CC_CreateHandle(st_dev) != 0:
                return False
            
            if self.cam.MV_CC_OpenDevice(MV_ACCESS_Exclusive, 0) != 0:
                self.log_message.emit(f"❌ {self.camera_name}: Open Failed")
                return False
            
            # ตั้งค่ากล้อง
            self.cam.MV_CC_SetEnumValue("TriggerMode", MV_TRIGGER_MODE_OFF)
            self.cam.MV_CC_SetFloatValue("ExposureTime", 20000.0)
            self.cam.MV_CC_SetEnumValue("ExposureAuto", MV_EXPOSURE_AUTO_MODE_OFF)
            
            # Packet Size
            nPacketSize = self.cam.MV_CC_GetOptimalPacketSize()
            if int(nPacketSize) > 0:
                self.cam.MV_CC_SetIntValue("GevSCPSPacketSize", int(nPacketSize))
            
            # เริ่มส่งภาพ
            ret = self.cam.MV_CC_StartGrabbing()
            if ret != 0:
                self.log_message.emit(f"❌ {self.camera_name}: Start Grabbing Failed")
                return False
            
            return True
        except Exception as e:
            self.log_message.emit(f"❌ {self.camera_name} Init Error: {e}")
            return False
    
    def close_camera(self):
        """ปิดกล้อง"""
        if self.cam:
            try:
                self.cam.MV_CC_StopGrabbing()
                self.cam.MV_CC_CloseDevice()
                self.cam.MV_CC_DestroyHandle()
            except:
                pass
            self.cam = None
    
    def capture(self, order_no):
        """สั่งบันทึกภาพ"""
        self.save_request = order_no
    
    def save_image(self, order_no, img_array):
        """บันทึกภาพ"""
        try:
            folder = os.path.join(OUTPUT_DIR, order_no)
            os.makedirs(folder, exist_ok=True)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = os.path.join(folder, f"{self.camera_name}_{ts}.jpg")
            
            save_img = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
            cv2.imwrite(filename, save_img)
            self.log_message.emit(f"✅ {self.camera_name} Saved: {filename}")
            self.status_changed.emit("CAPTURED", COLORS['success'], COLORS['success'])
        except Exception as e:
            self.log_message.emit(f"❌ {self.camera_name} Save Error: {e}")
    
    def run_simulation(self):
        """โหมดจำลอง"""
        self.log_message.emit(f"🔧 {self.camera_name}: Simulation Mode")
        self.status_changed.emit("SIMULATION", COLORS['processing'], COLORS['processing'])
        
        while self.running:
            try:
                img = np.zeros((480, 640, 3), dtype=np.uint8)
                img[:] = (30, 30, 30)
                
                noise = np.random.randint(0, 40, (480, 640, 3), dtype=np.uint8)
                img = cv2.add(img, noise)
                
                cv2.putText(img, f"{self.camera_name}", (150, 240), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 255, 255), 2)
                cv2.putText(img, "SIMULATION", (180, 280), cv2.FONT_HERSHEY_SIMPLEX, 1, (100, 200, 255), 2)
                
                h, w, ch = img.shape
                img_copy = img.copy()
                qt_img = QImage(img_copy.data, w, h, ch * w, QImage.Format_RGB888).copy()
                self.frame_received.emit(qt_img)
                
                if self.save_request:
                    self.log_message.emit(f"📸 (Sim) {self.camera_name} Saved {self.save_request}")
                    self.save_request = None
                
                time.sleep(0.033)
            except Exception as e:
                self.log_message.emit(f"❌ {self.camera_name} Simulation Error: {str(e)}")
                time.sleep(0.1)
    
    def stop(self):
        """หยุด thread"""
        self.running = False
        self.close_camera()
        self.wait()