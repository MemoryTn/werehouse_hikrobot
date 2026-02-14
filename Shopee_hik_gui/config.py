# -*- coding: utf-8 -*-
import os

# ================= NETWORK CONFIG =================
SERVER_IP = "0.0.0.0"      # Listen all (รวม 192.168.1.1)
SERVER_PORT = 5020         # Port ที่รอรับ OCR
TARGET_CAM_IP = "192.168.1.1"

# ================= RTSP CAMERA CONFIG =================
# ไม่ใช้ RTSP - ใช้ SCMVS ส่ง OCR ผ่าน Socket แทน
USE_RTSP = False  # ปิด RTSP ทั้งหมด

# Smart Camera SC2000 (ไม่ใช้ - ใช้ SCMVS แทน)
SC2000_RTSP_URL = ""

# Hikvision CCTV (ไม่ใช้)
HIKVISION_RTSP_URL = ""

# Hikrobot Cameras (ใช้ SDK แทน RTSP)
HIKROBOT_IPS = [
    "192.168.1.64",   # Hikrobot-1
    "192.168.1.65",   # Hikrobot-2
    "192.168.1.66",   # Hikrobot-3
    "192.168.1.67"    # Hikrobot-4
]

# ================= SIMULATION MODE =================
# ปิด simulation ทั้งหมด - ใช้กล้องจริง
USE_SIMULATION = False  # ใช้กล้องจริงทั้งหมด
HIKROBOT_USE_SIMULATION = False

# ================= PATH CONFIG =================
OUTPUT_DIR = "./evidence_images"
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

# ================= UI THEME (Modern Dark) =================
COLORS = {
    'bg_app': '#1e1e2e',       # พื้นหลังหลัก
    'bg_card': '#2b2b3b',      # พื้นหลัง Card
    'bg_input': '#313244',     # พื้นหลัง Input/Display
    'text': '#ffffff',         # สีตัวอักษรหลัก
    'text_dim': '#bac2de',     # สีตัวอักษรรอง
    'border': '#45475a',       # สีขอบ
    'active_bg': '#1e3a8a',    # พื้นหลังตอนกำลังทำงาน
    
    # สถานะ
    'success': '#a6e3a1',      # สีเขียวสำเร็จ
    'processing': '#89b4fa',   # สีฟ้า Processing
    'warning': '#f9e2af',      # สีเหลืองแจ้งเตือน
    'error': '#f38ba8',        # สีแดง Error
    
    # แบรนด์
    'shopee': '#ee4d2d',       # สีส้ม Shopee
    'primary': '#8b5cf6',      # ม่วง
}

FONTS = {
    'main': 'Segoe UI',
    'mono': 'Consolas'
}

FONTS = {
    'main': 'Segoe UI',
    'mono': 'Consolas'
}