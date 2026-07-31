import sys
import sqlite3
import random
import cv2
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget,
    QVBoxLayout, QHBoxLayout, QLabel, QGroupBox,
    QGridLayout, QFrame, QProgressBar, QComboBox, QSizePolicy,
    QScrollArea
)
from PyQt6.QtCore import QTimer, Qt, QDateTime
from PyQt6.QtGui import QImage, QPixmap
import pyqtgraph as pg


class StressMonitorApp(QMainWindow):
    def __init__(self):
        super().__init__()
        # 기본 언어 설정 및 번역 사전
        self.lang = 'en'
        self.translations = {
            'en': {
                'window_title': "STRESS Analysis Monitoring System",
                'title_main': "Stress Monitoring Dashboard",
                'subtitle': "Real-time wellness monitoring for operational teams",
                'live_camera': "Live Camera Feed",
                'operational_metrics': "Operational Metrics",
                'heart_rate': "Heart Rate",
                'spo2': "SpO2",
                'stress': "Stress",
                'hr_unit': "bpm",
                'spo2_unit': "%",
                'stress_unit': "score",
                'hr_hint': "Target range 60-90",
                'spo2_hint': "Healthy range 95+",
                'stress_hint': "Lower is better",
                'graph_title': "Heart Rate Trend",
                'left_label': "bpm",
                'bottom_label': "last 60s",
                'waiting': "Waiting for data...",
                'initializing_camera': "Initializing Camera...",
                'stable': "Stable",
                'needs_attention': "Needs attention",
                'normal': "Normal",
                'low_oxygen': "Low oxygen",
                'high_stress': "High stress",
                'watch': "Watch closely",
                'relaxed': "Relaxed",
                'status_stable': "● STABLE",
                'status_watch': "● WATCH",
                'status_high': "● HIGH ALERT",
                'last_updated_prefix': "Last updated:"
            },
            'ko': {
                'window_title': "스트레스 분석 모니터링 시스템",
                'title_main': "스트레스 모니터링 대시보드",
                'subtitle': "운영 팀을 위한 실시간 웰니스 모니터링",
                'live_camera': "실시간 카메라 피드",
                'operational_metrics': "운영 지표",
                'heart_rate': "심박수",
                'spo2': "혈중산소(SPO2)",
                'stress': "스트레스",
                'hr_unit': "bpm",
                'spo2_unit': "%",
                'stress_unit': "점수",
                'hr_hint': "목표 범위 60-90",
                'spo2_hint': "정상 범위 95+",
                'stress_hint': "낮을수록 좋음",
                'graph_title': "심박수 추이",
                'left_label': "bpm",
                'bottom_label': "최근 60초",
                'waiting': "데이터를 기다리는 중...",
                'initializing_camera': "카메라 초기화 중...",
                'stable': "안정",
                'needs_attention': "주의 필요",
                'normal': "정상",
                'low_oxygen': "저산소",
                'high_stress': "높은 스트레스",
                'watch': "관찰 필요",
                'relaxed': "편안함",
                'status_stable': "● 정상",
                'status_watch': "● 관찰",
                'status_high': "● 고위험",
                'last_updated_prefix': "마지막 업데이트:"
            }
        }
        self.setWindowTitle(self.translations[self.lang]['window_title'])

        # ------------------------------------------------------------------
        # [수정 1] 고정 크기(resize) 대신 화면에 맞춰 최대화로 시작.
        # 어떤 모니터 해상도에서 실행해도 내부 위젯들의 최소 높이 합이
        # 창 크기를 넘어서서 잘리는 문제를 방지합니다.
        # ------------------------------------------------------------------
        self.showMaximized()

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

        # ------------------------------------------------------------------
        # [수정 3] central_widget을 QScrollArea로 감싸서, 만약 창을 작게
        # 줄이거나 저해상도 화면에서 실행해도 내용이 잘리지 않고
        # 스크롤로 전부 볼 수 있도록 안전장치를 추가.
        # ------------------------------------------------------------------
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("QScrollArea { border: none; background: #020617; }")
        self.setCentralWidget(scroll_area)

        central_widget = QWidget()
        scroll_area.setWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(16)

        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 0, 0)

        title_layout = QVBoxLayout()
        self.title_label = QLabel("")
        self.title_label.setObjectName("titleLabel")
        self.subtitle_label = QLabel("")
        self.subtitle_label.setObjectName("subtitleLabel")
        title_layout.addWidget(self.title_label)
        title_layout.addWidget(self.subtitle_label)
        header_layout.addLayout(title_layout)

        right_header = QVBoxLayout()
        right_header.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.timestamp_label = QLabel("--")
        self.timestamp_label.setStyleSheet("color: #cbd5e1; font-size: 12px;")
        self.status_label = QLabel("")
        self.status_label.setObjectName("statusLabel")
        self.status_label.setStyleSheet("color: #22c55e;")
        # 언어 선택 콤보박스 추가
        self.lang_combo = QComboBox()
        self.lang_combo.addItems(["English", "한국어"])
        self.lang_combo.setCurrentIndex(0)
        self.lang_combo.setFixedWidth(120)
        self.lang_combo.currentIndexChanged.connect(self.on_language_changed)
        right_header.addWidget(self.lang_combo, 0, Qt.AlignmentFlag.AlignRight)
        right_header.addWidget(self.timestamp_label, 0, Qt.AlignmentFlag.AlignRight)
        right_header.addWidget(self.status_label, 0, Qt.AlignmentFlag.AlignRight)
        header_layout.addLayout(right_header)
        main_layout.addWidget(header_widget)
        # header 고정(0), content 가변(1)
        main_layout.setStretch(0, 0)

        content_layout = QHBoxLayout()
        content_layout.setSpacing(16)

        self.video_group = QGroupBox("")
        video_layout = QVBoxLayout()
        self.video_label = QLabel("")
        self.video_label.setObjectName("cameraLabel")
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # ------------------------------------------------------------------
        # [수정 2] 최소 높이 값들을 줄여서 콘텐츠 전체 높이 합이
        # 실제 창 높이를 넘지 않도록 함 (380 -> 240).
        # ------------------------------------------------------------------
        self.video_label.setMinimumHeight(240)

        self.video_label.setStyleSheet("background-color: #020617; color: #f8fafc;")
        video_layout.addWidget(self.video_label)
        self.video_group.setLayout(video_layout)
        content_layout.addWidget(self.video_group, 2)

        self.data_group = QGroupBox("")
        data_layout = QVBoxLayout()

        metrics_layout = QGridLayout()
        metrics_layout.setSpacing(12)

        (self.hr_card, self.hr_title_label, self.hr_value_label, self.hr_unit_label,
         self.hr_progress, self.hr_hint_label) = self.build_metric_card(
            "", "", "", "#38bdf8"
        )
        (self.spo2_card, self.spo2_title_label, self.spo2_value_label, self.spo2_unit_label,
         self.spo2_progress, self.spo2_hint_label) = self.build_metric_card(
            "", "", "", "#34d399"
        )
        (self.stress_card, self.stress_title_label, self.stress_value_label, self.stress_unit_label,
         self.stress_progress, self.stress_hint_label) = self.build_metric_card(
            "", "", "", "#f43f5e"
        )

        metrics_layout.addWidget(self.hr_card, 0, 0)
        metrics_layout.addWidget(self.spo2_card, 0, 1)
        metrics_layout.addWidget(self.stress_card, 0, 2)
        data_layout.addLayout(metrics_layout)

        self.graph_widget = pg.PlotWidget()
        self.graph_widget.setBackground('#020617')
        self.graph_widget.setLabel('left', '')
        self.graph_widget.setLabel('bottom', '')

        # ------------------------------------------------------------------
        # [수정 2] 그래프 최소 높이도 축소 (420 -> 260)
        # ------------------------------------------------------------------
        self.graph_widget.setMinimumHeight(260)

        self.graph_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.graph_widget.showGrid(x=True, y=True, alpha=0.2)
        self.graph_line = self.graph_widget.plot(pen=pg.mkPen(color='#f43f5e', width=2))

        # ------------------------------------------------------------------
        # [수정 4] pyqtgraph의 PlotItem은 축 라벨(제목)이 들어갈 공간을
        # 기본적으로 충분히 예약하지 않아서, 위젯이 작아지면 x축/y축
        # 라벨 텍스트가 잘리는 문제가 발생함. 축 높이/너비와 여백을
        # 명시적으로 늘려서 라벨이 잘리지 않도록 함.
        # ------------------------------------------------------------------
        bottom_axis = self.graph_widget.getAxis('bottom')
        left_axis = self.graph_widget.getAxis('left')
        bottom_axis.setHeight(45)   # 축 눈금 + 라벨 텍스트가 들어갈 높이 확보
        left_axis.setWidth(55)      # 축 눈금 + 라벨 텍스트가 들어갈 너비 확보
        self.graph_widget.getPlotItem().layout.setContentsMargins(10, 10, 20, 15)

        data_layout.addWidget(self.graph_widget)

        self.info_label = QLabel("")
        self.info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.info_label.setWordWrap(True)
        self.info_label.setStyleSheet(
            "font-size: 13px; color: #cbd5e1; padding: 8px; background: #0f172a; border-radius: 8px;"
        )
        data_layout.addWidget(self.info_label)

        # 메트릭(0), 그래프(1), 정보(2) 순서로 그래프에 비례 높이를 부여
        data_layout.setStretch(0, 0)
        data_layout.setStretch(1, 1)
        data_layout.setStretch(2, 0)

        self.data_group.setLayout(data_layout)
        content_layout.addWidget(self.data_group, 3)
        main_layout.addLayout(content_layout)
        # content 레이아웃이 남은 공간을 차지
        main_layout.setStretch(1, 1)
        # 초기 언어 적용
        self.set_language(self.lang)

    def build_metric_card(self, title, unit, hint, color):
        card = QFrame()
        card.setObjectName("metricCard")
        card.setMinimumHeight(100)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(8)

        title_label = QLabel(title)
        title_label.setObjectName("metricTitle")
        layout.addWidget(title_label)

        value_layout = QHBoxLayout()
        value_label = QLabel("0")
        value_label.setObjectName("metricValue")
        value_label.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        value_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        value_label.setMinimumWidth(100)

        unit_label = QLabel(unit)
        unit_label.setObjectName("metricHint")
        unit_label.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight)
        unit_label.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Preferred)

        value_layout.addWidget(value_label, 1)
        value_layout.addWidget(unit_label, 0)
        layout.addLayout(value_layout)

        progress_bar = QProgressBar()
        progress_bar.setRange(0, 100)
        progress_bar.setValue(0)
        progress_bar.setFixedHeight(8)
        # ------------------------------------------------------------------
        # [수정 5] 바 높이가 8px밖에 안 되는데 기본적으로 "50%" 같은
        # 퍼센트 텍스트를 중앙에 그리려고 해서 위아래로 잘려 보이는
        # 문제였음. 텍스트를 아예 끄고 색상 바만 표시하도록 변경.
        # ------------------------------------------------------------------
        progress_bar.setTextVisible(False)
        progress_bar.setStyleSheet(f"QProgressBar::chunk {{ background: {color}; }}")
        layout.addWidget(progress_bar)

        hint_label = QLabel(hint)
        hint_label.setObjectName("metricHint")
        layout.addWidget(hint_label)

        return card, title_label, value_label, unit_label, progress_bar, hint_label

    def init_camera(self):
        """OpenCV를 이용한 웹캠 캡처 초기화"""
        # 기본 장치로 먼저 시도
        self.cap = cv2.VideoCapture(0)
        if not self.cap.isOpened():
            # Windows 환경에서는 DirectShow 백엔드를 시도
            try:
                self.cap.release()
            except Exception:
                pass
            self.cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)

        self.cam_timer = QTimer()
        self.cam_timer.timeout.connect(self.update_frame)
        if self.cap.isOpened():
            self.cam_timer.start(30)
        else:
            # 카메라를 열지 못하면 안내 텍스트만 남기고 타이머는 시작하지 않음
            self.video_label.setText(self.t('initializing_camera'))

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
        try:
            self.cursor.execute('''
                INSERT INTO sensor_log (heart_rate, spo2, stress_level)
                VALUES (?, ?, ?)
            ''', (hr, spo2, stress))
            self.conn.commit()
        except (sqlite3.ProgrammingError, AttributeError):
            # 커넥션이 닫혀있거나 커서가 유효하지 않을 경우 재초기화 후 재시도
            try:
                self.init_db()
                self.cursor.execute('''
                    INSERT INTO sensor_log (heart_rate, spo2, stress_level)
                    VALUES (?, ?, ?)
                ''', (hr, spo2, stress))
                self.conn.commit()
            except Exception:
                # 실패 시 로깅 대신 무시하여 UI 업데이트는 계속 진행
                pass

    def update_ui(self, hr, spo2, stress):
        """그래프 선 이동 및 텍스트 상태 업데이트"""
        self.hr_data = self.hr_data[1:] + [hr]
        self.graph_line.setData(self.time_data, self.hr_data)

        self.hr_value_label.setText(f"{hr:.1f}")
        self.hr_progress.setValue(int(min(100, max(0, (hr / 120) * 100))))
        self.hr_hint_label.setText(self.t('stable') if 60 <= hr <= 90 else self.t('needs_attention'))

        self.spo2_value_label.setText(f"{spo2:.1f}")
        self.spo2_progress.setValue(int(min(100, max(0, spo2))))
        self.spo2_hint_label.setText(self.t('normal') if spo2 >= 95 else self.t('low_oxygen'))

        self.stress_value_label.setText(f"{stress:.1f}")
        self.stress_progress.setValue(int(min(100, max(0, stress))))
        if stress >= 70:
            self.stress_hint_label.setText(self.t('high_stress'))
            self.stress_value_label.setStyleSheet("color: #fb7185;")
        elif stress >= 40:
            self.stress_hint_label.setText(self.t('watch'))
            self.stress_value_label.setStyleSheet("color: #f59e0b;")
        else:
            self.stress_hint_label.setText(self.t('relaxed'))
            self.stress_value_label.setStyleSheet("color: #f8fafc;")

        self.timestamp_label.setText(QDateTime.currentDateTime().toString("yyyy-MM-dd hh:mm:ss"))
        if stress >= 70:
            self.status_label.setText(self.t('status_high'))
            self.status_label.setStyleSheet("color: #fb7185;")
        elif stress >= 40:
            self.status_label.setText(self.t('status_watch'))
            self.status_label.setStyleSheet("color: #f59e0b;")
        else:
            self.status_label.setText(self.t('status_stable'))
            self.status_label.setStyleSheet("color: #22c55e;")

        info_text = (
            f"{self.t('last_updated_prefix')} {QDateTime.currentDateTime().toString('hh:mm:ss')} | "
            f"{self.t('heart_rate')}: {hr:.1f} {self.t('hr_unit')} | {self.t('spo2')}: {spo2:.1f}{self.t('spo2_unit')} | {self.t('stress')}: {stress:.1f}"
        )
        self.info_label.setText(info_text)

    def t(self, key):
        return self.translations.get(self.lang, {}).get(key, key)

    def on_language_changed(self, index):
        self.lang = 'en' if index == 0 else 'ko'
        self.set_language(self.lang)

    def set_language(self, lang):
        # 창 제목
        self.setWindowTitle(self.translations[lang]['window_title'])
        # 헤더
        self.title_label.setText(self.translations[lang]['title_main'])
        self.subtitle_label.setText(self.translations[lang]['subtitle'])
        # 그룹 타이틀
        self.video_group.setTitle(self.translations[lang]['live_camera'])
        self.data_group.setTitle(self.translations[lang]['operational_metrics'])
        # 메트릭 카드
        self.hr_title_label.setText(self.translations[lang]['heart_rate'])
        self.hr_unit_label.setText(self.translations[lang]['hr_unit'])
        self.hr_hint_label.setText(self.translations[lang]['hr_hint'])

        self.spo2_title_label.setText(self.translations[lang]['spo2'])
        self.spo2_unit_label.setText(self.translations[lang]['spo2_unit'])
        self.spo2_hint_label.setText(self.translations[lang]['spo2_hint'])

        self.stress_title_label.setText(self.translations[lang]['stress'])
        self.stress_unit_label.setText(self.translations[lang]['stress_unit'])
        self.stress_hint_label.setText(self.translations[lang]['stress_hint'])

        # 그래프
        try:
            self.graph_widget.setTitle(self.translations[lang]['graph_title'])
        except Exception:
            pass
        self.graph_widget.setLabel('left', self.translations[lang]['left_label'])
        self.graph_widget.setLabel('bottom', self.translations[lang]['bottom_label'])

        # 기타
        self.video_label.setText(self.translations[lang]['initializing_camera'])
        self.info_label.setText(self.translations[lang]['waiting'])
        self.status_label.setText(self.translations[lang]['status_stable'])
        # 콤보박스 표시 (유저 친화적 표시값 유지)
        self.lang_combo.setCurrentIndex(0 if lang == 'en' else 1)

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
        # 타이머 정지
        try:
            self.cam_timer.stop()
        except Exception:
            pass
        try:
            self.test_timer.stop()
        except Exception:
            pass
        try:
            self.conn.close()
        except Exception:
            pass
        event.accept()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = StressMonitorApp()
    window.show()
    sys.exit(app.exec())