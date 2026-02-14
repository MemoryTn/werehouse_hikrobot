# -*- coding: utf-8 -*-
"""
Hikrobot / Hikvision Camera Software Trigger - FULL DEBUG VERSION (FIXED)
- GigE + USB Support
- Multi Camera
- Software Trigger
- Save as JPEG (Fixed format error)
"""

import sys
import os
import time
import msvcrt
from ctypes import *

# =============================
# IMPORT MVS SDK
# =============================
# ตรวจสอบว่าไฟล์ MvCameraControl_class.py อยู่ในโฟลเดอร์เดียวกับ script หรือไม่
sys.path.append(".")
try:
    from MvCameraControl_class import *
except ImportError:
    print("Error: ไม่พบไฟล์ MvCameraControl_class.py")
    print("กรุณา copy ไฟล์นี้มาจาก MVS SDK/Development/Samples/Python/MvImport")
    sys.exit(1)

# =============================
# CONFIG
# =============================
SAVE_DIR = "images"
TRIGGER_TIMEOUT_MS = 3000

# สร้างโฟลเดอร์ถ้ายังไม่มี
os.makedirs(SAVE_DIR, exist_ok=True)

# =============================
# UTILS
# =============================
def ToHexStr(num):
    return f"0x{num:08X}"

def print_ret(step, ret):
    if ret == 0:
        print(f"   [OK] {step}")
    else:
        print(f"   [FAIL] {step} : {ToHexStr(ret)}")

# =============================
# GRAB & SAVE (FIXED FUNCTION)
# =============================
def grab_and_save(cam, filename):
    """
    ฟังก์ชันรับภาพและแปลงเป็น JPEG ก่อนบันทึก
    """
    stOutFrame = MV_FRAME_OUT()
    memset(byref(stOutFrame), 0, sizeof(stOutFrame))

    # 1. ดึงภาพ Raw Data จากกล้อง
    ret = cam.MV_CC_GetImageBuffer(stOutFrame, TRIGGER_TIMEOUT_MS)
    if ret != 0:
        print_ret("GetImageBuffer", ret)
        return False
    
    # 2. เตรียมแปลงไฟล์ (Convert to JPEG)
    c_buf_size = stOutFrame.stFrameInfo.nWidth * stOutFrame.stFrameInfo.nHeight * 4 + 2048
    stParam = MV_SAVE_IMAGE_PARAM_EX()
    memset(byref(stParam), 0, sizeof(stParam))

    stParam.enImageType = MV_Image_Jpeg   # บันทึกเป็น JPEG
    stParam.nJpgQuality = 90              # คุณภาพรูป (0-100)
    stParam.nWidth      = stOutFrame.stFrameInfo.nWidth
    stParam.nHeight     = stOutFrame.stFrameInfo.nHeight
    stParam.pData       = stOutFrame.pBufAddr
    stParam.nDataLen    = stOutFrame.stFrameInfo.nFrameLen
    stParam.enPixelType = stOutFrame.stFrameInfo.enPixelType
    
    # สร้าง Buffer เปล่าๆ มารอรับข้อมูล JPEG
    stParam.nBufferSize = c_buf_size
    stParam.pImageBuffer = (c_ubyte * c_buf_size)()

    try:
        # สั่ง SDK แปลงข้อมูล
        ret = cam.MV_CC_SaveImageEx2(stParam)
        if ret != 0:
            print_ret("SaveImageEx2", ret)
            return False

        # 3. เขียนลงไฟล์
        # ใช้ nImageLen คือขนาดไฟล์จริงหลังบีบอัดแล้ว
        file_bytes = string_at(stParam.pImageBuffer, stParam.nImageLen)
        
        with open(filename, "wb") as f:
            f.write(file_bytes)
        
        print(f"       -> Saved: {filename} (Size: {stParam.nImageLen} bytes)")
        return True

    except Exception as e:
        print(f"       -> Error saving file: {e}")
        return False
        
    finally:
        # 4. สำคัญมาก! ต้องคืน Buffer ให้กล้องเสมอ
        cam.MV_CC_FreeImageBuffer(stOutFrame)

# =============================
# MAIN
# =============================
def main():
    print("=== Hikrobot Camera DEBUG MODE (JPEG FIXED) ===")

    # 1) ค้นหากล้อง (ENUM DEVICES)
    deviceList = MV_CC_DEVICE_INFO_LIST()
    tlayerType = MV_GIGE_DEVICE | MV_USB_DEVICE

    ret = MvCamera.MV_CC_EnumDevices(tlayerType, deviceList)
    if ret != 0:
        print_ret("EnumDevices", ret)
        return

    if deviceList.nDeviceNum == 0:
        print(" ไม่พบกล้อง (No Camera Found)")
        return

    print(f" พบกล้องทั้งหมด: {deviceList.nDeviceNum} ตัว")

    cameras = []

    # 2) เปิดกล้องแต่ละตัว (OPEN & CONFIG)
    for i in range(deviceList.nDeviceNum):
        print(f"\n=== Init Camera {i+1} ===")

        stDevice = deviceList.pDeviceInfo[i].contents
        cam = MvCamera()

        # สร้าง Handle
        ret = cam.MV_CC_CreateHandle(stDevice)
        if ret != 0:
            print_ret("CreateHandle", ret)
            continue

        # เปิด Device
        ret = cam.MV_CC_OpenDevice(MV_ACCESS_Control, 0)
        if ret != 0:
            print_ret("OpenDevice", ret)
            cam.MV_CC_DestroyHandle()
            continue
        
        # ตั้งค่า Packet Size สำหรับกล้อง GigE (ถ้าเป็น USB คำสั่งนี้จะ fail แต่ไม่คริติคอล)
        if stDevice.nTLayerType == MV_GIGE_DEVICE:
            nPacketSize = cam.MV_CC_GetOptimalPacketSize()
            if int(nPacketSize) > 0:
                cam.MV_CC_SetIntValue("GevSCPSPacketSize", nPacketSize)

        # =============================
        # CONFIG PARAMETERS
        # =============================
        print("   Setting parameters...")

        # เปิด Trigger Mode (1 = On)
        ret = cam.MV_CC_SetEnumValue("TriggerMode", 1)
        if ret != 0: print_ret("Set TriggerMode", ret)

        # เลือก Trigger Source เป็น Software (7 หรือ 6 แล้วแต่รุ่นกล้อง)
        # ลองวน loop ตั้งค่า เพราะบางรุ่นใช้ value 7, บางรุ่นใช้ 6
        ret = cam.MV_CC_SetEnumValue("TriggerSource", 7) 
        if ret != 0:
            cam.MV_CC_SetEnumValue("TriggerSource", 6)

        # ปิด Auto FPS เพื่อให้รอ Trigger อย่างเดียว
        cam.MV_CC_SetBoolValue("AcquisitionFrameRateEnable", False)

        # เริ่มการทำงาน (Start Grabbing)
        ret = cam.MV_CC_StartGrabbing()
        if ret != 0:
            print_ret("StartGrabbing", ret)
            cam.MV_CC_CloseDevice()
            cam.MV_CC_DestroyHandle()
            continue

        print("   Camera READY")
        cameras.append(cam)

    if not cameras:
        print("\n[ERROR] ไม่สามารถเปิดกล้องได้เลยสักตัว")
        return

    print("\n===========================================")
    print(f" SYSTEM READY ({len(cameras)} cameras)")
    print(" กด 't' เพื่อถ่ายรูป (Trigger)")
    print(" กด 'q' เพื่อจบการทำงาน")
    print("===========================================")

    # 3) LOOP รับคำสั่ง
    try:
        while True:
            # ใช้ msvcrt สำหรับ Windows เพื่อรับปุ่มกด
            if msvcrt.kbhit():
                key = msvcrt.getch()

                if key in (b'q', b'Q'):
                    break

                if key in (b't', b'T'):
                    print("\n[TRIGGER COMMAND]")
                    ts = time.strftime("%Y%m%d_%H%M%S")

                    for idx, cam in enumerate(cameras):
                        # ส่งคำสั่ง Trigger ไปที่กล้อง
                        ret = cam.MV_CC_SetCommandValue("TriggerSoftware")
                        
                        if ret == 0:
                            # ตั้งชื่อไฟล์
                            fname = os.path.join(SAVE_DIR, f"cam{idx+1}_{ts}.jpg")
                            grab_and_save(cam, fname)
                        else:
                            print_ret(f"Cam{idx+1} Trigger Fail", ret)
            
            # ลดภาระ CPU
            time.sleep(0.01)

    except KeyboardInterrupt:
        pass

    # 4) CLEANUP
    print("\nClosing cameras...")
    for cam in cameras:
        cam.MV_CC_StopGrabbing()
        cam.MV_CC_CloseDevice()
        cam.MV_CC_DestroyHandle()

    print("Done.")

if __name__ == "__main__":
    main()