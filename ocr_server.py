# -*- coding: utf-8 -*-
import socket
import re
import time
from PyQt5.QtCore import QThread, pyqtSignal
from config import SERVER_IP, SERVER_PORT

class OCRServerThread(QThread):
    order_received = pyqtSignal(str)
    log_message = pyqtSignal(str)

    def run(self):
        self.running = True
        # Regex สำหรับ Shopee Order (14 หลัก)
        order_pattern = re.compile(r"Shopee\s*Order\s*No\.?\s*([A-Z0-9]{14})", re.I)

        while self.running:
            try:
                server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                server.bind((SERVER_IP, SERVER_PORT))
                server.listen(1)
                self.log_message.emit(f"📡 Server Listening on {SERVER_PORT}")

                while self.running:
                    server.settimeout(1.0)
                    try:
                        conn, addr = server.accept()
                    except socket.timeout:
                        continue
                    except:
                        break

                    self.log_message.emit(f"🔗 Client Connected: {addr[0]}")
                    with conn:
                        while self.running:
                            data = conn.recv(1024)
                            if not data: break
                            
                            text = data.decode("utf-8", errors="ignore")
                            for line in text.splitlines():
                                match = order_pattern.search(line)
                                if match:
                                    order_no = match.group(1).upper()
                                    if not order_no.isdigit(): # ต้องมีตัวอักษรผสม
                                        self.order_received.emit(order_no)
                                    else:
                                        self.log_message.emit(f"⚠️ Ignored Digit-Only: {order_no}")
                    
                    self.log_message.emit("Disconnected")

                server.close()

            except Exception as e:
                self.log_message.emit(f"❌ Server Error: {e}")
                time.sleep(5)

    def stop(self):
        self.running = False
        self.wait()