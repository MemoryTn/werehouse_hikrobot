# -*- coding: utf-8 -*-
import sys
import os
from datetime import datetime
from PyQt5.QtWidgets import *
from PyQt5.QtGui import QFont, QPixmap
from PyQt5.QtCore import Qt, pyqtSignal, QTimer, QTime

# ========== IMPORT CONFIG จากไฟล์ภายนอก ==========
from config import COLORS, FONTS

# ========== Custom Widgets ==========

class StatBox(QFrame):
    def __init__(self, title, value_color):
        super().__init__()
        self.setStyleSheet(f"QFrame {{ background-color: {COLORS['bg_card']}; border-radius: 10px; border: 1px solid {COLORS['border']}; }}")
        self.setFrameShape(QFrame.StyledPanel)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(2)
        
        self.val = QLabel("0")
        self.val.setAlignment(Qt.AlignCenter)
        self.val.setStyleSheet(f"color: {value_color}; font-size: 24px; font-weight: 800; font-family: {FONTS['mono']}; border: none; background: transparent;")
        
        lbl = QLabel(title)
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setWordWrap(True)
        lbl.setStyleSheet(f"color: {COLORS['text_dim']}; font-size: 11px; font-weight: bold; border: none; background: transparent;")
        
        layout.addWidget(self.val)
        layout.addWidget(lbl)

class PipelineStep(QFrame):
    def __init__(self, step_id, title_th, title_en):
        super().__init__()
        self.default_style = "background-color: transparent; border-radius: 6px; border: 1px solid transparent;"
        self.active_style = f"background-color: {COLORS['bg_input']}; border-radius: 6px; border: 1px solid {COLORS['processing']};"
        
        self.setStyleSheet(self.default_style)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(15)
        
        self.icon = QLabel("○")
        self.icon.setFont(QFont(FONTS['main'], 14))
        self.icon.setStyleSheet(f"color: {COLORS['text_dim']}; border: none; background: transparent;")
        self.icon.setFixedWidth(24)
        self.icon.setAlignment(Qt.AlignCenter)
        
        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)
        
        self.lbl_th = QLabel(f"{step_id}. {title_th}")
        self.lbl_th.setStyleSheet(f"color: {COLORS['text_dim']}; font-size: 13px; font-weight: 600; border: none; background: transparent;")
        
        self.lbl_en = QLabel(title_en)
        self.lbl_en.setStyleSheet(f"color: {COLORS['text_dim']}; font-size: 10px; border: none; background: transparent;")
        
        text_layout.addWidget(self.lbl_th)
        text_layout.addWidget(self.lbl_en)
        
        layout.addWidget(self.icon)
        layout.addLayout(text_layout)
        layout.addStretch()
        
    def set_status(self, status):
        if status == 'processing':
            self.setStyleSheet(self.active_style)
            self.icon.setText("➤")
            self.icon.setStyleSheet(f"color: {COLORS['processing']}; font-weight: bold; border: none; background: transparent;")
            self.lbl_th.setStyleSheet(f"color: {COLORS['text']}; font-weight: bold; font-size: 13px; border: none; background: transparent;")
            self.lbl_en.setStyleSheet(f"color: {COLORS['processing']}; font-size: 10px; border: none; background: transparent;")
        elif status == 'success':
            self.setStyleSheet(self.default_style)
            self.icon.setText("✓")
            self.icon.setStyleSheet(f"color: {COLORS['success']}; font-weight: bold; border: none; background: transparent;")
            self.lbl_th.setStyleSheet(f"color: {COLORS['text']}; font-size: 13px; border: none; background: transparent;")
            self.lbl_en.setStyleSheet(f"color: {COLORS['success']}; font-size: 10px; border: none; background: transparent;")
        elif status == 'error':
            self.setStyleSheet(self.default_style)
            self.icon.setText("✕")
            self.icon.setStyleSheet(f"color: {COLORS['error']}; font-weight: bold; border: none; background: transparent;")
            self.lbl_th.setStyleSheet(f"color: {COLORS['text']}; font-size: 13px; border: none; background: transparent;")
            self.lbl_en.setStyleSheet(f"color: {COLORS['error']}; font-size: 10px; border: none; background: transparent;")
        else:
            self.setStyleSheet(self.default_style)
            self.icon.setText("○")
            self.icon.setStyleSheet(f"color: {COLORS['text_dim']}; border: none; background: transparent;")
            self.lbl_th.setStyleSheet(f"color: {COLORS['text_dim']}; font-size: 13px; border: none; background: transparent;")
            self.lbl_en.setStyleSheet(f"color: {COLORS['text_dim']}; font-size: 10px; border: none; background: transparent;")

class CameraCard(QFrame):
    retake_clicked = pyqtSignal(int)
    
    def __init__(self, title, icon, camera_index=0, is_main=False):
        super().__init__()
        self.is_main = is_main
        self.camera_index = camera_index
        
        self.setStyleSheet(f"QFrame {{ background-color: {COLORS['bg_card']}; border: 1px solid {COLORS['border']}; border-radius: 8px; }}")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(5)
        
        header = QHBoxLayout()
        lbl_title = QLabel(f"{icon} {title}")
        lbl_title.setStyleSheet(f"color: {COLORS['text']}; font-size: {'14px' if is_main else '11px'}; font-weight: bold; border: none; background: transparent;")
        header.addWidget(lbl_title)
        
        self.status_dot = QLabel("● STANDBY")
        self.status_dot.setStyleSheet(f"color: {COLORS['text_dim']}; font-size: 9px; font-weight: bold; border: none; background: transparent;")
        header.addWidget(self.status_dot, 0, Qt.AlignRight)
        
        layout.addLayout(header)
        
        self.screen = QLabel("NO SIGNAL")
        self.screen.setAlignment(Qt.AlignCenter)
        self.screen.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Expanding)
        self.screen.setMinimumSize(120, 90)
        self.screen.setStyleSheet(f"background-color: #000; color: {COLORS['text_dim']}; border: 2px solid {COLORS['border']}; border-radius: 6px; font-size: {'20px' if is_main else '12px'};")
            
        layout.addWidget(self.screen, stretch=1)
        
        if not is_main:
            self.btn_retake = QPushButton("🔄 Retake")
            self.btn_retake.setCursor(Qt.PointingHandCursor)
            self.btn_retake.setStyleSheet(f"""
                QPushButton {{ background-color: {COLORS['bg_input']}; color: {COLORS['text']}; border: 1px solid {COLORS['border']}; border-radius: 4px; padding: 4px; font-size: 10px; font-weight: bold; }}
                QPushButton:hover {{ background-color: {COLORS['warning']}; color: #222; border: 1px solid {COLORS['warning']}; }}
                QPushButton:disabled {{ background-color: {COLORS['bg_card']}; color: {COLORS['text_dim']}; border: 1px solid {COLORS['border']}; }}
            """)
            self.btn_retake.clicked.connect(lambda: self.retake_clicked.emit(self.camera_index))
            self.btn_retake.setEnabled(False)
            layout.addWidget(self.btn_retake)

    def set_active(self, text, color=None, border_color=None):
        if color is None:
            color = COLORS['text_dim']
        if border_color is None:
            border_color = COLORS['border']
            
        self.screen.setText(text)
        self.screen.setStyleSheet(f"background-color: #000; color: {color}; border: 2px solid {border_color}; border-radius: 6px; font-size: {'28px' if self.is_main else '14px'}; font-weight: bold;")
        
        if color == COLORS['processing']:
            self.status_dot.setText("⚡ CAPTURING")
            self.status_dot.setStyleSheet(f"color: {COLORS['processing']}; font-weight: bold; border: none; background: transparent;")
        elif color == COLORS['success']:
            self.status_dot.setText("✅ LIVE")
            self.status_dot.setStyleSheet(f"color: {COLORS['success']}; font-weight: bold; border: none; background: transparent;")
        elif "RETAKING" in str(text).upper():
            self.status_dot.setText("🔄 RETAKING")
            self.status_dot.setStyleSheet(f"color: {COLORS['warning']}; font-weight: bold; border: none; background: transparent;")
        else:
            self.status_dot.setText("● STANDBY")
            self.status_dot.setStyleSheet(f"color: {COLORS['text_dim']}; font-weight: bold; border: none; background: transparent;")

    def set_preview_mode(self, text_status="PREVIEW", color=COLORS['success']):
        """ 🆕 เข้าสู่โหมด Preview: เปลี่ยนสีกรอบและสถานะ แต่ **ไม่ลบรูป** """
        self.screen.setStyleSheet(f"""
            background-color: #000;
            border: 2px solid {color};
            border-radius: 6px;
        """)
        
        self.status_dot.setText(f"👁️ {text_status}")
        self.status_dot.setStyleSheet(f"color: {color}; font-weight: bold; border: none; background: transparent;")

    def update_frame(self, qt_image):
        if qt_image.isNull():
            return
        pixmap = QPixmap.fromImage(qt_image)
        w, h = self.screen.width(), self.screen.height()
        if w > 10 and h > 10:
            self.screen.setPixmap(pixmap.scaled(w, h, Qt.KeepAspectRatio, Qt.SmoothTransformation))
    
    def enable_retake(self, enabled=True):
        if hasattr(self, 'btn_retake'):
            self.btn_retake.setEnabled(enabled)

class MainUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Shopee Express - Smart Sorting System v3.4")
        self.resize(1366, 768)
        self.setMinimumSize(1024, 600)
        self.setStyleSheet(f"background-color: {COLORS['bg_app']};")
        
        self.total_count = 0
        self.success_count = 0
        self.pipeline_steps = {}
        self.current_order_no = None
        
        self.setup_ui()

    def setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)
        
        # Left: Cameras
        left_layout = QVBoxLayout()
        left_layout.setSpacing(10)
        
        self.cam_main = CameraCard("SC2000 Smart Camera (OCR)", "📸", camera_index=-1, is_main=True)
        self.cam_main.set_active("NOT CONNECTED")
        left_layout.addWidget(self.cam_main, stretch=6)
        
        bottom_layout = QHBoxLayout()
        bottom_layout.setSpacing(8)
        
        self.hikrobot_cams = []
        for i in range(4):
            cam = CameraCard(f"Hikrobot-{i+1}", "👁️", camera_index=i)
            self.hikrobot_cams.append(cam)
            bottom_layout.addWidget(cam, stretch=1)
            
        left_layout.addLayout(bottom_layout, stretch=4)
        main_layout.addLayout(left_layout, stretch=65)

        # Right: Info
        right_scroll = QScrollArea()
        right_scroll.setWidgetResizable(True)
        right_scroll.setFrameShape(QFrame.NoFrame)
        right_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        right_scroll.setStyleSheet("background: transparent; border: none;")
        
        right_content = QWidget()
        right_layout = QVBoxLayout(right_content)
        right_layout.setContentsMargins(0, 0, 5, 0)
        right_layout.setSpacing(12)
        
        # Header
        header_card = QFrame()
        header_card.setStyleSheet(f"background-color: {COLORS['bg_card']}; border-radius: 10px; border: 1px solid {COLORS['border']};")
        header_card.setFixedHeight(85)
        
        h_layout = QHBoxLayout(header_card)
        h_layout.setContentsMargins(15, 5, 15, 5)
        
        status_container = QWidget()
        status_layout = QVBoxLayout(status_container)
        status_layout.setContentsMargins(0, 0, 0, 0)
        status_layout.setSpacing(2)
        
        status_layout.addWidget(QLabel("SYSTEM STATUS", styleSheet=f"color:{COLORS['text_dim']}; font-size:10px; font-weight:bold; border:none; background:transparent;"))
        self.lbl_status = QLabel("🟢 ONLINE")
        self.lbl_status.setStyleSheet(f"color:{COLORS['success']}; font-size:18px; font-weight:bold; border:none; background:transparent;")
        status_layout.addWidget(self.lbl_status)
        h_layout.addWidget(status_container)
        h_layout.addStretch()
        
        clock_container = QWidget()
        clock_layout = QVBoxLayout(clock_container)
        clock_layout.setContentsMargins(0, 0, 0, 0)
        
        clock_lbl = QLabel("CURRENT TIME")
        clock_lbl.setStyleSheet(f"color:{COLORS['text_dim']}; font-size:10px; font-weight:bold; border:none; background:transparent;")
        clock_lbl.setAlignment(Qt.AlignRight)
        clock_layout.addWidget(clock_lbl)
        
        self.lbl_clock = QLabel("00:00:00")
        self.lbl_clock.setAlignment(Qt.AlignRight)
        self.lbl_clock.setStyleSheet(f"color:{COLORS['text']}; font-size:26px; font-weight:bold; font-family:{FONTS['mono']}; border:none; background:transparent;")
        clock_layout.addWidget(self.lbl_clock)
        h_layout.addWidget(clock_container)
        
        right_layout.addWidget(header_card)
        
        # Result
        result_card = QFrame()
        result_card.setStyleSheet(f"background-color: {COLORS['bg_card']}; border-radius: 10px; border: 1px solid {COLORS['border']};")
        r_layout = QVBoxLayout(result_card)
        r_layout.setContentsMargins(20, 20, 20, 20)
        r_layout.setSpacing(10)
        
        r_layout.addWidget(QLabel("LATEST ORDER ID", styleSheet=f"color:{COLORS['text_dim']}; font-size:11px; font-weight:bold; border:none; background:transparent;"))
        
        self.result_stack = QStackedWidget()
        self.result_stack.setFixedHeight(80)
        
        self.lbl_result = QLabel("WAITING...")
        self.lbl_result.setAlignment(Qt.AlignCenter)
        self.lbl_result.setStyleSheet(f"color:{COLORS['text_dim']}; font-size:28px; font-weight:bold; font-family:{FONTS['mono']}; border: 2px dashed {COLORS['border']}; border-radius: 8px;")
        self.result_stack.addWidget(self.lbl_result)
        
        self.lbl_countdown = QLabel("")
        self.lbl_countdown.setAlignment(Qt.AlignCenter)
        self.lbl_countdown.setStyleSheet(f"color:{COLORS['warning']}; font-size:48px; font-weight:bold; font-family:{FONTS['mono']};")
        self.result_stack.addWidget(self.lbl_countdown)
        
        r_layout.addWidget(self.result_stack)
        r_layout.addWidget(QLabel("SHOPEE EXPRESS", alignment=Qt.AlignCenter, styleSheet=f"background-color:{COLORS['shopee']}; color:white; border-radius:4px; padding:6px; font-weight:bold; font-size:12px; height:30px;"))
        
        self.btn_retake_all = QPushButton("🔄 Retake All Cameras")
        self.btn_retake_all.setCursor(Qt.PointingHandCursor)
        self.btn_retake_all.setFixedHeight(45)
        self.btn_retake_all.setStyleSheet(f"""
            QPushButton {{ background-color: {COLORS['error']}; color: white; border: none; border-radius: 6px; font-size: 14px; font-weight: bold; }}
            QPushButton:hover {{ background-color: {COLORS['shopee']}; }}
            QPushButton:disabled {{ background-color: {COLORS['bg_input']}; color: {COLORS['text_dim']}; border: 1px solid {COLORS['border']}; }}
        """)
        self.btn_retake_all.setEnabled(False)
        r_layout.addWidget(self.btn_retake_all)
        
        right_layout.addWidget(result_card)
        
        # Stats
        stats_container = QWidget()
        stats_grid = QGridLayout(stats_container)
        stats_grid.setContentsMargins(0, 0, 0, 0)
        stats_grid.setSpacing(10)
        
        self.stat_total = StatBox("TOTAL SCANS", COLORS['text'])
        self.stat_success = StatBox("SUCCESS", COLORS['success'])
        self.stat_fail = StatBox("REJECTED", COLORS['error'])
        self.stat_rate = StatBox("YIELD RATE", COLORS['warning'])
        
        stats_grid.addWidget(self.stat_total, 0, 0)
        stats_grid.addWidget(self.stat_success, 0, 1)
        stats_grid.addWidget(self.stat_fail, 1, 0)
        stats_grid.addWidget(self.stat_rate, 1, 1)
        right_layout.addWidget(stats_container)
        
        # Pipeline
        pipe_card = QFrame()
        pipe_card.setStyleSheet(f"background-color: {COLORS['bg_card']}; border-radius: 10px; padding: 15px; border: 1px solid {COLORS['border']};")
        p_layout = QVBoxLayout(pipe_card)
        p_layout.setContentsMargins(10, 10, 10, 10)
        p_layout.setSpacing(5)
        
        p_layout.addWidget(QLabel("PROCESS WORKFLOW", styleSheet=f"color:{COLORS['text']}; font-weight:bold; font-size:12px; border:none; background:transparent;"))
        
        for key, idx, th, en in [
            ("sensor", "1", "ตรวจจับพัสดุ", "Induction Sensor Triggered"),
            ("sc2000", "2", "สแกนบาร์โค้ด SC2000", "Smart Camera OCR Processing"),
            ("hikrobot", "3", "บันทึกภาพรอบด้าน", "Hikrobot Multi-View Capture"),
            ("save", "4", "บันทึกหลักฐาน", "Evidence Storage & Sync")
        ]:
            step = PipelineStep(idx, th, en)
            p_layout.addWidget(step)
            self.pipeline_steps[key] = step
            
        p_layout.addStretch()
        right_layout.addWidget(pipe_card)
        right_layout.addStretch()
        
        right_scroll.setWidget(right_content)
        main_layout.addWidget(right_scroll, stretch=35)
        
        self.timer_clock = QTimer()
        self.timer_clock.timeout.connect(lambda: self.lbl_clock.setText(QTime.currentTime().toString("HH:mm:ss")))
        self.timer_clock.start(1000)

    def log(self, msg):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

    def reset_pipeline(self):
        for step in self.pipeline_steps.values():
            step.set_status('idle')
        self.lbl_result.setText("WAITING...")
        self.lbl_result.setStyleSheet(f"color:{COLORS['text_dim']}; font-size:28px; font-family:{FONTS['mono']}; font-weight:bold; border: 2px dashed {COLORS['border']}; border-radius: 8px;")
        self.result_stack.setCurrentIndex(0)
        if hasattr(self, 'cam_main'):
            self.cam_main.set_active("NOT CONNECTED")
        for cam in self.hikrobot_cams:
            cam.set_active("READY")

    def update_stats(self, success=True):
        self.total_count += 1
        if success:
            self.success_count += 1
        self.stat_total.val.setText(str(self.total_count))
        self.stat_success.val.setText(str(self.success_count))
        self.stat_fail.val.setText(str(self.total_count - self.success_count))
        if self.total_count > 0:
            self.stat_rate.val.setText(f"{(self.success_count / self.total_count) * 100:.1f}%")

    def animate_step(self, step, state='processing'):
        if step in self.pipeline_steps:
            self.pipeline_steps[step].set_status(state)
    
    def show_countdown(self, seconds):
        if seconds > 0:
            self.lbl_countdown.setText(f"⏱️ {seconds}")
            self.result_stack.setCurrentIndex(1)
        else:
            self.result_stack.setCurrentIndex(0)
    
    def load_and_display_images(self, image_paths):
        for i, path in enumerate(image_paths):
            if i >= len(self.hikrobot_cams):
                break
            try:
                if not os.path.exists(path):
                    continue
                pixmap = QPixmap(path)
                if not pixmap.isNull():
                    self.hikrobot_cams[i].update_frame(pixmap.toImage())
                    self.log(f"📷 Loaded {path}")
            except Exception as e:
                self.log(f"❌ Error loading {path}: {e}")
    
    def enable_retake_buttons(self, enabled=True):
        self.btn_retake_all.setEnabled(enabled)
        for cam in self.hikrobot_cams:
            cam.enable_retake(enabled)
    
    def update_main_camera(self, qt_image):
        if hasattr(self, 'cam_main'):
            self.cam_main.update_frame(qt_image)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setFont(QFont(FONTS['main'], 10))
    window = MainUI()
    window.show()
    sys.exit(app.exec_())