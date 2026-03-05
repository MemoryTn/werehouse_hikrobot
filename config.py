# -*- coding: utf-8 -*-
import os

# ================= NETWORK CONFIG =================
SERVER_IP = "0.0.0.0"
SERVER_PORT = 5020
TARGET_CAM_IP = "192.168.1.15"

# ================= CAMERA IPS & URLs =================
# SC2000 ใช้ SDK ดึงภาพแบบ Live Feed 
SC2000_IP = "192.168.1.13"
CAM_DICT = {
    "FRONT VIEW": "192.168.1.13",
    "LEFT SIDE":  "192.168.1.11",
    "RIGHT SIDE": "192.168.1.14",
    "BACK VIEW":  "192.168.1.10"
}

# Hikvision CCTV ใช้ RTSP
HIKVISION_RTSP_URL = "rtsp://admin:Abc_2026@192.168.1.64/Streaming/Channels/102"      # ของเดิม: ใช้แสดงผลบน GUI (Sub Stream)
HIKVISION_RTSP_URL_REC = "rtsp://admin:Abc_2026@192.168.1.64/Streaming/Channels/101"      # ของเดิม: ใช้บันทึกภาพ (Main Stream)

# Hikrobot Cameras (ใช้ SDK สำหรับถ่ายภาพเมื่อมี Trigger เท่านั้น)
HIKROBOT_IPS = [
CAM_DICT["FRONT VIEW"],
CAM_DICT["LEFT SIDE"],
CAM_DICT["RIGHT SIDE"],
CAM_DICT["BACK VIEW"]
]

# ================= PATH CONFIG =================
OUTPUT_DIR = "./evidence_images"
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

OUTPUT_DIR_VIDEOS = "./evidence_videos"
if not os.path.exists(OUTPUT_DIR_VIDEOS):
    os.makedirs(OUTPUT_DIR_VIDEOS)

# ================= UI THEME (Modern Dark) =================
COLORS = {
    'bg_app': '#1e1e2e',
    'bg_card': '#2b2b3b',
    'bg_input': '#313244',
    'text': '#ffffff',
    'text_dim': '#bac2de',
    'border': '#45475a',
    'active_bg': '#1e3a8a',
    'success': '#a6e3a1',
    'processing': '#89b4fa',
    'warning': '#f9e2af',
    'error': '#f38ba8',
    'shopee': '#ee4d2d',
    'primary': '#8b5cf6',
}

FONTS = {
    'main': 'Segoe UI',
    'mono': 'Consolas'
}