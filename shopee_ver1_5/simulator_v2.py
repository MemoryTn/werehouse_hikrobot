# -*- coding: utf-8 -*-
import socket
import json
import time
import random
import base64
import cv2
import numpy as np
import config

def create_dummy_image():
    img = np.zeros((480, 640, 3), dtype=np.uint8)
    cv2.putText(img, f"SIMULATED {time.time()}", (50, 240), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
    _, buf = cv2.imencode('.jpg', img)
    return base64.b64encode(buf).decode('utf-8')

def run_sc2000_sim():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("0.0.0.0", config.SC2000_PORT))
    server.listen(1)
    
    print(f"🤖 Simulator listening on {config.SC2000_PORT}")
    
    while True:
        conn, addr = server.accept()
        print(f"✅ Backend Connected: {addr}")
        
        while True:
            try:
                # 1. Send Image
                msg_img = {
                    "type": "image",
                    "data": create_dummy_image()
                }
                conn.sendall((json.dumps(msg_img) + "\n\n").encode('utf-8'))
                
                # 2. Send OCR (Random success)
                time.sleep(0.5)
                if random.random() > 0.3:
                    order_no = f"SPX{random.randint(1000000000, 9999999999)}"
                    msg_ocr = {
                        "type": "ocr",
                        "data": order_no,
                        "confidence": 0.95
                    }
                else:
                    msg_ocr = {"type": "ocr", "data": "ERROR_READ", "confidence": 0.4}
                
                conn.sendall((json.dumps(msg_ocr) + "\n\n").encode('utf-8'))
                print(f"Sent: {msg_ocr['data']}")
                
                time.sleep(2)
            except:
                break
        conn.close()

if __name__ == "__main__":
    run_sc2000_sim()