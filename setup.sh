#!/bin/bash

# ==========================================
# PARCEL EVIDENCE SYSTEM - AUTO INSTALLER
# ==========================================

PROJECT_DIR="parcel_evidence_system"
echo "🚀 Starting Setup..."

# 1. ตรวจสอบ Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Error: Docker is not installed. Please install Docker first."
    exit 1
fi

# 2. รับค่า Config จากผู้ใช้
echo "------------------------------------------------"
echo "Please configure your system:"
echo "------------------------------------------------"

read -p "Enter Camera RTSP URL (Context Camera): " USER_RTSP_URL
if [ -z "$USER_RTSP_URL" ]; then
    USER_RTSP_URL="rtsp://admin:123456@192.168.1.65:554/Streaming/Channels/101"
    echo "Using Default: $USER_RTSP_URL"
fi

read -p "Enter Listening Port (Default 5001): " USER_PORT
if [ -z "$USER_PORT" ]; then
    USER_PORT=5001
    echo "Using Default: $USER_PORT"
fi

# 3. สร้าง Directory Project
if [ -d "$PROJECT_DIR" ]; then
    echo "⚠️  Directory '$PROJECT_DIR' exists. Updating files..."
else
    mkdir "$PROJECT_DIR"
    echo "✅ Created directory '$PROJECT_DIR'"
fi

cd "$PROJECT_DIR"

# 4. สร้างไฟล์ app.py
cat << 'EOF' > app.py
import socket
import cv2
import os
import time
import sys
from datetime import datetime

# Environment Variables
STATION_NAME = os.getenv('STATION_NAME', 'Station-1')
LISTEN_PORT = int(os.getenv('LISTEN_PORT', '5001'))
RTSP_URL = os.getenv('RTSP_URL', '')
OUTPUT_DIR = os.getenv('OUTPUT_DIR', '/data')

def log(msg):
    print(f"[{datetime.now()}] [{STATION_NAME}] {msg}", flush=True)

class DockerParcelStation:
    def __init__(self):
        if not RTSP_URL:
            log("❌ Error: RTSP_URL is not set!")
            sys.exit(1)
        self.rtsp_url = RTSP_URL
        self.cap_context = None
        self.running = False

    def connect_camera(self):
        log(f"Connecting to camera...")
        if self.cap_context:
            self.cap_context.release()
        self.cap_context = cv2.VideoCapture(self.rtsp_url)
        self.cap_context.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    def save_evidence(self, order_id):
        clean_id = "".join(x for x in order_id if x.isalnum())
        if not clean_id: return

        log(f"🔔 Triggered! Order ID: {clean_id}")
        folder_path = os.path.join(OUTPUT_DIR, clean_id)
        os.makedirs(folder_path, exist_ok=True)

        if self.cap_context is None or not self.cap_context.isOpened():
            self.connect_camera()

        # Grab frame to clear buffer
        self.cap_context.grab()
        ret, frame = self.cap_context.read()

        if ret:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{folder_path}/{clean_id}_{timestamp}.jpg"
            cv2.putText(frame, f"ID: {clean_id}", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            cv2.imwrite(filename, frame)
            log(f"✅ Saved: {filename}")
        else:
            log("❌ Error: Could not capture frame. Reconnecting...")
            self.connect_camera()

    def run(self):
        self.connect_camera()
        self.running = True
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.bind(('0.0.0.0', LISTEN_PORT))
        server.listen(1)
        log(f"📡 Server listening on port {LISTEN_PORT}...")

        while self.running:
            try:
                client_socket, addr = server.accept()
                with client_socket:
                    while True:
                        data = client_socket.recv(1024)
                        if not data: break
                        raw_data = data.decode('utf-8', errors='ignore').strip()
                        for line in raw_data.splitlines():
                            if line: self.save_evidence(line)
            except Exception as e:
                log(f"Error: {e}")
                time.sleep(1)

if __name__ == "__main__":
    DockerParcelStation().run()
EOF

# 5. สร้างไฟล์ Dockerfile
cat <<EOF > Dockerfile
FROM python:3.9-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN apt-get update && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 && rm -rf /var/lib/apt/lists/*
WORKDIR /app
RUN pip install --no-cache-dir opencv-python-headless
COPY app.py .
CMD ["python", "app.py"]
EOF

# 6. สร้างไฟล์ docker-compose.yml
cat <<EOF > docker-compose.yml
version: '3.8'
services:
  parcel-station:
    build: .
    container_name: parcel_station_ocr
    restart: always
    environment:
      - STATION_NAME=Station-AUTO
      - LISTEN_PORT=$USER_PORT
      - RTSP_URL=$USER_RTSP_URL
      - OUTPUT_DIR=/data
      - TZ=Asia/Bangkok
    ports:
      - "$USER_PORT:$USER_PORT"
    volumes:
      - ./evidence_images:/data
EOF

# 7. สร้าง Script สำหรับถอนการติดตั้ง (เผื่ออยากลบ)
cat <<EOF > uninstall.sh
#!/bin/bash
docker-compose down
echo "Container stopped and removed."
EOF
chmod +x uninstall.sh

# 8. สั่ง Run
echo "------------------------------------------------"
echo "🔨 Building and Starting Docker Container..."
echo "------------------------------------------------"

# เช็คว่าเครื่องใช้ docker compose (v2) หรือ docker-compose (v1)
if docker compose version &> /dev/null; then
    docker compose up -d --build
else
    docker-compose up -d --build
fi

echo "------------------------------------------------"
echo "✅ System is RUNNING!"
echo "   - RTSP URL: $USER_RTSP_URL"
echo "   - Listening Port: $USER_PORT"
echo "   - Images will be saved in: $(pwd)/evidence_images"
echo ""
echo "📝 To check logs: cd $PROJECT_DIR && docker compose logs -f"
echo "🛑 To stop: cd $PROJECT_DIR && ./uninstall.sh"
echo "------------------------------------------------"