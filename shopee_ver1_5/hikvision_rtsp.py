# -*- coding: utf-8 -*-
"""
Hikvision RTSP Video Stream Handler
รับภาพจาก Hikvision camera ผ่าน RTSP protocol สำหรับแสดงใน GUI
"""

import cv2
import threading
import time
from typing import Optional, Callable
import numpy as np


class HikvisionRTSP:
    """
    จัดการ RTSP stream จาก Hikvision camera
    รองรับ multiple streams (Main/Sub stream)
    """
    
    def __init__(self, 
                 host: str = "192.168.1.64",
                 port: int = 554,
                 username: str = "admin",
                 password: str = "admin123",
                 channel: int = 1,
                 stream_type: str = "main"):
        """
        Args:
            host: IP address ของกล้อง Hikvision
            port: RTSP port (default: 554)
            username: Username สำหรับ login
            password: Password
            channel: Channel number (default: 1)
            stream_type: "main" (high quality) หรือ "sub" (low quality)
        """
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.channel = channel
        self.stream_type = stream_type
        
        # สร้าง RTSP URL
        self.rtsp_url = self._build_rtsp_url()
        
        self.cap = None
        self.running = False
        self.thread = None
        
        # Latest frame
        self.latest_frame: Optional[np.ndarray] = None
        self.frame_lock = threading.Lock()
        
        # Callback
        self.on_frame_callback: Optional[Callable] = None
        
        # Stats
        self.fps = 0
        self.frame_count = 0
        self.last_fps_time = time.time()
    
    def _build_rtsp_url(self) -> str:
        """
        สร้าง RTSP URL สำหรับ Hikvision
        Format: rtsp://username:password@ip:port/Streaming/Channels/channelID
        """
        if self.stream_type == "main":
            stream_id = f"{self.channel}01"  # Main stream
        else:
            stream_id = f"{self.channel}02"  # Sub stream
        
        url = f"rtsp://{self.username}:{self.password}@{self.host}:{self.port}/Streaming/Channels/{stream_id}"
        return url
    
    def connect(self) -> bool:
        """เชื่อมต่อกับกล้อง"""
        try:
            self.cap = cv2.VideoCapture(self.rtsp_url)
            
            if not self.cap.isOpened():
                print(f"❌ Cannot connect to RTSP: {self.host}")
                return False
            
            # ตั้งค่า buffer ให้ต่ำเพื่อลด latency
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            
            print(f"✅ Hikvision RTSP Connected: {self.host}")
            return True
        
        except Exception as e:
            print(f"❌ RTSP Connection Error: {e}")
            return False
    
    def start_stream(self):
        """เริ่ม streaming"""
        if self.cap and self.cap.isOpened():
            self.running = True
            self.thread = threading.Thread(target=self._stream_loop, daemon=True)
            self.thread.start()
            print(f"🎬 RTSP Streaming Started: {self.host}")
    
    def stop_stream(self):
        """หยุด streaming"""
        self.running = False
        
        if self.thread:
            self.thread.join(timeout=2)
        
        if self.cap:
            self.cap.release()
        
        print(f"⏹️ RTSP Streaming Stopped: {self.host}")
    
    def _stream_loop(self):
        """อ่าน frame ต่อเนื่อง"""
        while self.running:
            try:
                ret, frame = self.cap.read()
                
                if not ret:
                    print(f"⚠️ RTSP Frame read failed: {self.host}")
                    time.sleep(0.1)
                    continue
                
                # Update latest frame
                with self.frame_lock:
                    self.latest_frame = frame.copy()
                
                # Update FPS
                self.frame_count += 1
                current_time = time.time()
                elapsed = current_time - self.last_fps_time
                
                if elapsed >= 1.0:
                    self.fps = self.frame_count / elapsed
                    self.frame_count = 0
                    self.last_fps_time = current_time
                
                # Callback
                if self.on_frame_callback:
                    self.on_frame_callback(frame)
            
            except Exception as e:
                print(f"⚠️ RTSP Stream Error: {e}")
                time.sleep(0.1)
        
        print(f"🔌 RTSP Loop Ended: {self.host}")
    
    def get_latest_frame(self) -> Optional[np.ndarray]:
        """ดึง frame ล่าสุด (thread-safe)"""
        with self.frame_lock:
            return self.latest_frame.copy() if self.latest_frame is not None else None
    
    def set_on_frame_callback(self, callback: Callable):
        """ตั้ง callback เมื่อได้รับ frame ใหม่"""
        self.on_frame_callback = callback
    
    def get_fps(self) -> float:
        """ดึง FPS ปัจจุบัน"""
        return self.fps
    
    def is_connected(self) -> bool:
        """ตรวจสอบว่ายังเชื่อมต่ออยู่หรือไม่"""
        return self.running and self.cap is not None and self.cap.isOpened()
    
    def reconnect(self) -> bool:
        """ลองเชื่อมต่อใหม่"""
        self.stop_stream()
        time.sleep(1)
        
        if self.connect():
            self.start_stream()
            return True
        
        return False


# =============================
# TESTING
# =============================

if __name__ == "__main__":
    # ทดสอบ RTSP stream
    rtsp = HikvisionRTSP(
        host="192.168.1.64",
        username="admin",
        password="admin123",
        stream_type="sub"  # ใช้ sub stream สำหรับทดสอบ (bandwidth ต่ำกว่า)
    )
    
    def on_frame(frame):
        # แสดง frame
        cv2.imshow("Hikvision Live", frame)
        cv2.waitKey(1)
    
    rtsp.set_on_frame_callback(on_frame)
    
    if rtsp.connect():
        rtsp.start_stream()
        
        try:
            while True:
                fps = rtsp.get_fps()
                print(f"FPS: {fps:.1f}", end='\r')
                time.sleep(1)
        
        except KeyboardInterrupt:
            print("\n🛑 Stopping...")
            rtsp.stop_stream()
            cv2.destroyAllWindows()
