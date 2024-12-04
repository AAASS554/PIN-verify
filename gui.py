from admin import CardAuth  # 从admin.py导入CardAuth类
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                           QHBoxLayout, QPushButton, QLabel, QLineEdit,
                           QComboBox, QCheckBox, QSlider, QMessageBox, QFrame, QGridLayout)
from PyQt5.QtCore import Qt, QSize, QPoint
from PyQt5.QtGui import QFont, QIcon, QColor, QPalette
import sys
import pymysql
from sshtunnel import SSHTunnelForwarder
import time
import random
import string
import datetime
import uuid

class DatabaseConnection:
    # SSH隧道配置
    SSH_CONFIG = {
        'ssh_host': '0',
        'ssh_port': 22,
        'ssh_username': '0',
        'ssh_password': '0',
    }

    # 数据库配置
    DB_CONFIG = {
        'host': '127.0.0.1',
        'user': '0',
        'password': '0',
        'database': 'u',
        'port': 3306,
    }

    def __init__(self):
        self.tunnel = None
        self.connection = None
        self._connect_attempts = 0
        self._max_attempts = 3
        self._retry_delay = 1

    def connect(self):
        while self._connect_attempts < self._max_attempts:
            try:
                if self.tunnel and self.tunnel.is_active:
                    self.close()
                    
                self.tunnel = SSHTunnelForwarder(
                    (self.SSH_CONFIG['ssh_host'], self.SSH_CONFIG['ssh_port']),
                    ssh_username=self.SSH_CONFIG['ssh_username'],
                    ssh_password=self.SSH_CONFIG['ssh_password'],
                    remote_bind_address=('127.0.0.1', 3306)
                )
                
                self.tunnel.start()

                self.connection = pymysql.connect(
                    host=self.DB_CONFIG['host'],
                    user=self.DB_CONFIG['user'],
                    password=self.DB_CONFIG['password'],
                    database=self.DB_CONFIG['database'],
                    port=self.tunnel.local_bind_port,
                    charset='utf8mb4',
                    cursorclass=pymysql.cursors.DictCursor
                )
                
                self._connect_attempts = 0
                return self.connection
                
            except Exception as e:
                self._connect_attempts += 1
                print(f"连接失败 ({self._connect_attempts}/{self._max_attempts}): {str(e)}")
                if self._connect_attempts < self._max_attempts:
                    time.sleep(self._retry_delay)
                self.close()
                
        print("达到最大重试次数，连接失败")
        return None

    def close(self):
        if self.connection:
            self.connection.close()
        if self.tunnel:
            self.tunnel.close()

class CustomSlider(QWidget):
    def __init__(self, title, default_value, min_value, max_value, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 0, 5, 0)
        
        # 数值显示
        self.value_label = QLabel(f"{default_value:.3f}")
        self.value_label.setFixedWidth(50)
        self.value_label.setStyleSheet("color: #ffff00;")
        layout.addWidget(self.value_label)
        
        # 滑块
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(min_value, max_value)
        self.slider.setValue(int(default_value * 1000))
        self.slider.valueChanged.connect(self.update_value)
        layout.addWidget(self.slider)
        
        # 标题
        title_label = QLabel(title)
        title_label.setStyleSheet("color: #00ff00;")
        layout.addWidget(title_label)
    
    def update_value(self):
        value = self.slider.value() / 1000
        self.value_label.setText(f"{value:.3f}")

class GroupBox(QFrame):
    def __init__(self, title, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            QFrame {
                border: 1px solid #3d3d3d;
                border-radius: 5px;
                padding: 5px;
                background-color: #252525;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(5)
        
        title_label = QLabel(title)
        title_label.setStyleSheet("color: #00ff00; font-weight: bold;")
        layout.addWidget(title_label)

class HackWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.auth = CardAuth()  # 创建CardAuth实例
        self.init_system()
        self.init_ui()
        self.init_events()
        
        # 添加状态变量
        self.is_running = False
        self.current_direction = None
        self.is_recoil_active = False
        self.is_pressure_active = False
        self.hotkeys = {
            'aim': None,  # 瞄准热键
            'trigger': None  # 扳机热键
        }
        self.waiting_for_hotkey = False
        self.current_hotkey_type = None
    
    def init_system(self):
        """初始化系统"""
        try:
            import pygame
            pygame.init()
        except:
            pass

    def init_events(self):
        """初始化所有事件绑定"""
        # ... (保持其他事件绑定不变)

        # 启动分类事件绑定
        if hasattr(self, 'sendinput_combo'):
            self.sendinput_combo.currentTextChanged.connect(self.on_sendinput_change)
        
        # 热键按钮事件
        if hasattr(self, 'aim_hotkey_btn'):
            self.aim_hotkey_btn.clicked.connect(lambda: self.set_hotkey('aim'))
        if hasattr(self, 'trigger_hotkey_btn'):
            self.trigger_hotkey_btn.clicked.connect(lambda: self.set_hotkey('trigger'))
        
        # 方向按钮事件
        if hasattr(self, 'direction_btns'):
            for btn in self.direction_btns:
                btn.clicked.connect(lambda checked, b=btn: self.on_direction_click(b))
        
        # 启动按钮事件
        if hasattr(self, 'recoil_btn'):
            self.recoil_btn.clicked.connect(self.toggle_recoil)
        if hasattr(self, 'pressure_btn'):
            self.pressure_btn.clicked.connect(self.toggle_pressure)

    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle('记得晚安 3.1')
        self.setFixedSize(380, 650)  # 调整窗口大小
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)  # 无边框窗口
        
        # 设置整体样式
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1a1a1a;
                border: 1px solid #3d3d3d;
            }
            QWidget {
                background-color: #1a1a1a;
                color: #cccccc;
            }
            QComboBox {
                background-color: #1a1a1a;
                border: 1px solid #3d3d3d;
                color: #cccccc;
                padding: 2px 5px;
                height: 20px;
            }
            QPushButton {
                background-color: #1a1a1a;
                border: 1px solid #3d3d3d;
                color: #cccccc;
                padding: 2px;
                height: 20px;
            }
            QPushButton:checked {
                background-color: #3d3d3d;
                color: #ffffff;
            }
            QLineEdit {
                background-color: #1a1a1a;
                border: 1px solid #3d3d3d;
                color: #cccccc;
                padding: 2px 5px;
                height: 20px;
            }
        """)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(2)
        main_layout.setContentsMargins(5, 5, 5, 5)
        
        # 顶部信息区域
        info_group = QWidget()
        info_layout = QVBoxLayout(info_group)
        info_layout.setSpacing(1)
        info_layout.setContentsMargins(2, 2, 2, 2)
        
        info_text = """软件无毒无充 接受但不限于360，火绒等进行扫描
此软件为永久公开免费软件！！！！
更新内容 预瞄准功能
扳机玩自由自定义
QQ 1412800823
1412800823@qq.com
------两岸猿声啼不住，轻舟已过万重山。"""
        
        info_label = QLabel(info_text)
        info_label.setStyleSheet("""
            color: #ff6b6b;
            font-size: 12px;
            padding: 2px;
        """)
        info_layout.addWidget(info_label)
        
        # 状态指示器
        status_layout = QHBoxLayout()
        self.status_indicator = QLabel("●")
        self.status_indicator.setStyleSheet("color: #ff0000;")  # 初始为红色
        status_layout.addWidget(self.status_indicator)
        status_layout.addWidget(QLabel("状态"))
        info_layout.addLayout(status_layout)  # 添加到info_layout中
        
        # 卡密验证区域
        auth_layout = QHBoxLayout()
        auth_layout.setSpacing(2)
        self.card_input = QLineEdit()
        self.card_input.setPlaceholderText('请输入卡密')
        self.card_input.setFixedHeight(25)  # 固定高度
        auth_layout.addWidget(self.card_input)
        
        verify_btn = QPushButton('验证')
        verify_btn.setFixedSize(50, 25)  # 固定大小
        verify_btn.clicked.connect(self.verify_card)
        verify_btn.setStyleSheet("""
            QPushButton {
                background-color: #1a1a1a;
                border: 1px solid #3d3d3d;
                color: #00ff00;
                padding: 2px;
            }
            QPushButton:hover {
                background-color: #2d2d2d;
            }
        """)
        auth_layout.addWidget(verify_btn)
        info_layout.addLayout(auth_layout)
        
        main_layout.addWidget(info_group)
        
        # 功能区域
        self.func_group = QWidget()
        func_layout = QVBoxLayout(self.func_group)
        func_layout.setSpacing(10)
        
        # 模型选择区域
        model_group = QWidget()
        model_layout = QVBoxLayout(model_group)
        model_layout.setSpacing(2)
        model_layout.setContentsMargins(2, 2, 2, 2)
        
        # 文件选择
        file_layout = QHBoxLayout()
        file_label = QLabel('/onnx\\')
        file_label.setFixedWidth(40)
        file_layout.addWidget(file_label)
        
        self.file_combo = QComboBox()
        self.file_combo.setFixedHeight(25)
        self.file_combo.addItems([
            'cs2.onnx', 'apex.onnx', 'cai6.onnx', 'COD20.onnx',
            'cod20??.onnx', 'Apex.onnx', 'PUBG 8w_320.onnx', 'pubg.onnx'
        ])
        self.file_combo.setStyleSheet("""
            QComboBox {
                background-color: #1a1a1a;
                border: 1px solid #3d3d3d;
                padding: 2px 5px;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox::down-arrow {
                image: url(down_arrow.png);
                width: 12px;
                height: 12px;
            }
        """)
        file_layout.addWidget(self.file_combo)
        model_layout.addLayout(file_layout)
        
        # 控制区域
        control_group = QWidget()
        control_layout = QVBoxLayout(control_group)
        control_layout.setSpacing(2)
        control_layout.setContentsMargins(2, 2, 2, 2)
        
        # 自动分辨率选项
        auto_res = QCheckBox('自动分辨率 如果识别不对就关了自己输入游戏的的')
        auto_res.setStyleSheet("""
            QCheckBox {
                color: #00ff00;
                spacing: 5px;
            }
            QCheckBox::indicator {
                width: 15px;
                height: 15px;
                background-color: #1a1a1a;
                border: 1px solid #3d3d3d;
            }
            QCheckBox::indicator:checked {
                background-color: #00ff00;
            }
        """)
        control_layout.addWidget(auto_res)
        
        # 滑块区域
        slider_group = QWidget()
        slider_layout = QVBoxLayout(slider_group)
        slider_layout.setSpacing(1)
        slider_layout.setContentsMargins(2, 2, 2, 2)
        
        # 添加滑块
        for title, default, max_val in [
            ("偏移量", 0.250, 1000),
            ("灵敏度", 0.500, 1000),
            ("范围", 320, 1000)
        ]:
            slider_row = QHBoxLayout()
            slider_row.setSpacing(2)
            
            value_label = QLabel(f"{default:.3f}" if isinstance(default, float) else str(default))
            value_label.setStyleSheet("color: #ffff00;")
            value_label.setFixedWidth(50)
            value_label.setAlignment(Qt.AlignmentFlag.AlignRight)
            slider_row.addWidget(value_label)
            
            slider = QSlider(Qt.Orientation.Horizontal)
            slider.setFixedHeight(15)
            slider.setRange(0, max_val)
            slider.setValue(int(default * 1000) if isinstance(default, float) else default)
            slider.setStyleSheet("""
                QSlider::groove:horizontal {
                    height: 4px;
                    background: #3d3d3d;
                }
                QSlider::handle:horizontal {
                    background: #ffff00;
                    width: 10px;
                    height: 10px;
                    margin: -3px 0;
                }
            """)
            slider_row.addWidget(slider)
            
            title_label = QLabel(title)
            title_label.setFixedWidth(50)
            slider_row.addWidget(title_label)
            
            slider_layout.addLayout(slider_row)
        
        func_layout.addWidget(model_group)
        
        # 块控制区域
        slider_group = QWidget()
        slider_layout = QVBoxLayout(slider_group)
        slider_layout.setSpacing(5)
        
        # 偏移量滑块
        self.add_slider_control(slider_layout, "偏移量", 0.250, 1000)
        # 敏度滑块
        self.add_slider_control(slider_layout, "灵敏度", 0.500, 1000)
        # 范围滑块
        self.add_slider_control(slider_layout, "范围", 320, 1000, is_integer=True)
        
        func_layout.addWidget(slider_group)
        
        # 启动分类区域
        launch_group = QWidget()
        launch_layout = QVBoxLayout(launch_group)
        launch_layout.setSpacing(2)
        launch_layout.setContentsMargins(5, 5, 5, 5)

        # Sendinput下拉框
        sendinput_layout = QHBoxLayout()
        self.sendinput_combo = QComboBox()
        self.sendinput_combo.addItem("Sendinput")
        self.sendinput_combo.setStyleSheet("""
            QComboBox {
                background-color: #1a1a1a;
                border: 1px solid #3d3d3d;
                color: #ffffff;
                padding: 5px;
            }
        """)
        sendinput_layout.addWidget(self.sendinput_combo)
        launch_layout.addLayout(sendinput_layout)

        # 间隔值区域
        intervals_group = QWidget()
        intervals_layout = QVBoxLayout(intervals_group)
        intervals_layout.setSpacing(1)
        intervals_layout.setContentsMargins(0, 0, 0, 0)

        # 创建三个间隔值显示行
        self.interval_values = []
        interval_labels = [
            ("前瞄间隔", "0"),
            ("激活间隔", "0"),
            ("激活范围", "0")
        ]

        for label_text, default_value in interval_labels:
            row_layout = QHBoxLayout()
            row_layout.setSpacing(2)
            
            # 黄色方块按钮
            square_btn = QPushButton()
            square_btn.setFixedSize(12, 12)
            square_btn.setStyleSheet("""
                QPushButton {
                    background-color: #ffff00;
                    border: none;
                }
                QPushButton:checked {
                    background-color: #808000;
                }
            """)
            square_btn.setCheckable(True)
            row_layout.addWidget(square_btn)
            
            # 数值显示
            value_label = QLabel(default_value)
            value_label.setStyleSheet("color: #ffff00;")
            value_label.setFixedWidth(30)
            value_label.setAlignment(Qt.AlignmentFlag.AlignRight)
            row_layout.addWidget(value_label)
            
            # 标签
            label = QLabel(label_text)
            label.setStyleSheet("color: #cccccc;")
            row_layout.addWidget(label)
            row_layout.addStretch()
            
            intervals_layout.addLayout(row_layout)
            self.interval_values.append((square_btn, value_label))

        launch_layout.addWidget(intervals_group)

        # 方向按钮组
        directions_group = QWidget()
        directions_layout = QVBoxLayout(directions_group)
        directions_layout.setSpacing(1)
        directions_layout.setContentsMargins(0, 0, 0, 0)

        # 第一排方向按钮
        dir1_layout = QHBoxLayout()
        dir1_layout.setSpacing(1)
        for direction in ["左", "右", "中", "侧1", "侧2"]:
            btn = QPushButton(direction)
            btn.setFixedSize(30, 20)
            btn.setCheckable(True)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #1a1a1a;
                    border: 1px solid #3d3d3d;
                    color: #cccccc;
                    padding: 2px;
                }
                QPushButton:checked {
                    background-color: #3d3d3d;
                    color: #ffffff;
                }
            """)
            dir1_layout.addWidget(btn)
        directions_layout.addLayout(dir1_layout)

        # 第二排方向按钮
        dir2_layout = QHBoxLayout()
        dir2_layout.setSpacing(1)
        for direction in ["all", "右", "中", "侧1", "侧2"]:
            btn = QPushButton(direction)
            btn.setFixedSize(30, 20)
            btn.setCheckable(True)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #1a1a1a;
                    border: 1px solid #3d3d3d;
                    color: #cccccc;
                    padding: 2px;
                }
                QPushButton:checked {
                    background-color: #3d3d3d;
                    color: #ffffff;
                }
            """)
            dir2_layout.addWidget(btn)
        directions_layout.addLayout(dir2_layout)

        launch_layout.addWidget(directions_group)

        # X轴和Y轴速度
        speeds_group = QWidget()
        speeds_layout = QVBoxLayout(speeds_group)
        speeds_layout.setSpacing(1)
        speeds_layout.setContentsMargins(0, 0, 0, 0)

        for axis in ["X轴速度", "Y轴速"]:
            speed_layout = QHBoxLayout()
            speed_layout.setSpacing(2)
            
            # 黄色方块按钮
            square_btn = QPushButton()
            square_btn.setFixedSize(12, 12)
            square_btn.setStyleSheet("""
                QPushButton {
                    background-color: #ffff00;
                    border: none;
                }
                QPushButton:checked {
                    background-color: #808000;
                }
            """)
            square_btn.setCheckable(True)
            speed_layout.addWidget(square_btn)
            
            # 数值显示
            value_label = QLabel("0.000")
            value_label.setStyleSheet("color: #ffff00;")
            value_label.setFixedWidth(50)
            value_label.setAlignment(Qt.AlignmentFlag.AlignRight)
            speed_layout.addWidget(value_label)
            
            # 标签
            label = QLabel("越大越快")
            label.setStyleSheet("color: #cccccc;")
            speed_layout.addWidget(label)
            speed_layout.addStretch()
            
            speeds_layout.addLayout(speed_layout)

        launch_layout.addWidget(speeds_group)

        # 启动按钮组
        start_layout = QHBoxLayout()
        start_layout.setSpacing(5)
        self.start_recoil = QPushButton("启动后坐")
        self.start_pressure = QPushButton("启动压枪")
        for btn in [self.start_recoil, self.start_pressure]:
            btn.setFixedHeight(25)
            btn.setCheckable(True)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #1a1a1a;
                    border: 1px solid #3d3d3d;
                    color: #cccccc;
                    padding: 2px;
                }
                QPushButton:checked {
                    background-color: #3d3d3d;
                    color: #ffffff;
                }
            """)
        start_layout.addWidget(self.start_recoil)
        start_layout.addWidget(self.start_pressure)
        launch_layout.addLayout(start_layout)

        # 设置启动分类区域的样式
        launch_group.setStyleSheet("""
            QWidget {
                background-color: #1a1a1a;
            }
            QPushButton {
                background-color: transparent;
                border: 1px solid #3d3d3d;
                color: #cccccc;
                padding: 1px;
                height: 18px;
            }
            QPushButton:checked {
                background-color: #3d3d3d;
                color: #ffffff;
            }
            QLabel {
                color: #cccccc;
                font-size: 12px;
            }
        """)

        func_layout.addWidget(launch_group)
        main_layout.addWidget(self.func_group)
        
        # 初始状态：功能区域禁用
        self.func_group.setEnabled(False)
        
        # 设置窗口属性
        self.setFixedSize(400, 700)  # 增加窗口高度以容纳所有控件

    def add_slider_control(self, parent_layout, title, default_value, max_value, is_integer=False):
        """辅助方法：添加滑块控制"""
        layout = QHBoxLayout()
        
        # 值标签
        value_label = QLabel(str(default_value) if is_integer else f"{default_value:.3f}")
        value_label.setStyleSheet("color: #ffff00;")
        layout.addWidget(value_label)
        
        # 滑块
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(0, max_value)
        slider.setValue(default_value if is_integer else int(default_value * 1000))
        
        # 连接信号
        if is_integer:
            slider.valueChanged.connect(
                lambda v: value_label.setText(str(v))
            )
        else:
            slider.valueChanged.connect(
                lambda v: value_label.setText(f"{v/1000:.3f}")
            )
        
        layout.addWidget(slider)
        layout.addWidget(QLabel(title))
        
        parent_layout.addLayout(layout)
        return slider, value_label

    def on_sendinput_change(self, mode):
        """处理输入模式改变"""
        print(f"切换输入模式: {mode}")
        # TODO: 实现具体的输入模式切换逻辑

    def set_hotkey(self, hotkey_type):
        """设置热键"""
        self.waiting_for_hotkey = True
        self.current_hotkey_type = hotkey_type
        label = self.aim_hotkey_label if hotkey_type == 'aim' else self.trigger_hotkey_label
        label.setText("请按键...")

    def on_direction_click(self, button):
        """处理方向按钮点击"""
        # 取消其他按钮的选中状态
        for btn in self.direction_btns:
            if btn != button:
                btn.setChecked(False)
        
        self.current_direction = button.text()
        print(f"选择方向: {self.current_direction}")
        # TODO: 实现具体的方向切换逻辑

    def toggle_recoil(self):
        """切换后坐力状态"""
        self.is_recoil_active = not self.is_recoil_active
        self.recoil_btn.setChecked(self.is_recoil_active)
        print(f"后坐力状态: {'开启' if self.is_recoil_active else '关闭'}")
        # TODO: 实现具体的后坐力控制逻辑

    def toggle_pressure(self):
        """切换压枪状态"""
        self.is_pressure_active = not self.is_pressure_active
        self.pressure_btn.setChecked(self.is_pressure_active)
        print(f"压枪状态: {'开启' if self.is_pressure_active else '关闭'}")
        # TODO: 实现具体的压枪控制逻辑

    def keyPressEvent(self, event):
        """处理键盘事件"""
        if self.waiting_for_hotkey:
            key = event.key()
            key_text = event.text().upper()
            if self.current_hotkey_type == 'aim':
                self.hotkeys['aim'] = key
                self.aim_hotkey_label.setText(f"当前热键: {key_text}")
                print(f"设置瞄准热键: {key_text}")
            elif self.current_hotkey_type == 'trigger':
                self.hotkeys['trigger'] = key
                self.trigger_hotkey_label.setText(f"当前热键: {key_text}")
                print(f"设置扳机热键: {key_text}")
            self.waiting_for_hotkey = False
            self.current_hotkey_type = None
        super().keyPressEvent(event)
    def verify_card(self):
        """验证卡密"""
        try:
            card_key = self.card_input.text().strip()
            if not card_key:
                QMessageBox.warning(self, '错误', '请输入卡密')
                return
            
            # 获取机器码（这里需要根据实际情况获取）
            device_id = str(uuid.getnode())  # 使用MAC地址作为机器码
            
            success, message = self.auth.verify_card(card_key, device_id)
            if success:
                self.func_group.setEnabled(True)
                QMessageBox.information(self, '成功', message)
                self.card_input.setEnabled(False)
                if hasattr(self, 'status_indicator'):
                    self.status_indicator.setStyleSheet("color: #00ff00;")
            else:
                QMessageBox.warning(self, '错误', message)
        except Exception as e:
            QMessageBox.critical(self, '错误', f'验证过程出错: {str(e)}')

    def on_model_change(self, model_name):
        """处理模型切换事件"""
        # 根据不同模型设置相应的默认参数
        model_configs = {
            'cai6.onnx': {
                'offset': 0.250,
                'sensitivity': 0.500,
                'range': 320,
                'x_speed': 0.000,
                'y_speed': 0.000
            },
            'cs2.onnx': {
                'offset': 0.300,
                'sensitivity': 0.600,
                'range': 350,
                'x_speed': 0.000,
                'y_speed': 0.000
            }
        }
        
        # 获取当前模型的配置
        config = model_configs.get(model_name, model_configs['cai6.onnx'])
        
        try:
            # 更新UI控件的值
            self.offset_slider.setValue(int(config['offset'] * 1000))
            self.offset_value_label.setText(f"{config['offset']:.3f}")
            
            self.sens_slider.setValue(int(config['sensitivity'] * 1000))
            self.sens_value_label.setText(f"{config['sensitivity']:.3f}")
            
            self.range_slider.setValue(config['range'])
            self.range_value_label.setText(str(config['range']))
            
            self.x_axis_slider.setValue(int(config['x_speed'] * 1000))
            self.x_value_label.setText(f"{config['x_speed']:.3f}")
            
            self.y_axis_slider.setValue(int(config['y_speed'] * 1000))
            self.y_value_label.setText(f"{config['y_speed']:.3f}")
        except Exception as e:
            print(f"Error updating values: {str(e)}")

    def on_sendinput_change(self, mode):
        """处理输入模式改变"""
        print(f"Changed input mode to: {mode}")
        # TODO: 实现输入模式切换逻辑

    def set_hotkey(self, hotkey_type):
        """设置热键"""
        self.waiting_for_hotkey = True
        self.current_hotkey_type = hotkey_type
        label = self.aim_hotkey_label if hotkey_type == 'aim' else self.trigger_hotkey_label
        label.setText("请按键...")

    def on_interval_change(self, key, value):
        """处理间隔值改"""
        try:
            value = float(value)
            print(f"Changed {key} to: {value}")
            # TODO: 实现间隔值调整逻辑
        except ValueError:
            pass

    def on_slider_change_with_label(self, slider, label, value):
        """处理滑块值改变并更新标签"""
        if slider == self.offset_slider:
            label.setText(f"{value/1000:.3f}")
        elif slider == self.sens_slider:
            label.setText(f"{value/1000:.3f}")
        elif slider == self.range_slider:
            label.setText(str(value))

    def mousePressEvent(self, event):
        """处理鼠标按下事件"""
        if event.button() == Qt.LeftButton:
            try:
                self.drag_position = event.globalPos() - self.frameGeometry().topLeft()
                event.accept()
            except Exception as e:
                print(f"鼠标按下事件处理错误: {str(e)}")

    def mouseMoveEvent(self, event):
        """处理鼠标移动事件"""
        try:
            if event.buttons() & Qt.LeftButton:
                new_pos = event.globalPos() - self.drag_position
                # 确保窗口不会移出屏幕
                screen = QApplication.primaryScreen().geometry()
                x = max(0, min(new_pos.x(), screen.width() - self.width()))
                y = max(0, min(new_pos.y(), screen.height() - self.height()))
                self.move(x, y)
        except Exception as e:
            print(f"鼠标移动事件处理错误: {str(e)}")

def main():
    app = QApplication(sys.argv)
    window = HackWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main() 