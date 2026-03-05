# -*- coding: utf-8 -*-
"""
main.py – AppController v4.0
==============================
Layout:
  บนซ้าย  → SC2000 RTSP (front)  LiveFeedCard
  บนขวา   → Hikvision RTSP        LiveFeedCard
  ล่าง 4  → Hikrobot snapshot      SnapshotCard  (retake ได้)

Startup:
  1. LiveFeedThread เปิด RTSP ทั้งสอง
  2. CameraServerThread รอ OCR → trigger Hikrobot capture
"""

import sys
import os
import re
from PyQt5.QtWidgets import QApplication, QMessageBox
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QPixmap, QImage
from config import COLORS

from gui_app import MainUI
from camera_server import CameraServerThread
from live_feed import LiveFeedThread
from recorder import HikvisionRecorder


class AppController:
    def __init__(self):
        self.ui = MainUI()

        self.live_feed     = LiveFeedThread(num_cams=4, fps_limit=15)
        self.camera_server = CameraServerThread()
        self.recorder       = HikvisionRecorder(log_callback=self.ui.log)

        self.reset_timer = QTimer()
        self.reset_timer.setSingleShot(True)
        self.reset_timer.timeout.connect(self.reset_display)

        self._snapshot_mode = False   # True ขณะแสดง snapshot

        self.setup_connections()
        self.start_threads()

    # ── Signal wiring ─────────────────────────────────────────────────────────

    def setup_connections(self):
        # Live feed frames
        self.live_feed.sc2000_frame.connect(self._on_sc2000_frame)
        self.live_feed.hikvision_frame.connect(self._on_hikvision_frame)
        self.live_feed.cameras_ready.connect(self._on_cameras_ready)
        self.live_feed.log_message.connect(self.ui.log)

        # Camera server
        self.camera_server.order_received.connect(self.handle_new_order)
        self.camera_server.countdown_update.connect(self.handle_countdown)
        self.camera_server.images_captured.connect(self.handle_images_captured)
        self.camera_server.image_retaken.connect(self.handle_image_retaken)
        self.camera_server.log_message.connect(self.ui.log)
        self.camera_server.manual_duplicate.connect(self.handle_manual_duplicate)

        # Retake buttons
        self.ui.btn_retake_all.clicked.connect(self.handle_retake_all)
        for cam in self.ui.hikrobot_cams:
            cam.retake_clicked.connect(self.handle_retake_single)
            
        # 📌 Manual Input เชื่อมสัญญาณปุ่มและช่องใส่ Text
        self.ui.btn_manual.clicked.connect(self.handle_manual_submit)
        self.ui.txt_manual.returnPressed.connect(self.handle_manual_submit) # กด Enter ได้

        # 📌 Order ID Input เชื่อมสัญญาณปุ่มและช่องใส่ Text
        self.ui.btn_order.clicked.connect(self.handle_order_submit)
        self.ui.txt_order.returnPressed.connect(self.handle_order_submit) # กด Enter ได้

        # Shutdown
        QApplication.instance().aboutToQuit.connect(self.on_exit)

    # ── Startup ───────────────────────────────────────────────────────────────

    def start_threads(self):
        self.live_feed.start()
        self.camera_server.start()
        self.ui.log("🚀 System Started")
        self.ui.log("🎥 Live Feed starting (SC2000 + Hikvision)…")
        self.ui.log("📡 Waiting for OCR on port 5020…")

    def _on_cameras_ready(self, cameras: list):
        self.ui.log(f"🔗 LiveFeed ready (Hikrobot handles managed by CameraServer)")

    # ── Frame handlers ────────────────────────────────────────────────────────

    def _on_sc2000_frame(self, qt_image: QImage):
        self.ui.feed_sc2000.update_frame(qt_image)

    def _on_hikvision_frame(self, qt_image: QImage):
        self.ui.feed_hikvision.update_frame(qt_image)

    # ── Shutdown ──────────────────────────────────────────────────────────────

    def on_exit(self):
        print("🛑 Shutting down…")
        self.recorder.stop_record()
        self.live_feed.stop()
        if self.camera_server.isRunning():
            self.camera_server.stop()
        print("✅ Done")

    # ── Order handling ────────────────────────────────────────────────────────
    
    def handle_manual_submit(self):
            """รับค่าจาก GUI จัดการสถานะปุ่ม อัดวิดีโอ / หยุดอัด"""
            btn_text = self.ui.btn_manual.text().strip()
            plate_no = self.ui.txt_manual.text().strip().upper()
            
            # 🔴 กรณี: กำลังจะกดเพื่อ "เริ่มอัด"
            if "CONFIRM" in btn_text or "ยืนยัน" in btn_text:
                
                # ป้องกันค่าว่าง
                if not plate_no:
                    msg_box = QMessageBox(self.ui)
                    msg_box.setIcon(QMessageBox.Warning)
                    msg_box.setWindowTitle("⚠️ แจ้งเตือน")
                    msg_box.setText("กรุณากรอกทะเบียนรถก่อนกดยืนยัน")
                    msg_box.setStyleSheet(f"QMessageBox {{ background-color: {COLORS['bg_card']}; }} QLabel {{ color: white; font-weight: bold; min-width: 300px; }} QPushButton {{ background-color: {COLORS['primary']}; color: white; border: none; padding: 8px 30px; font-weight: 900; }}")
                    msg_box.exec_()
                    self.ui.txt_manual.setFocus()
                    return
                    
                # 1. สั่งเริ่มอัดวิดีโอ RTSP
                success, msg = self.recorder.start_record(plate_no)
                
                if success:
                    # 2. เปลี่ยนปุ่มเป็นสีแดง "หยุดอัด" และล็อคช่องพิมพ์
                    self.ui.btn_manual.setText("⏹️ STOP RECORD")
                    self.ui.btn_manual.setStyleSheet(f"""
                        QPushButton {{
                            background-color: #d32f2f; 
                            color: white; 
                            border: none; 
                            border-radius: 2px; 
                            padding: 0px 20px; 
                            font-size: 14px;
                            font-weight: 900;
                            letter-spacing: 1px;
                        }}
                        QPushButton:hover {{ background-color: #ff3333; }}
                    """)
                    self.ui.txt_manual.setEnabled(False)
                    self.ui.txt_order.setEnabled(False)
                    self.ui.btn_order.setEnabled(False)
                
            # 🟢 กรณี: กำลังอัดอยู่ และกดเพื่อ "หยุดอัด / เสร็จสิ้น"
            elif "STOP" in btn_text or "หยุด" in btn_text:
                
                # 1. สั่งคลาส Recorder ให้หยุดอัดและเซฟไฟล์
                self.recorder.stop_record()
                
                # 2. คืนค่าปุ่มให้กลับเป็นโหมดปกติ (สีม่วง)
                self.ui.txt_manual.clear()
                self.ui.txt_manual.setEnabled(True)
                self.ui.txt_manual.setFocus()
                self.ui.txt_order.setEnabled(True)
                self.ui.btn_order.setEnabled(True)
                
                self.ui.btn_manual.setText("🚗 CONFIRM")
                self.ui.btn_manual.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {COLORS['primary']}; 
                        color: white; 
                        border: none; 
                        border-radius: 2px; 
                        padding: 0px 20px; 
                        font-size: 12px;
                        font-weight: 900;
                        letter-spacing: 1px;
                    }}
                    QPushButton:hover {{ background-color: {COLORS['active_bg']}; }}
                """)
                
                # 3. เคลียร์หน้าจอทั้งหมดเพื่อพร้อมรับคันต่อไป
                self.reset_display()

    def handle_order_submit(self):
        """รับค่าจาก Order ID (แบบดั้งเดิม: พิมพ์แล้วส่งค่าเลย ไม่ต้องรอเสร็จสิ้น)"""
        order_no = self.ui.txt_order.text().strip().upper()
        
        # ป้องกันค่าว่าง
        if not order_no:
            return
            
        # 📌 ตรวจสอบความยาวของ Order ID ต้องเท่ากับ 14 ตัวอักษร
        if len(order_no) != 14:
            msg_box = QMessageBox(self.ui)
            msg_box.setIcon(QMessageBox.Warning)
            msg_box.setWindowTitle("⚠️ แจ้งเตือน")
            msg_box.setText("กรุณากรอก Order ID ให้ครบ 14 หลัก")
            msg_box.setStyleSheet(f"""
                QMessageBox {{
                    background-color: {COLORS['bg_card']};
                }}
                QLabel {{
                    color: white;
                    font-size: 14px;
                    font-weight: bold;
                    min-width: 300px;
                }}
                QPushButton {{
                    background-color: {COLORS['primary']}; 
                    color: white; 
                    border: none; 
                    border-radius: 2px; 
                    padding: 8px 30px; 
                    font-size: 12px;
                    font-weight: 900;
                }}
                QPushButton:hover {{ 
                    background-color: {COLORS['active_bg']}; 
                }}
            """)
            msg_box.exec_()
            self.ui.txt_order.setFocus()
            return
            
        # ล้างช่องข้อความ
        self.ui.txt_order.clear()
        
        # ส่งไป Trigger กระบวนการนับถอยหลังและถ่ายภาพใน Thread หลังบ้าน
        self.camera_server.trigger_manual(order_no)

    def handle_manual_duplicate(self, message):
        self.ui.log(f"⚠️ Pop-up Alert: {message.replace(chr(10), ' ')}")
        
        msg_box = QMessageBox(self.ui)
        msg_box.setIcon(QMessageBox.Warning)
        msg_box.setWindowTitle("⚠️ แจ้งเตือนข้อมูลซ้ำ")
        msg_box.setText(message)
        
        msg_box.setStyleSheet(f"""
            QMessageBox {{
                background-color: {COLORS['bg_card']};
            }}
            QLabel {{
                color: white;
                font-size: 14px;
                font-weight: bold;
                min-width: 350px;
                min-height: 80px;
            }}
            QPushButton {{
                background-color: {COLORS['primary']}; 
                color: white; 
                border: none; 
                border-radius: 2px; 
                padding: 8px 30px; 
                font-size: 12px;
                font-weight: 900;
            }}
            QPushButton:hover {{ 
                background-color: {COLORS['active_bg']}; 
            }}
        """)
        msg_box.exec_()

        # กรณีแจ้งเตือนข้อมูลซ้ำ ให้รีเซ็ตปุ่มกลับเป็น "ยืนยัน" พร้อมอิโมจิ
        self.ui.txt_manual.setEnabled(True)
        self.ui.btn_manual.setEnabled(True)
        self.ui.btn_manual.setText("🚗 CONFIRM")
        self.ui.btn_manual.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['primary']}; 
                color: white; 
                border: none; 
                border-radius: 2px; 
                padding: 0px 20px; 
                font-size: 12px;
                font-weight: 900;
                letter-spacing: 1px;
            }}
            QPushButton:hover {{ background-color: {COLORS['active_bg']}; }}
        """)

        self.ui.txt_order.setEnabled(True)
        self.ui.btn_order.setEnabled(True)
        self.ui.btn_order.setText("📦 CONFIRM")
        self.ui.btn_order.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['shopee']}; 
                color: white; 
                border: none; 
                border-radius: 2px; 
                padding: 0px 20px; 
                font-size: 12px;
                font-weight: 900;
                letter-spacing: 1px;
            }}
            QPushButton:hover {{ background-color: #ff6644; }}
        """)

    def handle_new_order(self, order_no):
        try:
            self.reset_timer.stop()
            self.ui.reset_pipeline()

            self.ui.lbl_result.setText(order_no)
            self.ui.lbl_result.setStyleSheet(
                f"color:{COLORS['shopee']}; font-size:40px; font-weight:900;"
                f" font-family:Consolas; background-color: #050508; border:2px solid {COLORS['shopee']}; border-radius:2px; letter-spacing: 2px;"
            )
            self.ui.log(f"🔔 NEW TARGET PROCESSING: {order_no}")

            for cam in self.ui.hikrobot_cams:
                cam.set_status("■ STANDBY", COLORS["warning"])
            self._snapshot_mode = False

        except Exception as e:
            self.ui.log(f"❌ handle_new_order: {e}")

    def handle_countdown(self, seconds):
        try:
            if seconds > 0:
                self.ui.show_countdown(seconds)
                for cam in self.ui.hikrobot_cams:
                    cam.set_status(f"⏱️ {seconds}", COLORS["warning"])
            else:
                self.ui.show_countdown(0)
                for cam in self.ui.hikrobot_cams:
                    cam.set_status("📸 CAPTURING", COLORS["processing"])

        except Exception as e:
            self.ui.log(f"❌ handle_countdown: {e}")

    def handle_images_captured(self, image_paths):
        try:
            self.ui.update_stats()

            # โหลดรูปลง SnapshotCard ทั้ง 4
            self.ui.load_and_display_images(image_paths)

            self.ui.lbl_result.setStyleSheet(
                f"color:{COLORS['success']}; font-size:40px; font-weight:900;"
                f" font-family:Consolas; background-color: #050508; border:2px solid {COLORS['success']}; border-radius:2px; letter-spacing: 2px;"
            )
            for cam in self.ui.hikrobot_cams:
                cam.set_preview_mode("PREVIEW", COLORS["processing"])

            self.ui.enable_retake_buttons(True)
            self.ui.current_order_no = self.camera_server.current_order_no
            self._snapshot_mode = True
            self.ui.log("✅ Captured – RTSP feeds still running")

        except Exception as e:
            self.ui.log(f"❌ handle_images_captured: {e}")

    def handle_image_retaken(self, image_path):
        try:
            match = re.search(r"cam(\d+)_", image_path)
            if match:
                cam_idx = int(match.group(1)) - 1
                if 0 <= cam_idx < len(self.ui.hikrobot_cams):
                    self.ui.hikrobot_cams[cam_idx].show_image(image_path)
                    self.ui.hikrobot_cams[cam_idx].set_preview_mode("UPDATED", COLORS["success"])
                    self.ui.hikrobot_cams[cam_idx].enable_retake(True)
                    self.ui.log(f"🔄 Retaken cam{cam_idx+1} OK")
        except Exception as e:
            self.ui.log(f"❌ handle_image_retaken: {e}")

    # ── Retake ────────────────────────────────────────────────────────────────

    def handle_retake_single(self, camera_index):
        try:
            self.ui.hikrobot_cams[camera_index].set_status("📸 RETAKING", COLORS["warning"])
            self.ui.hikrobot_cams[camera_index].enable_retake(False)
            self.camera_server.retake_camera(camera_index)
        except Exception as e:
            self.ui.log(f"❌ handle_retake_single: {e}")

    def handle_retake_all(self):
        try:
            self.ui.enable_retake_buttons(False)
            for cam in self.ui.hikrobot_cams:
                cam.set_status("📸 RETAKING", COLORS["warning"])
            self.camera_server.retake_all()
        except Exception as e:
            self.ui.log(f"❌ handle_retake_all: {e}")

    # ── Reset ─────────────────────────────────────────────────────────────────

    def reset_display(self):
        try:
            self.ui.reset_pipeline()
            self.ui.enable_retake_buttons(False)
            self.ui.current_order_no = None
            self.camera_server.current_order_no = None
            self._snapshot_mode = False
            self.ui.log("↺ Display reset")
        except Exception as e:
            self.ui.log(f"❌ reset_display: {e}")

    def run(self):
        self.ui.show()


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    try:
        app = QApplication(sys.argv)
        controller = AppController()
        controller.run()
        sys.exit(app.exec_())
    except Exception as e:
        print(f"❌ Fatal: {e}")
        import traceback
        traceback.print_exc()