
import socket
import os
import re
import time

HOST = "192.168.1.1"
PORT = 5001

BASE_DIR = r"C:\Users\User\Desktop\data"
SLEEP_TIME = 0.5

# รองรับ Shopee Order No. XXXXXXXX
pattern = re.compile(
    r"SHOPEE\s*ORDER\s*NO\.\s*([A-Z0-9]{14})"
)

os.makedirs(BASE_DIR, exist_ok=True)

created_dirs = set()

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind((HOST, PORT))
s.listen(1)
print("Listening on port", PORT)

conn, addr = s.accept()
print("Connected:", addr)

while True:
    data = conn.recv(1024)
    if not data:
        break

    text = data.decode(errors="ignore").strip().upper()
    print("OCR result:", text)

    match = pattern.search(text)
    if match:
        order_no = match.group(1)
        dir_path = os.path.join(BASE_DIR, order_no)

        if not os.path.exists(dir_path):
            os.makedirs(dir_path)
            print(f"📁 Created directory: {dir_path}")
        else:
            print(f"⚠ Directory already exists: {dir_path}")

    time.sleep(SLEEP_TIME)

conn.close()
s.close()
