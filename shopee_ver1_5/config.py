# -*- coding: utf-8 -*-
import os

# ================= NETWORK CONFIG =================
# Backend Server (Brain)
BACKEND_HOST = "0.0.0.0"
BACKEND_PORT = 5010       # Port สำหรับรับ Trigger จาก OCR ภายนอก (ถ้ามี)
GUI_BROADCAST_PORT = 5002  # Port สำหรับส่งข้อมูลไปหา GUI

# SC2000 Smart Camera
SC2000_IP = "192.168.1.10"
SC2000_PORT = 5001
SC2000_CONFIDENCE_THRESHOLD = 0.85

# Hikvision CCTV (RTSP)
RTSP_URL = "rtsp://admin:admin123@192.168.1.64:554/Streaming/Channels/102" # Sub-stream

# ================= PATHS =================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IMAGE_DIR = os.path.join(BASE_DIR, "evidence_images")
LOG_DIR = os.path.join(BASE_DIR, "logs")

# สร้างโฟลเดอร์ถ้ายังไม่มี
os.makedirs(IMAGE_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)