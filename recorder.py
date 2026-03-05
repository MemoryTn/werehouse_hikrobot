# -*- coding: utf-8 -*-
import os
import time
import subprocess
from config import HIKVISION_RTSP_URL_REC, OUTPUT_DIR_VIDEOS

class HikvisionRecorder:
    def __init__(self, log_callback=None):
        self.process = None
        self.is_recording = False
        self.current_file = ""
        self.current_folder = ""
        self.log_callback = log_callback
        
    def _popen_hidden(self, cmd, **kwargs):
        """Run subprocess without showing a console window on Windows."""
        if os.name == "nt":
            kwargs.setdefault("creationflags", subprocess.CREATE_NO_WINDOW)
            si = subprocess.STARTUPINFO()
            si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            kwargs.setdefault("startupinfo", si)
        return subprocess.Popen(cmd, **kwargs)
    
    def log(self, msg):
        if self.log_callback:
            self.log_callback(msg)
        else:
            print(f"[RECORDER] {msg}")

    def start_record(self, target_id):
        if self.is_recording:
            return False, "กำลังอัดอยู่แล้ว"
        
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        folder_name = f"{target_id}_{timestamp}"
        self.current_folder = os.path.join(OUTPUT_DIR_VIDEOS, folder_name)
        os.makedirs(self.current_folder, exist_ok=True)
        
        # 📌 จุดเปลี่ยนชีวิต: เปลี่ยนจาก .mp4 เป็น .mkv 
        self.current_file = os.path.join(self.current_folder, f"hikvision_vid_{timestamp}.mkv")
        
        cmd = [
            "ffmpeg", 
            "-rtsp_transport", "tcp", 
            "-i", HIKVISION_RTSP_URL_REC, 
            "-c", "copy", 
            "-y",  
            self.current_file
        ]
        
        try:
            # รันแบบเรียบง่าย ไม่ต้องใช้ท่าพิเศษอะไรเลย
            self.process = self._popen_hidden(
                cmd, 
                stdout=subprocess.DEVNULL, 
                stderr=subprocess.DEVNULL
            )
            self.is_recording = True
            
            self.log(f"📁 สร้างโฟลเดอร์: {folder_name}")
            self.log(f"🔴 เริ่มบันทึกวิดีโอ (MKV): ลงในโฟลเดอร์สำเร็จ")
            return True, self.current_file
        except FileNotFoundError:
            self.log("❌ ไม่พบโปรแกรม FFmpeg")
            return False, "FFmpeg is missing"

    def stop_record(self):
        if self.is_recording and self.process:
            self.log("⏹️ กำลังปิดไฟล์วิดีโอ...")
            try:
                # 📌 สั่งชักปลั๊กได้เลย ไฟล์ MKV จะไม่พังแน่นอน
                self.process.terminate()
                self.process.wait()
            except Exception as e:
                self.log(f"⚠️ Error stopping process: {e}")
            
            self.is_recording = False
            self.process = None
            self.log(f"✅ บันทึกวิดีโอเสร็จสมบูรณ์ (เปิดไฟล์ .mkv ดูได้เลย)")
            return True, self.current_file
            
        return False, "ไม่มีวิดีโอที่กำลังอัดอยู่"