# -*- coding: utf-8 -*-
import socket
import threading
import time
import json
import base64
import numpy as np
import cv2
from typing import Callable, Optional
import config

class SC2000Driver:
    """
    Driver จัดการการเชื่อมต่อกับกล้อง SC2000 ผ่าน TCP
    ทำหน้าที่รับภาพและผล OCR แล้วส่ง callback กลับไปหา Backend
    """
    def __init__(self, on_data_received: Callable):
        self.host = config.SC2000_IP
        self.port = config.SC2000_PORT
        self.callback = on_data_received
        self.running = False
        self.socket = None
        self.thread = None
        self.connected = False

    def connect(self):
        self.running = True
        self.thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.thread.start()

    def _worker_loop(self):
        while self.running:
            try:
                print(f"🔌 SC2000: Connecting to {self.host}:{self.port}...")
                self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.socket.settimeout(5)
                self.socket.connect((self.host, self.port))
                self.connected = True
                print(f"✅ SC2000: Connected!")

                buffer = b""
                while self.running:
                    try:
                        chunk = self.socket.recv(4096)
                        if not chunk: break
                        buffer += chunk
                        
                        # ใช้ \n\n เป็นตัวจบ Packet (ตาม Simulator)
                        while b"\n\n" in buffer:
                            packet, buffer = buffer.split(b"\n\n", 1)
                            self._process_packet(packet)
                            
                    except socket.timeout:
                        continue
                    except Exception as e:
                        print(f"⚠️ SC2000 Error: {e}")
                        break
            except Exception as e:
                print(f"❌ SC2000 Connection Failed: {e}")
            
            self.connected = False
            if self.running:
                time.sleep(3) # Retry delay

    def _process_packet(self, raw_bytes):
        try:
            data_str = raw_bytes.decode('utf-8')
            json_data = json.loads(data_str)
            
            # ส่งข้อมูลดิบกลับไปให้ Backend ตัดสินใจ
            self.callback(json_data)
        except Exception as e:
            print(f"⚠️ Invalid Packet: {e}")

    def stop(self):
        self.running = False
        if self.socket:
            self.socket.close()