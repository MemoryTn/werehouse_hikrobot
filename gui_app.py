# -*- coding: utf-8 -*-
import sys
import os
from datetime import datetime
from PyQt5.QtWidgets import *
from PyQt5.QtGui import QFont, QPixmap, QImage, QIcon
from PyQt5.QtCore import Qt, pyqtSignal, QTimer, QTime

from config import COLORS, FONTS

# ══════════════════════════════════════════════════════════════
# LiveFeedCard (Industrial Style)
# ══════════════════════════════════════════════════════════════
class LiveFeedCard(QFrame):
    def __init__(self, title, icon):
        super().__init__()
        self.setFrameShape(QFrame.NoFrame)
        self.setStyleSheet(f"""
            QFrame {{ 
                background-color: {COLORS['bg_card']}; 
                border: 1px solid #3f3f4e; 
                border-top: 3px solid {COLORS['primary']}; 
                border-radius: 3px; 
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        header = QHBoxLayout()
        header.setContentsMargins(5, 0, 5, 0)
        lbl_title = QLabel(f"{icon} {title.upper()}")
        lbl_title.setStyleSheet(f"color: #d4d4d4; font-size: 12px; font-weight: 900; letter-spacing: 1px; border: none; background: transparent;")
        header.addWidget(lbl_title)

        self.status_dot = QLabel("■ CONNECTING")
        self.status_dot.setStyleSheet(f"color: {COLORS['warning']}; font-size: 11px; font-weight: 900; border: none; background: transparent; letter-spacing: 1px;")
        header.addWidget(self.status_dot, 0, Qt.AlignRight)

        layout.addLayout(header)

        self.screen = QLabel("NO VIDEO SIGNAL")
        self.screen.setAlignment(Qt.AlignCenter)
        self.screen.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Expanding)
        self.screen.setMinimumSize(120, 90)
        self.screen.setStyleSheet(f"background-color: #050508; color: #444; border: 1px solid #111; border-radius: 2px; font-size: 14px; font-weight: 900; font-family: {FONTS['mono']}; letter-spacing: 2px;")
        layout.addWidget(self.screen, stretch=1)

    def update_frame(self, qt_image: QImage):
        if qt_image is None or qt_image.isNull():
            return
        pixmap = QPixmap.fromImage(qt_image)
        w, h = self.screen.width(), self.screen.height()
        if w > 10 and h > 10:
            self.screen.setPixmap(pixmap.scaled(w, h, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        if "CONNECTING" in self.status_dot.text():
            self.status_dot.setText("■ LIVE")
            self.status_dot.setStyleSheet(f"color: {COLORS['success']}; font-size: 11px; font-weight: 900; border: none; background: transparent; letter-spacing: 1px;")


# ══════════════════════════════════════════════════════════════
# SnapshotCard (Industrial Style)
# ══════════════════════════════════════════════════════════════
class SnapshotCard(QFrame):
    retake_clicked = pyqtSignal(int)

    def __init__(self, title, icon, camera_index=0):
        super().__init__()
        self.camera_index = camera_index
        self.setFrameShape(QFrame.NoFrame)
        self.setStyleSheet(f"""
            QFrame {{ 
                background-color: {COLORS['bg_card']}; 
                border: 1px solid #3f3f4e; 
                border-top: 3px solid #89b4fa; 
                border-radius: 3px; 
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(5)

        header = QHBoxLayout()
        header.setContentsMargins(4, 2, 4, 0)
        lbl_title = QLabel(f"{icon} {title.upper()}")
        lbl_title.setStyleSheet(f"color: #d4d4d4; font-size: 11px; font-weight: 900; letter-spacing: 1px; border: none; background: transparent;")
        header.addWidget(lbl_title)

        self.status_dot = QLabel("■ READY")
        self.status_dot.setStyleSheet(f"color: {COLORS['text_dim']}; font-size: 10px; font-weight: 900; border: none; background: transparent;")
        header.addWidget(self.status_dot, 0, Qt.AlignRight)

        layout.addLayout(header)

        self.screen = QLabel("STANDBY")
        self.screen.setAlignment(Qt.AlignCenter)
        self.screen.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Expanding)
        self.screen.setMinimumSize(80, 60)
        self.screen.setStyleSheet(f"background-color: #050508; color: #444; border: 1px solid #111; border-radius: 2px; font-size: 12px; font-weight: 900; font-family: {FONTS['mono']}; letter-spacing: 1px;")
        layout.addWidget(self.screen, stretch=1)

        self.btn_retake = QPushButton("RETX / RETAKE")
        self.btn_retake.setCursor(Qt.PointingHandCursor)
        self.btn_retake.setFixedHeight(24)
        self.btn_retake.setStyleSheet(f"""
            QPushButton {{ 
                background-color: #1e1e2e; 
                color: {COLORS['text']}; 
                border: 1px solid #555; 
                border-radius: 2px; 
                font-size: 10px; 
                font-weight: 900; 
                letter-spacing: 1px;
            }}
            QPushButton:hover {{ 
                background-color: {COLORS['warning']}; 
                color: #111; 
                border: 1px solid {COLORS['warning']}; 
            }}
            QPushButton:disabled {{ 
                background-color: transparent; 
                color: {COLORS['border']}; 
                border: 1px dashed {COLORS['border']}; 
            }}
        """)
        self.btn_retake.clicked.connect(lambda: self.retake_clicked.emit(self.camera_index))
        self.btn_retake.setEnabled(False)
        layout.addWidget(self.btn_retake)

    def show_image(self, image_path: str):
        pixmap = QPixmap(image_path)
        if not pixmap.isNull():
            w, h = self.screen.width(), self.screen.height()
            if w > 10 and h > 10:
                self.screen.setPixmap(pixmap.scaled(w, h, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            self.status_dot.setText("■ CAPTURED")
            self.status_dot.setStyleSheet(f"color: {COLORS['success']}; font-size: 10px; font-weight: 900; border: none; background: transparent;")
            self.screen.setStyleSheet(f"background-color: #050508; border: 2px solid {COLORS['success']}; border-radius: 2px;")

    def set_status(self, text, color):
        self.screen.setText(text.upper())
        self.screen.setStyleSheet(f"background-color: #050508; color: {color}; border: 2px solid {color}; border-radius: 2px; font-size: 12px; font-weight: 900; font-family: {FONTS['mono']};")
        self.status_dot.setText(f"■ {text.upper()}")
        self.status_dot.setStyleSheet(f"color: {color}; font-size: 10px; font-weight: 900; border: none; background: transparent;")

    def set_preview_mode(self, text_status="PREVIEW", color=None):
        if color is None: color = COLORS['success']
        self.screen.setStyleSheet(f"background-color: #050508; border: 2px solid {color}; border-radius: 2px;")
        self.status_dot.setText(f"■ {text_status.upper()}")
        self.status_dot.setStyleSheet(f"color: {color}; font-size: 10px; font-weight: 900; border: none; background: transparent;")

    def enable_retake(self, enabled=True):
        self.btn_retake.setEnabled(enabled)

    def reset(self):
        self.screen.clear()
        self.screen.setText("STANDBY")
        self.screen.setStyleSheet(f"background-color: #050508; color: #444; border: 1px solid #111; border-radius: 2px; font-size: 12px; font-weight: 900; font-family: {FONTS['mono']};")
        self.status_dot.setText("■ READY")
        self.status_dot.setStyleSheet(f"color: {COLORS['text_dim']}; font-size: 10px; font-weight: 900; border: none; background: transparent;")
        self.btn_retake.setEnabled(False)


# ══════════════════════════════════════════════════════════════
# MainUI
# ══════════════════════════════════════════════════════════════
class MainUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Shopee Express - Smart Sorting System v4.0 (Industrial Mode)")
        self.resize(1440, 880)
        self.setMinimumSize(1200, 700)
        self.setStyleSheet(f"background-color: #111116;")

        self.total_count   = 0
        self.current_order_no = None

        self.setup_ui()

    def setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(12)

        # ══ TOP SECTION (Live feeds + Controls) ═════════════════════════
        top_section = QHBoxLayout()
        top_section.setSpacing(12)

        # ── Left Panel (Live Feeds) ──────────────
        left_feeds = QHBoxLayout()
        left_feeds.setSpacing(10)

        self.feed_sc2000    = LiveFeedCard("SC2000 OCR SCANNER", "📸")
        self.feed_hikvision = LiveFeedCard("HIKVISION CCTV", "🎥")
        left_feeds.addWidget(self.feed_sc2000,    stretch=1)
        left_feeds.addWidget(self.feed_hikvision, stretch=1)
        
        top_section.addLayout(left_feeds, stretch=65)

        # ── Right Panel (Controls) ──────────────
        right = QVBoxLayout()
        right.setContentsMargins(5, 0, 0, 0)
        right.setSpacing(10) 

        # 1. Header (Status + Total Scan + Clock)
        header_card = QFrame()
        header_card.setFrameShape(QFrame.NoFrame)
        header_card.setStyleSheet(f"background-color: {COLORS['bg_card']}; border: 1px solid #3f3f4e; border-top: 3px solid #6c7086; border-radius: 3px;")
        header_card.setFixedHeight(75) # ปรับให้ความสูงคงที่และเล็กลง
        
        h_layout = QHBoxLayout(header_card)
        h_layout.setContentsMargins(20, 0, 20, 0) 

        # -- Status --
        status_box = QWidget()
        sl = QVBoxLayout(status_box)
        sl.setAlignment(Qt.AlignVCenter)
        sl.setContentsMargins(0, 0, 0, 0)
        sl.setSpacing(2)
        
        lbl_stat_title = QLabel("SYS STATUS")
        lbl_stat_title.setStyleSheet(f"color:#888; font-size:10px; font-weight:900; border:none; background:transparent; letter-spacing: 1px;")
        sl.addWidget(lbl_stat_title)
        
        self.lbl_status = QLabel("■ ONLINE")
        self.lbl_status.setStyleSheet(f"color:{COLORS['success']}; font-size:18px; font-weight:900; border:none; background:transparent; font-family:{FONTS['mono']};")
        sl.addWidget(self.lbl_status)
        h_layout.addWidget(status_box)
        
        h_layout.addStretch()

        # -- Total Scan --
        total_box = QWidget()
        tl = QVBoxLayout(total_box)
        tl.setAlignment(Qt.AlignVCenter | Qt.AlignHCenter)
        tl.setContentsMargins(0, 0, 0, 0)
        tl.setSpacing(2)

        lbl_total_title = QLabel("TOTAL SCANS")
        lbl_total_title.setStyleSheet(f"color:#888; font-size:10px; font-weight:900; border:none; background:transparent; letter-spacing: 1px;")
        lbl_total_title.setAlignment(Qt.AlignCenter)
        tl.addWidget(lbl_total_title)

        self.lbl_total = QLabel("0")
        self.lbl_total.setAlignment(Qt.AlignCenter)
        self.lbl_total.setStyleSheet(f"color:#e5e5e5; font-size:28px; font-weight:900; font-family:{FONTS['mono']}; border:none; background:transparent;")
        tl.addWidget(self.lbl_total)
        h_layout.addWidget(total_box)

        h_layout.addStretch()

        # -- Clock --
        clock_box = QWidget()
        cl = QVBoxLayout(clock_box)
        cl.setAlignment(Qt.AlignVCenter)
        cl.setContentsMargins(0, 0, 0, 0)
        cl.setSpacing(2)
        
        cl_lbl = QLabel("SYS CLOCK")
        cl_lbl.setStyleSheet(f"color:#888; font-size:10px; font-weight:900; border:none; background:transparent; letter-spacing: 1px;")
        cl_lbl.setAlignment(Qt.AlignRight)
        cl.addWidget(cl_lbl)
        
        self.lbl_clock = QLabel("00:00:00")
        self.lbl_clock.setAlignment(Qt.AlignRight)
        self.lbl_clock.setStyleSheet(f"color:#e5e5e5; font-size:28px; font-weight:900; font-family:{FONTS['mono']}; border:none; background:transparent;")
        cl.addWidget(self.lbl_clock)
        
        h_layout.addWidget(clock_box)

        # 2. License Plate Input Card 
        manual_card = QFrame()
        manual_card.setFrameShape(QFrame.NoFrame)
        manual_card.setStyleSheet(f"background-color: {COLORS['bg_card']}; border: 1px solid #3f3f4e; border-left: 3px solid {COLORS['primary']}; border-radius: 3px;")
        m_layout = QHBoxLayout(manual_card)
        m_layout.setContentsMargins(15, 12, 15, 12)
        m_layout.setSpacing(12)
        
        self.txt_manual = QLineEdit()
        self.txt_manual.setFixedHeight(58)
        self.txt_manual.setPlaceholderText("🚗 PLATE NO. INPUT...")
        self.txt_manual.setStyleSheet(f"""
            QLineEdit {{
                background-color: #050508; 
                color: {COLORS['success']}; 
                border: 1px solid #555; 
                border-radius: 2px; 
                padding: 0px 15px; 
                font-size: 24px;
                font-weight: 900;
                font-family: 'Leelawadee UI', 'Tahoma', 'sans-serif';
            }}
            QLineEdit:focus {{ border: 1px solid {COLORS['primary']}; background-color: #111; }}
            QLineEdit:disabled {{ color: {COLORS['success']}; background-color: #0a0a0f; border: 1px dashed #333;}}
        """)
        
        self.btn_manual = QPushButton("🚗 CONFIRM")
        self.btn_manual.setFixedHeight(58)
        self.btn_manual.setCursor(Qt.PointingHandCursor)
        self.btn_manual.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['primary']}; 
                color: white; 
                border: none; 
                border-radius: 2px; 
                padding: 0px 15px; 
                font-size: 14px;
                font-weight: 900;
                letter-spacing: 1px;
            }}
            QPushButton:hover {{ background-color: {COLORS['active_bg']}; }}
        """)
        m_layout.addWidget(self.txt_manual, stretch=6)
        m_layout.addWidget(self.btn_manual, stretch=4)

        # 3. Result Banner (เพิ่ม addStretch เพื่อจัดกึ่งกลาง และฟิกซ์ความสูงจอ LED ให้พอดี)
        result_card = QFrame()
        result_card.setFrameShape(QFrame.NoFrame)
        result_card.setStyleSheet(f"background-color: {COLORS['bg_card']}; border: 1px solid #3f3f4e; border-top: 3px solid {COLORS['warning']}; border-radius: 3px;")
        r_layout = QVBoxLayout(result_card)
        r_layout.setContentsMargins(20, 20, 20, 20)
        r_layout.setSpacing(12)

        lbl_res_title = QLabel("LATEST TARGET ID")
        lbl_res_title.setStyleSheet(f"color:#888; font-size:11px; font-weight:900; border:none; background:transparent; letter-spacing: 1px;")
        
        # จัดให้จออยู่ตรงกลางกรณีกล่องหลักขยาย
        r_layout.addStretch()
        r_layout.addWidget(lbl_res_title)

        self.result_stack = QStackedWidget()
        self.result_stack.setFixedHeight(80) # Fix ขนาดจอไม่ให้โตเกินไป ลดมาจากพื้นที่เวิ้งว้างเดิม

        self.lbl_result = QLabel("- STANDBY -")
        self.lbl_result.setAlignment(Qt.AlignCenter)
        self.lbl_result.setStyleSheet(f"""
            color: #444; 
            font-size: 40px; 
            font-weight: 900; 
            font-family: {FONTS['mono']}; 
            background-color: #050508;
            border: 2px solid #222; 
            border-radius: 2px;
            letter-spacing: 2px;
        """)
        self.result_stack.addWidget(self.lbl_result)

        self.lbl_countdown = QLabel("")
        self.lbl_countdown.setAlignment(Qt.AlignCenter)
        self.lbl_countdown.setStyleSheet(f"color:{COLORS['warning']}; font-size:64px; font-weight:900; font-family:{FONTS['mono']}; background-color:#050508; border: 2px solid {COLORS['warning']}; border-radius: 2px;")
        self.result_stack.addWidget(self.lbl_countdown)

        r_layout.addWidget(self.result_stack)
        
        tag_lbl = QLabel("SPX EXPRESS : SYSTEM CORE", alignment=Qt.AlignCenter)
        tag_lbl.setStyleSheet(f"background-color:{COLORS['shopee']}; color:#fff; border-radius:2px; padding:6px; font-weight:900; font-size:12px; letter-spacing: 2px;")
        r_layout.addWidget(tag_lbl)

        self.btn_retake_all = QPushButton("SYSTEM OVERRIDE: RETAKE ALL")
        self.btn_retake_all.setCursor(Qt.PointingHandCursor)
        self.btn_retake_all.setFixedHeight(48)
        self.btn_retake_all.setStyleSheet(f"""
            QPushButton {{ 
                background-color: #d32f2f; 
                color: white; 
                border: none; 
                border-radius: 2px; 
                font-size: 14px; 
                font-weight: 900; 
                letter-spacing: 1px;
            }}
            QPushButton:hover {{ background-color: #ff3333; }}
            QPushButton:disabled {{ 
                background-color: #1a1a24; 
                color: #444; 
                border: 1px dashed #333; 
            }}
        """)
        self.btn_retake_all.setEnabled(False)
        r_layout.addWidget(self.btn_retake_all)
        r_layout.addStretch() # ขนาบด้วย Stretch บนล่าง

        # 4. Order ID Input Card 
        order_card = QFrame()
        order_card.setFrameShape(QFrame.NoFrame)
        order_card.setStyleSheet(f"background-color: {COLORS['bg_card']}; border: 1px solid #3f3f4e; border-left: 3px solid {COLORS['shopee']}; border-radius: 3px;")
        o_layout = QHBoxLayout(order_card)
        o_layout.setContentsMargins(15, 12, 15, 12)
        o_layout.setSpacing(12)
        
        self.txt_order = QLineEdit()
        self.txt_order.setFixedHeight(58)
        self.txt_order.setMaxLength(14)
        self.txt_order.setPlaceholderText("📦 ORDER ID INPUT...")
        self.txt_order.setStyleSheet(f"""
            QLineEdit {{
                background-color: #050508; 
                color: {COLORS['warning']}; 
                border: 1px solid #555; 
                border-radius: 2px; 
                padding: 0px 15px; 
                font-size: 24px;
                font-weight: 900;
                font-family: {FONTS['mono']};
            }}
            QLineEdit:focus {{ border: 1px solid {COLORS['shopee']}; background-color: #111; }}
            QLineEdit:disabled {{ color: #444; background-color: #0a0a0f; border: 1px dashed #333;}}
        """)
        
        self.btn_order = QPushButton("📦 CONFIRM")
        self.btn_order.setFixedHeight(58)
        self.btn_order.setCursor(Qt.PointingHandCursor)
        self.btn_order.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['shopee']}; 
                color: white; 
                border: none; 
                border-radius: 2px; 
                padding: 0px 15px; 
                font-size: 14px;
                font-weight: 900;
                letter-spacing: 1px;
            }}
            QPushButton:hover {{ background-color: #ff6644; }}
        """)
        o_layout.addWidget(self.txt_order, stretch=7)
        o_layout.addWidget(self.btn_order, stretch=3)

        # 📌 แบ่งสัดส่วน Stretch ให้ทุกกล่องขยายรับพื้นที่ร่วมกันอย่างสมดุล (Proportional Sharing)
        right.addWidget(header_card, stretch=0) # Fix size ให้ไม่ขยายจนเทอะทะ
        right.addWidget(manual_card, stretch=0) # Fix size
        right.addWidget(result_card, stretch=1) # จอผลลัพธ์รับพื้นที่เยอะสุด
        right.addWidget(order_card, stretch=0)  # Fix size

        top_section.addLayout(right, stretch=35)
        root.addLayout(top_section, stretch=65) 

        # ══ BOTTOM SECTION (4 Snapshot Cameras) ══════════════
        bot_section = QHBoxLayout()
        bot_section.setSpacing(10)

        cam_labels = [
            ("FRONT VIEW", "⬆️"),
            ("LEFT SIDE",  "⬅️"),
            ("RIGHT SIDE", "➡️"),
            ("BACK VIEW",  "⬇️")
        ]
        self.hikrobot_cams: list[SnapshotCard] = []
        for i, (name, icon) in enumerate(cam_labels):
            card = SnapshotCard(f"{name} MODULE", icon, camera_index=i)
            self.hikrobot_cams.append(card)
            bot_section.addWidget(card, stretch=1)
        
        root.addLayout(bot_section, stretch=35)

        self.timer_clock = QTimer()
        self.timer_clock.timeout.connect(
            lambda: self.lbl_clock.setText(QTime.currentTime().toString("HH:mm:ss"))
        )
        self.timer_clock.start(1000)

    def log(self, msg):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

    def reset_pipeline(self):
        self.lbl_result.setText("- STANDBY -")
        self.lbl_result.setStyleSheet(f"""
            color: #444; 
            font-size: 40px; 
            font-weight: 900; 
            font-family: {FONTS['mono']}; 
            background-color: #050508;
            border: 2px solid #222; 
            border-radius: 2px;
            letter-spacing: 2px;
        """)
        self.result_stack.setCurrentIndex(0)
        for cam in self.hikrobot_cams:
            cam.reset()

    def update_stats(self):
        self.total_count += 1
        self.lbl_total.setText(str(self.total_count))

    def show_countdown(self, seconds):
        if seconds > 0:
            self.lbl_countdown.setText(f"{seconds}s")
            self.result_stack.setCurrentIndex(1)
        else:
            self.result_stack.setCurrentIndex(0)

    def load_and_display_images(self, image_paths: list):
        for i, path in enumerate(image_paths):
            if i >= len(self.hikrobot_cams):
                break
            if not os.path.exists(path):
                continue
            self.hikrobot_cams[i].show_image(path)
            self.log(f"SYS: Loaded evidence CAM-0{i+1}: {path}")

    def enable_retake_buttons(self, enabled=True):
        self.btn_retake_all.setEnabled(enabled)
        for cam in self.hikrobot_cams:
            cam.enable_retake(enabled)

    def update_main_camera(self, qt_image):
        self.feed_sc2000.update_frame(qt_image)