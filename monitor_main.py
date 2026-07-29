import sys
import sqlite3
import random
import cv2
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget,
    QVBoxLayout, QHBoxLayout, QLabel, QGroupBox,
    QGridLayout, QFrame, QProgressBar
)
from PyQt6.QtCore import QTimer, Qt, QDateTime
from PyQt6.QtGui import QImage, QPixmap
import pyqtgraph as pg


class StressMonitorApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("STRESS Analysis Monitoring System")
        self.resize(1400, 780)
        self.setStyleSheet("""
            QMainWindow { background: #020617; color: #f8fafc; }
            QGroupBox { background: #111827; border: 1px solid #334155; border-radius: 12px; padding-top: 12px; color: #f8fafc; }
            QLabel { color: #e2e8f0; }
            QLabel#titleLabel { font-size: 24px; font-weight: 700; color: #f8fafc; }
            QLabel#subtitleLabel { color: #94a3b8; font-size: 12px; }
            QLabel#statusLabel { font-size: 13px; font-weight: 600; }
            QLabel#cameraLabel { background-color: #020617; color: #f8fafc; }
            QLabel#metricTitle { color: #94a3b8; font-size: 12px; text-transform: uppercase; letter-spacing: 1px; }
            QLabel#metricValue { font-size: 24px; font-weight: 700; color: #f8fafc; }
            QLabel#metricHint { color: #64748b; font-size: 11px; }
            QFrame#metricCard { background: #0f172a; border: 1px solid #334155; border-radius: 12px; }
            QProgressBar { border: none; border-radius: 8px; background: #1f2937; }
            QProgressBar::chunk { border-radius: 8px; }
        """)

        # 1. DB 초기화
        self.init_db()

        # 2. 메인 UI 레이아웃 초기화
        self.init_ui()

        # 3. 노트북 내장 웹캠 초기화 및 타이머 설정
        self.init_camera()

        # [테스트용] 라즈베리파이 센서 데이터 더미 생성기
        self.test_timer = QTimer()
        self.test_timer.timeout.connect(self.generate_dummy_data)
        self.test_timer.start(1000)

        # 실시간 그래프 출력을 위한 데이터 버퍼
        self.time_data = list(range(60))
        self.hr_data = [0] * 60

    def init_db(self):
        """SQLite 데이터베이스 연동 및 테이블 생성"""
        self.conn = sqlite3.connect("stress_data.db", check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS sensor_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                heart_rate REAL,
                spo2 REAL,
                stress_level REAL
            )
        ''')
        self.conn.commit()

    def init_ui(self):
        """PyQt6 기반 메인 모니터링 UI 구성"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(16)

        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 0, 0)

        title_layout = QVBoxLayout()
        title_label = QLabel("Stress Monitoring Dashboard")
        title_label.setObjectName("titleLabel")
        subtitle_label = QLabel("Real-time wellness monitoring for operational teams")
        subtitle_label.setObjectName("subtitleLabel")
        title_layout.addWidget(title_label)
        title_layout.addWidget(subtitle_label)
        header_layout.addLayout(title_layout)

        right_header = QVBoxLayout()
        right_header.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.timestamp_label = QLabel("--")
        self.timestamp_label.setStyleSheet("color: #cbd5e1; font-size: 12px;")
        self.status_label = QLabel("● STABLE")
        self.status_label.setObjectName("statusLabel")
        self.status_label.setStyleSheet("color: #22c55e;")
        right_header.addWidget(self.timestamp_label, 0, Qt.AlignmentFlag.AlignRight)
        right_header.addWidget(self.status_label, 0, Qt.AlignmentFlag.AlignRight)
        header_layout.addLayout(right_header)
        main_layout.addWidget(header_widget)

        content_layout = QHBoxLayout()
        content_layout.setSpacing(16)

        video_group = QGroupBox("Live Camera Feed")
        video_layout = QVBoxLayout()
        self.video_label = QLabel("Initializing Camera...")
        self.video_label.setObjectName("cameraLabel")
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video_label.setMinimumHeight(380)
        self.video_label.setStyleSheet("background-color: #020617; color: #f8fafc;")
        video_layout.addWidget(self.video_label)
        video_group.setLayout(video_layout)
        content_layout.addWidget(video_group, 2)

        data_group = QGroupBox("Operational Metrics")
        data_layout = QVBoxLayout()

        metrics_layout = QGridLayout()
        metrics_layout.setSpacing(12)

        self.hr_card, self.hr_value_label, self.hr_progress, self.hr_hint_label = self.build_metric_card(
            "Heart Rate", "bpm", "Target range 60-90", "#38bdf8"
        )
        self.spo2_card, self.spo2_value_label, self.spo2_progress, self.spo2_hint_label = self.build_metric_card(
            "SpO2", "%", "Healthy range 95+", "#34d399"
        )
        self.stress_card, self.stress_value_label, self.stress_progress, self.stress_hint_label = self.build_metric_card(
            "Stress", "score", "Lower is better", "#f43f5e"
        )

        metrics_layout.addWidget(self.hr_card, 0, 0)
        metrics_layout.addWidget(self.spo2_card, 0, 1)
        metrics_layout.addWidget(self.stress_card, 0, 2)
        data_layout.addLayout(metrics_layout)

        self.graph_widget = pg.PlotWidget(title="Heart Rate Trend")
        self.graph_widget.setBackground('#020617')
        self.graph_widget.setLabel('left', 'bpm')
        self.graph_widget.setLabel('bottom', 'last 60s')
        self.graph_widget.showGrid(x=True, y=True, alpha=0.2)
        self.graph_line = self.graph_widget.plot(pen=pg.mkPen(color='#f43f5e', width=2))
        data_layout.addWidget(self.graph_widget)

        self.info_label = QLabel("Waiting for data...")
        self.info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.info_label.setStyleSheet(
            "font-size: 13px; color: #cbd5e1; padding: 8px; background: #0f172a; border-radius: 8px;"
        )
        data_layout.addWidget(self.info_label)

        data_group.setLayout(data_layout)
        content_layout.addWidget(data_group, 3)
        main_layout.addLayout(content_layout)

    def build_metric_card(self, title, unit, hint, color):
        card = QFrame()
        card.setObjectName("metricCard")
        card.setMinimumHeight(120)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(8)

        title_label = QLabel(title)
        title_label.setObjectName("metricTitle")
        layout.addWidget(title_label)

        value_layout = QHBoxLayout()
        value_label = QLabel("0")
        value_label.setObjectName("metricValue")
        unit_label = QLabel(unit)
        unit_label.setObjectName("metricHint")
        value_layout.addWidget(value_label)
        value_layout.addWidget(unit_label)
        layout.addLayout(value_layout)

        progress_bar = QProgressBar()
        progress_bar.setRange(0, 100)
        progress_bar.setValue(0)
        progress_bar.setFixedHeight(8)
        progress_bar.setStyleSheet(f"QProgressBar::chunk {{ background: {color}; }}")
        layout.addWidget(progress_bar)

        hint_label = QLabel(hint)
        hint_label.setObjectName("metricHint")
        layout.addWidget(hint_label)

        return card, value_label, progress_bar, hint_label

    def init_camera(self):
        """OpenCV를 이용한 웹캠 캡처 초기화"""
        self.cap = cv2.VideoCapture(0)

        self.cam_timer = QTimer()
        self.cam_timer.timeout.connect(self.update_frame)
        self.cam_timer.start(30)

    def update_frame(self):
        """웹캠 프레임을 읽어와 PyQt 레이블에 렌더링"""
        ret, frame = self.cap.read()
        if ret:
            rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb_image.shape
            bytes_per_line = ch * w

            qt_img = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
            pixmap = QPixmap.fromImage(qt_img)
            self.video_label.setPixmap(pixmap.scaled(
                self.video_label.width(), self.video_label.height(),
                Qt.AspectRatioMode.KeepAspectRatio))

    def save_to_db(self, hr, spo2, stress):
        """수신된 데이터를 로컬 DB에 INSERT"""
        self.cursor.execute('''
            INSERT INTO sensor_log (heart_rate, spo2, stress_level)
            VALUES (?, ?, ?)
        ''', (hr, spo2, stress))
        self.conn.commit()

    def update_ui(self, hr, spo2, stress):
        """그래프 선 이동 및 텍스트 상태 업데이트"""
        self.hr_data = self.hr_data[1:] + [hr]
        self.graph_line.setData(self.time_data, self.hr_data)

        self.hr_value_label.setText(f"{hr:.1f}")
        self.hr_progress.setValue(int(min(100, max(0, (hr / 120) * 100))))
        self.hr_hint_label.setText("Stable" if 60 <= hr <= 90 else "Needs attention")

        self.spo2_value_label.setText(f"{spo2:.1f}")
        self.spo2_progress.setValue(int(min(100, max(0, spo2))))
        self.spo2_hint_label.setText("Normal" if spo2 >= 95 else "Low oxygen")

        self.stress_value_label.setText(f"{stress:.1f}")
        self.stress_progress.setValue(int(min(100, max(0, stress))))
        if stress >= 70:
            self.stress_hint_label.setText("High stress")
            self.stress_value_label.setStyleSheet("color: #fb7185;")
        elif stress >= 40:
            self.stress_hint_label.setText("Watch closely")
            self.stress_value_label.setStyleSheet("color: #f59e0b;")
        else:
            self.stress_hint_label.setText("Relaxed")
            self.stress_value_label.setStyleSheet("color: #f8fafc;")

        self.timestamp_label.setText(QDateTime.currentDateTime().toString("yyyy-MM-dd hh:mm:ss"))
        if stress >= 70:
            self.status_label.setText("● HIGH ALERT")
            self.status_label.setStyleSheet("color: #fb7185;")
        elif stress >= 40:
            self.status_label.setText("● WATCH")
            self.status_label.setStyleSheet("color: #f59e0b;")
        else:
            self.status_label.setText("● STABLE")
            self.status_label.setStyleSheet("color: #22c55e;")

        info_text = (
            f"Last updated: {QDateTime.currentDateTime().toString('hh:mm:ss')} | "
            f"Heart Rate: {hr:.1f} bpm | SpO2: {spo2:.1f}% | Stress: {stress:.1f}"
        )
        self.info_label.setText(info_text)

    def generate_dummy_data(self):
        """테스트 구동용 가상 센서 데이터 생성 로직"""
        fake_hr = random.uniform(70, 95)
        fake_spo2 = random.uniform(96, 100)
        fake_stress = random.uniform(10, 40)

        self.save_to_db(fake_hr, fake_spo2, fake_stress)
        self.update_ui(fake_hr, fake_spo2, fake_stress)

    def closeEvent(self, event):
        """프로그램 종료 시 웹캠 및 DB 리소스 안전 반환"""
        if self.cap.isOpened():
            self.cap.release()
        self.conn.close()
        event.accept()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = StressMonitorApp()
    window.show()
    sys.exit(app.exec())