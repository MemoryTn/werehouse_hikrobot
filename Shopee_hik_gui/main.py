# -*- coding: utf-8 -*-
import sys
import os
import re
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer
from PyQt5.QtGui import QPixmap
from config import COLORS

# Import Modules
from gui_app import MainUI
from camera_server import CameraServerThread

class AppController:
    def __init__(self):
        self.ui = MainUI()
        
        # Camera Server
        self.camera_server = CameraServerThread()
        
        # Timer (สำหรับ Reset แบบ Manual หรือกรณีต้องการใช้ในอนาคต)
        self.reset_timer = QTimer()
        self.reset_timer.setSingleShot(True)
        self.reset_timer.timeout.connect(self.reset_display)
        
        self.setup_connections()
        self.start_threads()
    
    def setup_connections(self):
        # Camera Server -> Controller
        self.camera_server.order_received.connect(self.handle_new_order)
        self.camera_server.countdown_update.connect(self.handle_countdown)
        self.camera_server.images_captured.connect(self.handle_images_captured)
        self.camera_server.image_retaken.connect(self.handle_image_retaken)
        self.camera_server.log_message.connect(self.ui.log)
        
        # Retake Buttons
        self.ui.btn_retake_all.clicked.connect(self.handle_retake_all)
        for cam in self.ui.hikrobot_cams:
            cam.retake_clicked.connect(self.handle_retake_single)
            
        # 🆕 เชื่อมต่อ Event ปิดโปรแกรม (สำคัญมาก)
        QApplication.instance().aboutToQuit.connect(self.on_exit)
    
    def start_threads(self):
        try:
            self.camera_server.start()
            self.ui.log("🚀 System Started - Camera Server Listening on Port 5020")
            self.ui.log("📡 Waiting for OCR data from SCMVS...")
        except Exception as e:
            self.ui.log(f"❌ Error starting threads: {e}")

    # 🆕 ฟังก์ชันสำหรับปิด Thread เมื่อปิดโปรแกรม
    def on_exit(self):
        print("🛑 Shutting down system...")
        if self.camera_server.isRunning():
            self.camera_server.stop()
        print("✅ Shutdown Complete")
    
    def handle_new_order(self, order_no):
        try:
            self.reset_timer.stop()
            self.ui.reset_pipeline()
            
            self.ui.lbl_result.setText(order_no)
            self.ui.lbl_result.setStyleSheet(f"color:{COLORS['shopee']}; font-size:26px; font-weight:bold; font-family:Consolas; border: 2px solid {COLORS['shopee']}; border-radius: 8px;")
            self.ui.log(f"🔔 NEW ORDER: {order_no}")
            
            self.ui.animate_step('sensor', 'success')
            self.ui.animate_step('sc2000', 'processing')
            
            for cam in self.ui.hikrobot_cams:
                cam.set_active("⏱️ STANDBY", COLORS['warning'], COLORS['warning'])
            
            self.ui.enable_retake_buttons(False)
            
        except Exception as e:
            self.ui.log(f"❌ Error handling order: {e}")
    
    def handle_countdown(self, seconds):
        try:
            if seconds > 0:
                self.ui.show_countdown(seconds)
                for cam in self.ui.hikrobot_cams:
                    cam.set_active(f"⏱️ {seconds}", COLORS['warning'], COLORS['warning'])
            else:
                self.ui.show_countdown(0)
                self.ui.animate_step('sc2000', 'success')
                self.ui.animate_step('hikrobot', 'processing')
                
                for cam in self.ui.hikrobot_cams:
                    cam.set_active("📸 CAPTURING", COLORS['processing'], COLORS['processing'])
        except Exception as e:
            self.ui.log(f"❌ Error in countdown: {e}")
    
    def handle_images_captured(self, image_paths):
        """จัดการเมื่อถ่ายรูปเสร็จ (แสดง Preview และใช้ฟังก์ชัน set_preview_mode)"""
        try:
            self.ui.animate_step('hikrobot', 'success')
            self.ui.animate_step('save', 'success')
            self.ui.update_stats(success=True)
            
            # 1. โหลดและแสดงภาพ
            self.ui.load_and_display_images(image_paths)
            
            # 2. ปรับสถานะเป็น Preview (ไม่ลบรูป)
            self.ui.lbl_result.setStyleSheet(f"color:{COLORS['success']}; font-size:26px; font-weight:bold; font-family:Consolas; border: 2px solid {COLORS['success']}; border-radius: 8px;")
            
            for cam in self.ui.hikrobot_cams:
                cam.set_preview_mode("PREVIEW", COLORS['processing'])
            
            self.ui.enable_retake_buttons(True)
            self.ui.current_order_no = self.camera_server.current_order_no
            
            self.ui.log("⏳ Previewing... (Waiting for new order)")
            
        except Exception as e:
            self.ui.log(f"❌ Error handling captured images: {e}")
    
    def handle_image_retaken(self, image_path):
        """จัดการเมื่อถ่ายรูปใหม่เสร็จ (กล้องเดียว)"""
        try:
            match = re.search(r'cam(\d+)_', image_path)
            if match:
                cam_idx = int(match.group(1)) - 1
                if cam_idx < len(self.ui.hikrobot_cams):
                    pixmap = QPixmap(image_path)
                    if not pixmap.isNull():
                        from PyQt5.QtCore import Qt
                        scaled = pixmap.scaled(
                            self.ui.hikrobot_cams[cam_idx].screen.size(),
                            Qt.KeepAspectRatio,
                            Qt.SmoothTransformation
                        )
                        self.ui.hikrobot_cams[cam_idx].screen.setPixmap(scaled)
                        
                        # ใช้ set_preview_mode เพื่ออัปเดตสถานะโดยไม่ลบรูป
                        self.ui.hikrobot_cams[cam_idx].set_preview_mode("UPDATED", COLORS['success'])
                        self.ui.log(f"🔄 Retaken cam {cam_idx + 1} Success")
                        
                        self.ui.hikrobot_cams[cam_idx].enable_retake(True)
        except Exception as e:
            self.ui.log(f"❌ Error handling retaken image: {e}")
    
    def handle_retake_single(self, camera_index):
        try:
            self.ui.log(f"🔄 Retaking camera {camera_index + 1}...")
            # แจ้งสถานะ แต่อย่าเพิ่งลบรูป (หรือจะให้ขึ้นข้อความทับก็ได้ แล้วแต่ดีไซน์)
            # ในที่นี้ใช้ set_active ซึ่งจะขึ้นข้อความทับรูประหว่างถ่าย เพื่อให้รู้ว่ากำลังถ่ายใหม่
            self.ui.hikrobot_cams[camera_index].set_active("📸 RETAKING", COLORS['warning'], COLORS['warning'])
            self.ui.hikrobot_cams[camera_index].enable_retake(False)
            
            self.camera_server.retake_camera(camera_index)
        except Exception as e:
            self.ui.log(f"❌ Error retaking single camera: {e}")
    
    def handle_retake_all(self):
        try:
            self.ui.log("🔄 Retaking all cameras...")
            self.ui.enable_retake_buttons(False)
            
            for cam in self.ui.hikrobot_cams:
                cam.set_active("📸 RETAKING", COLORS['warning'], COLORS['warning'])
            
            self.camera_server.retake_all()
        except Exception as e:
            self.ui.log(f"❌ Error retaking all: {e}")
    
    def reset_display(self):
        try:
            self.ui.log("Display Reset")
            self.ui.reset_pipeline()
            self.ui.enable_retake_buttons(False)
            self.ui.current_order_no = None
            self.camera_server.current_order_no = None
            
            for cam in self.ui.hikrobot_cams:
                cam.set_active("READY", COLORS['text_dim'], COLORS['border'])
        except Exception as e:
            self.ui.log(f"❌ Error resetting display: {e}")
    
    def run(self):
        self.ui.show()

if __name__ == "__main__":
    try:
        app = QApplication(sys.argv)
        controller = AppController()
        controller.run()
        sys.exit(app.exec_())
    except Exception as e:
        print(f"❌ Fatal Error: {e}")
        import traceback
        traceback.print_exc()