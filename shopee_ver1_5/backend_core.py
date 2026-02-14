# -*- coding: utf-8 -*-
import socket
import threading
import json
import time
import os
import base64
import config
from datetime import datetime
from sc2000_driver import SC2000Driver

# Mock Hikrobot Import (กรณีไม่มี SDK จริง)
try:
    from MvImport.MvCameraControl_class import *
    HIKROBOT_AVAILABLE = True
except ImportError:
    HIKROBOT_AVAILABLE = False
    print("⚠️ Hikrobot SDK not found. Running in simulation mode for side cameras.")

class BackendServer:
    def __init__(self):
        self.clients = [] # GUI Clients
        self.lock = threading.Lock()
        
        # 1. Init SC2000 Driver
        self.sc2000 = SC2000Driver(on_data_received=self.handle_sc2000_data)
        
        # 2. Init GUI Broadcaster
        self.broadcast_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.broadcast_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.broadcast_sock.bind(("0.0.0.0", config.GUI_BROADCAST_PORT))
        self.broadcast_sock.listen(5)
        
        # State
        self.last_order = None
        
    def start(self):
        print(f"🚀 Backend Started.")
        print(f"   - GUI Port: {config.GUI_BROADCAST_PORT}")
        print(f"   - SC2000 Target: {config.SC2000_IP}")
        
        # Start Threads
        threading.Thread(target=self.gui_accept_loop, daemon=True).start()
        self.sc2000.connect()
        
        # Keep main thread alive
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.sc2000.stop()
            print("\n🛑 Shutting down...")

    # ================= GUI COMMUNICATION =================
    def gui_accept_loop(self):
        while True:
            client, addr = self.broadcast_sock.accept()
            print(f"🖥️ GUI Connected: {addr}")
            with self.lock:
                self.clients.append(client)
                
            # Send initial status
            self.send_to_gui("system_status", {"status": "ready", "hikrobot": HIKROBOT_AVAILABLE})

    def send_to_gui(self, msg_type, data):
        """ส่ง JSON ไปหา GUI"""
        payload = {
            "type": msg_type,
            "data": data,
            "timestamp": datetime.now().isoformat()
        }
        msg = json.dumps(payload) + "\n"
        
        with self.lock:
            dead_clients = []
            for client in self.clients:
                try:
                    client.sendall(msg.encode('utf-8'))
                except:
                    dead_clients.append(client)
            for d in dead_clients:
                self.clients.remove(d)

    # ================= LOGIC HANDLERS =================
    def handle_sc2000_data(self, data):
        """รับข้อมูลจาก SC2000 แล้วตัดสินใจ"""
        msg_type = data.get("type")
        
        if msg_type == "image":
            # Pass-through image to GUI immediately (Real-time view)
            self.send_to_gui("live_image", {"image": data["data"]})
            
        elif msg_type == "ocr":
            text = data.get("data", "")
            confidence = data.get("confidence", 0.0)
            
            # Logic 1: ส่งผลดิบไป GUI ก่อน
            self.send_to_gui("ocr_result", {
                "text": text,
                "confidence": confidence,
                "is_valid": confidence >= config.SC2000_CONFIDENCE_THRESHOLD
            })
            
            # Logic 2: ถ้ามั่นใจสูง -> Trigger ระบบอื่น
            if confidence >= config.SC2000_CONFIDENCE_THRESHOLD:
                self.process_successful_scan(text)

    def process_successful_scan(self, order_no):
        # 1. Check Duplicate
        save_path = os.path.join(config.IMAGE_DIR, order_no)
        if os.path.exists(save_path):
            print(f"⚠️ Duplicate Order: {order_no}")
            self.send_to_gui("process_step", {"step": "duplicate", "status": "warning"})
            return

        print(f"✅ New Order: {order_no}")
        self.send_to_gui("process_step", {"step": "new_order", "order_no": order_no})

        # 2. Trigger Hikrobot (Side Cameras)
        self.trigger_side_cameras(order_no)

        # 3. Save Data (Mock Save)
        os.makedirs(save_path, exist_ok=True)
        self.send_to_gui("process_step", {"step": "save", "status": "success"})
        
        # 4. Finish
        self.send_to_gui("job_complete", {"order_no": order_no})

    def trigger_side_cameras(self, order_no):
        """สั่งถ่ายภาพกล้องข้าง (Hikrobot)"""
        self.send_to_gui("process_step", {"step": "hikrobot", "status": "processing"})
        
        if HIKROBOT_AVAILABLE:
            # ใส่โค้ด Trigger Hardware จริงที่นี่
            pass
        else:
            # Mock delay
            time.sleep(0.5)
            
        self.send_to_gui("process_step", {"step": "hikrobot", "status": "success"})

if __name__ == "__main__":
    server = BackendServer()
    server.start()