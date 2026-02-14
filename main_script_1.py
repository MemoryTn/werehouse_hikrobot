# -*- coding: utf-8 -*-
"""
Hikrobot / Hikvision Multi-Camera Capture Server
CURRENT VERSION (Shopee Order No = 14 chars only)

- Receive OCR text via Socket
- Accept ONLY Shopee Order No (14 chars, alphanumeric, not digit-only)
- Capture 1 image per camera per order
- Never duplicate capture in same folder
"""

import socket
import os
import sys
import re
from datetime import datetime
from ctypes import *

# =============================
# IMPORT HIKROBOT SDK
# =============================
sys.path.append(".")
try:
    from MvImport.MvCameraControl_class import *
except ImportError:
    print("❌ Cannot import MvCameraControl_class.py")
    sys.exit(1)

# =============================
# CONFIG
# =============================
HOST = "192.168.1.3"
PORT = 5001
OUTPUT_DIR = "./evidence_images"
TRIGGER_TIMEOUT_MS = 3000

os.makedirs(OUTPUT_DIR, exist_ok=True)

# 🔒 Shopee Order No = 14 chars ONLY
ORDER_PATTERN = re.compile(
    r"Shopee\s*Order\s*No\.?\s*([A-Z0-9]{14})",
    re.I
)

# =============================
# UTILS
# =============================
def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

def folder_has_images(path):
    if not os.path.exists(path):
        return False
    return any(f.lower().endswith(".jpg") for f in os.listdir(path))

# =============================
# CAMERA MANAGER
# =============================
class HikCameraManager:
    def __init__(self):
        self.cameras = []

    def init_cameras(self):
        device_list = MV_CC_DEVICE_INFO_LIST()
        ret = MvCamera.MV_CC_EnumDevices(
            MV_GIGE_DEVICE | MV_USB_DEVICE,
            device_list
        )

        if ret != 0 or device_list.nDeviceNum == 0:
            log("❌ No camera found")
            return False

        log(f"📷 Found {device_list.nDeviceNum} camera(s)")

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

        log(f"✅ Cameras ready: {len(self.cameras)}")
        return True

    def capture_all(self, order_no):
        folder = os.path.join(OUTPUT_DIR, order_no)
        os.makedirs(folder, exist_ok=True)

        for idx, cam in enumerate(self.cameras):
            cam.MV_CC_SetCommandValue("TriggerSoftware")
            self._grab_and_save(cam, folder, idx + 1)

    def _grab_and_save(self, cam, folder, cam_idx):
        frame = MV_FRAME_OUT()
        memset(byref(frame), 0, sizeof(frame))

        ret = cam.MV_CC_GetImageBuffer(frame, TRIGGER_TIMEOUT_MS)
        if ret != 0:
            return

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

        if cam.MV_CC_SaveImageEx2(param) == 0:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{folder}/cam{cam_idx}_{ts}.jpg"
            with open(filename, "wb") as f:
                f.write(string_at(param.pImageBuffer, param.nImageLen))
            log(f"📸 Saved {filename}")

        cam.MV_CC_FreeImageBuffer(frame)

# =============================
# SOCKET SERVER
# =============================
def run_server():
    cam_mgr = HikCameraManager()
    if not cam_mgr.init_cameras():
        return

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((HOST, PORT))
    server.listen(1)

    log(f"📡 Listening OCR trigger on port {PORT}")

    while True:
        conn, addr = server.accept()
        log(f"🟢 OCR connected: {addr}")

        with conn:
            while True:
                data = conn.recv(1024)
                if not data:
                    break

                text = data.decode("utf-8", errors="ignore")
                for line in text.splitlines():
                    match = ORDER_PATTERN.search(line)
                    if not match:
                        continue

                    order_no = match.group(1).upper()

                    # 🔒 Final validation
                    if order_no.isdigit():
                        log(f"⚠️ Ignore invalid OrderNo (digit only): {order_no}")
                        continue

                    folder = os.path.join(OUTPUT_DIR, order_no)
                    if folder_has_images(folder):
                        log(f"⏭️ Skip (already captured): {order_no}")
                        continue

                    log(f"🔔 New Order Detected: {order_no}")
                    cam_mgr.capture_all(order_no)

# =============================
# MAIN
# =============================
if __name__ == "__main__":
    run_server()
