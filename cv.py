import socket
import cv2
import os
import time
import sys
import numpy as np
from datetime import datetime
from ctypes import *

# ==========================================
# IMPORT HIKROBOT SDK (แก้ไขให้ตรงกับเวอร์ชันเครื่องคุณ)
# ==========================================
try:
    sys.path.append(os.getcwd())
    # Import ทุกอย่างออกมา เพื่อให้ได้ค่าคงที่ด้วย (MV_GIGE_DEVICE, etc.)
    from MvImport.MvCameraControl_class import *
    print("✅ Load MvImport Library Success!")
except ImportError as e:
    print("❌ Error: ไม่สามารถ Import Library ได้")
    print(f"Details: {e}")
    sys.exit(1)

# --- CONFIG ---
HOST = '0.0.0.0'
PORT = 5001        # Port ที่รอรับ Trigger จากกล้อง OCR
OUTPUT_DIR = "./evidence_images"

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

class HikRobotCamera:
    def __init__(self):
        # --- แก้ไขจุดที่ 1: เปลี่ยนชื่อ Class เป็น MvCamera ---
        self.cam = MvCamera()
        
        self.stDeviceList = MV_CC_DEVICE_INFO_LIST()
        self.nPayloadSize = 0
        self.data_buf = None

    def connect(self):
        # 1. ค้นหากล้อง (Enum Devices)
        ret = MvCamera.MV_CC_EnumDevices(MV_GIGE_DEVICE | MV_USB_DEVICE, self.stDeviceList)
        if ret != 0:
            log(f"❌ Enum Devices fail! ret[0x{ret:x}]")
            return False

        if self.stDeviceList.nDeviceNum == 0:
            log("❌ No camera found!")
            return False

        log(f"📷 Found {self.stDeviceList.nDeviceNum} camera(s). Connecting to index 0...")

        # 2. สร้าง Handle
        stDeviceList = cast(self.stDeviceList.pDeviceInfo[0], POINTER(MV_CC_DEVICE_INFO)).contents
        ret = self.cam.MV_CC_CreateHandle(stDeviceList)
        if ret != 0:
            log(f"❌ Create Handle fail! ret[0x{ret:x}]")
            return False

        # 3. เปิดกล้อง
        ret = self.cam.MV_CC_OpenDevice(MV_ACCESS_Exclusive, 0)
        if ret != 0:
            log(f"❌ Open Device fail! ret[0x{ret:x}]")
            return False
        
        # 4. ตั้งค่า Parameter (ปิด Trigger Mode เพื่อสั่งถ่ายเอง)
        # หมายเหตุ: ถ้า SDK ฟ้อง Error บรรทัดนี้ ให้ลอง comment ทิ้งได้
        ret = self.cam.MV_CC_SetEnumValue("TriggerMode", MV_TRIGGER_MODE_OFF)
        
        # 5. เตรียม Buffer
        stParam =  MVCC_INTVALUE()
        memset(byref(stParam), 0, sizeof(MVCC_INTVALUE))
        ret = self.cam.MV_CC_GetIntValue("PayloadSize", stParam)
        self.nPayloadSize = stParam.nCurValue
        self.data_buf = (c_ubyte * self.nPayloadSize)()

        # 6. เริ่มส่งสัญญาณภาพ
        ret = self.cam.MV_CC_StartGrabbing()
        if ret != 0:
            log(f"❌ Start Grabbing fail! ret[0x{ret:x}]")
            return False

        log("✅ HikRobot Camera Connected & Running!")
        return True

    def take_snapshot(self, order_id):
        if self.data_buf is None:
            log("⚠️ Camera not ready, trying to reconnect...")
            self.connect()
            return

        # --- ดึงภาพ 1 เฟรม ---
        stFrameInfo = MV_FRAME_OUT_INFO_EX()
        memset(byref(stFrameInfo), 0, sizeof(stFrameInfo))
        
        # Timeout 1000ms
        ret = self.cam.MV_CC_GetOneFrameTimeout(self.data_buf, self.nPayloadSize, stFrameInfo, 1000)
        
        if ret == 0:
            # แปลงข้อมูลภาพ (ปรับแก้ตามประเภทกล้องของคุณ)
            h, w = stFrameInfo.nHeight, stFrameInfo.nWidth
            
            # สมมติว่าเป็น Mono8 (ขาวดำ) หรือ RGB ดิบ
            # สร้าง Numpy Array จาก Buffer
            p_data = (c_ubyte * stFrameInfo.nFrameLen).from_address(addressof(self.data_buf))
            image_data = np.frombuffer(p_data, dtype=np.uint8).reshape(h, w, -1) # ปรับ Shape อัตโนมัติ

            # ถ้าภาพเป็นขาวดำ (Mono) มันจะเป็น (h, w, 1) -> (h, w)
            if image_data.shape[2] == 1:
                image_data = image_data.reshape(h, w)
                final_image = image_data # ใช้ได้เลย
            else:
                # ถ้าเป็น Bayer (ภาพสีที่ยังไม่แปลง) ต้อง Convert
                # ลองรันดูก่อน ถ้าภาพเพี้ยนค่อยมาแก้บรรทัดนี้ครับ
                final_image = cv2.cvtColor(image_data, cv2.COLOR_BayerRG2RGB) 

            # --- SAVE ---
            clean_id = "".join(x for x in order_id if x.isalnum())
            folder_path = os.path.join(OUTPUT_DIR, clean_id)
            os.makedirs(folder_path, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{folder_path}/{clean_id}_{timestamp}.jpg"
            
            cv2.imwrite(filename, final_image)
            log(f"✅ Evidence Saved: {filename}")
            
        else:
            log(f"❌ Failed to grab frame. ret[0x{ret:x}]")
            # ถ้าหลุดให้ลองต่อใหม่
            self.connect()

def run_server():
    if not os.path.exists(OUTPUT_DIR): os.makedirs(OUTPUT_DIR)

    # เชื่อมต่อกล้อง
    cam = HikRobotCamera()
    if not cam.connect():
        log("❌ Cannot connect to camera. Exiting...")
        # (Optional) ถ้าไม่มีกล้องจริง ให้ comment บรรทัด return เพื่อเทสระบบ Server อย่างเดียว
        return

    # เปิด Server รอ Trigger
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind((HOST, PORT))
    s.listen(1)
    
    log(f"📡 Waiting for OCR Camera on port {PORT}...")

    while True:
        try:
            conn, addr = s.accept()
            log(f"🟢 Connected by OCR Camera: {addr}")
            
            with conn:
                while True:
                    data = conn.recv(1024)
                    if not data: break
                    
                    ocr_text = data.decode('utf-8', errors='ignore').strip()
                    if ocr_text:
                        for line in ocr_text.splitlines():
                            clean_txt = line.strip()
                            if clean_txt:
                                log(f"🔔 Triggered ID: {clean_txt}")
                                cam.take_snapshot(clean_txt)
        except Exception as e:
            log(f"Error: {e}")
            time.sleep(1)

if __name__ == "__main__":
    run_server()