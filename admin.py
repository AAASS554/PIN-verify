from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                           QHBoxLayout, QPushButton, QLabel, QLineEdit,
                           QTableWidget, QTableWidgetItem, QMessageBox,
                           QComboBox, QFileDialog, QGroupBox, QDialog, QGridLayout,
                           QDateTimeEdit)
from PyQt5.QtCore import Qt, QDateTime
import sys
import csv
import pymysql
from sshtunnel import SSHTunnelForwarder
import time
import random
import string
import datetime

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
        'host': '',
        'user': '0',
        'password': '',
        'database': '',
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
        """安全关闭连接"""
        try:
            if self.connection:
                self.connection.close()
                self.connection = None
            if self.tunnel:
                self.tunnel.close()
                self.tunnel = None
        except Exception as e:
            print(f"关闭连接错误: {str(e)}")

    def ensure_connection(self):
        """确保连接可用"""
        try:
            # 检查连接是否有效
            if self.connection and self.tunnel and self.tunnel.is_active:
                try:
                    self.connection.ping()
                    return self.connection
                except:
                    pass
            
            # 如果连接无效，关闭旧连接并创建新连接
            self.close()
            return self.connect()
            
        except Exception as e:
            print(f"确保连接错误: {str(e)}")
            self.close()
            return None

class CardAuth:
    def __init__(self):
        self.db = DatabaseConnection()

    def get_connection(self):
        """获取数据库连接"""
        return self.db.ensure_connection()

    def _generate_random_key(self, length=16):
        """生成随机卡密"""
        characters = string.ascii_letters + string.digits
        return ''.join(random.choice(characters) for _ in range(length))

    def generate_cards(self, days, count=1):
        """批量生成卡密"""
        connection = self.get_connection()
        if not connection:
            return []
        
        try:
            card_keys = []
            with connection.cursor() as cursor:
                for _ in range(count):
                    while True:
                        card_key = self._generate_random_key()
                        cursor.execute("SELECT id FROM card_keys WHERE card_key = %s", (card_key,))
                        if not cursor.fetchone():
                            break
                    
                    sql = """INSERT INTO card_keys 
                            (card_key, valid_days, create_time, status) 
                            VALUES (%s, %s, NOW(), 0)"""
                    cursor.execute(sql, (card_key, days))
                    card_keys.append(card_key)
                
                connection.commit()
                return card_keys
            
        except Exception as e:
            print(f"批量生成卡密错误: {str(e)}")
            return []
        
        finally:
            pass  # 不在这里关闭连接

    def verify_card(self, card_key, device_id=None):
        """验证卡密"""
        connection = self.get_connection()
        if not connection:
            return False, "数据库连接失败"
        
        try:
            with connection.cursor() as cursor:
                sql = """SELECT id, valid_days, create_time, status, use_time, device_id
                        FROM card_keys WHERE card_key = %s"""
                cursor.execute(sql, (card_key,))
                result = cursor.fetchone()
                
                if not result:
                    return False, "无效的卡密"
                    
                card_id = result['id']
                valid_days = result['valid_days']
                status = result['status']
                use_time = result['use_time']
                bound_device = result['device_id']
                
                if status == 1:
                    # 检查机器码
                    if device_id:
                        if bound_device and bound_device != device_id:
                            return False, "卡密已绑定其他机器"
                        elif not bound_device:
                            # 绑定机器码
                            cursor.execute("""
                                UPDATE card_keys 
                                SET device_id = %s, bind_time = NOW() 
                                WHERE id = %s
                            """, (device_id, card_id))
                            connection.commit()
                    
                    if use_time:
                        expiry_time = use_time + datetime.timedelta(days=valid_days)
                        if datetime.datetime.now() > expiry_time:
                            return False, "卡密已过期"
                        return True, "卡密验证成功"
                    return False, "卡密状态异常"
                
                # 首次使用卡密
                update_sql = """UPDATE card_keys 
                               SET status = 1, use_time = NOW(),
                                   device_id = %s, bind_time = NOW()
                               WHERE id = %s"""
                cursor.execute(update_sql, (device_id, card_id))
                connection.commit()
                
                return True, "卡密激活成功"
                
        except Exception as e:
            print(f"验证卡密错误: {str(e)}")
            return False, f"验证失败: {str(e)}"
            
        finally:
            pass  # 不在这里关闭连接

    def delete_card(self, card_key):
        """删除卡密"""
        connection = self.get_connection()
        if not connection:
            return False, "数据库连接失败"
        
        try:
            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM card_keys WHERE card_key = %s", (card_key,))
                if cursor.rowcount > 0:
                    connection.commit()
                    return True, "卡密删除成功"
                return False, "卡密不存在"
            
        except Exception as e:
            print(f"删除卡密错误: {str(e)}")
            return False, f"删除失败: {str(e)}"
        
        finally:
            pass  # 不在这里关闭连接

    def edit_card(self, card_key, valid_days=None, status=None, use_time=None):
        """编辑卡密"""
        connection = self.get_connection()
        if not connection:
            return False, "数据库连接失败"
        
        try:
            with connection.cursor() as cursor:
                updates = []
                params = []
                
                if valid_days is not None:
                    updates.append("valid_days = %s")
                    params.append(valid_days)
                if status is not None:
                    updates.append("status = %s")
                    params.append(status)
                if use_time is not None:
                    updates.append("use_time = %s")
                    params.append(use_time)
                    
                if not updates:
                    return False, "没有需要更新的内容"
                    
                params.append(card_key)
                sql = f"UPDATE card_keys SET {', '.join(updates)} WHERE card_key = %s"
                cursor.execute(sql, params)
                
                if cursor.rowcount > 0:
                    connection.commit()
                    return True, "卡密更新成功"
                return False, "卡密不存在"
                
        except Exception as e:
            print(f"编辑卡密错误: {str(e)}")
            return False, f"编辑失败: {str(e)}"
            
        finally:
            pass  # 在这里关闭连接

class AdminPanel(QMainWindow):
    def __init__(self):
        super().__init__()
        self.auth = CardAuth()
        self.init_ui()
        self.update_database()

    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle('卡密管理系统')
        self.setFixedSize(1400, 700)
        
        # 设置整体样式
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f6f6f6;
            }
            QWidget {
                color: #333333;
                font-size: 12px;
            }
            QPushButton {
                background-color: #20a53a;
                color: white;
                border: none;
                padding: 5px 15px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #1b8a31;
            }
            QLineEdit, QComboBox {
                border: 1px solid #dcdfe6;
                border-radius: 3px;
                padding: 5px;
                background: white;
            }
            QGroupBox {
                border: 1px solid #ebeef5;
                border-radius: 3px;
                margin-top: 10px;
                background-color: white;
            }
            QTableWidget {
                border: 1px solid #ebeef5;
                background-color: white;
                gridline-color: #ebeef5;
            }
            QTableWidget::item {
                padding: 8px;
                border-bottom: 1px solid #ebeef5;
            }
            QHeaderView::section {
                background-color: #fafafa;
                padding: 8px;
                border: none;
                border-bottom: 2px solid #ebeef5;
                font-weight: bold;
            }
            QScrollBar:vertical {
                border: none;
                background: #f6f6f6;
                width: 8px;
            }
            QScrollBar::handle:vertical {
                background: #c0c4cc;
                border-radius: 4px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # 统计信息区域
        stats_group = QGroupBox("统计信息")
        stats_layout = QHBoxLayout()
        self.stats_labels = {}
        for stat in ['总数', '已用', '未用', '已过期']:
            label = QLabel(f"{stat}: 0")
            self.stats_labels[stat] = label
            stats_layout.addWidget(label)
        stats_group.setLayout(stats_layout)
        layout.addWidget(stats_group)

        # 卡密生成区域
        gen_group = QGroupBox("生成卡密")
        gen_layout = QHBoxLayout()
        
        self.days_input = QLineEdit()
        self.days_input.setPlaceholderText('有效期(天)')
        self.days_input.setFixedWidth(100)
        gen_layout.addWidget(self.days_input)
        
        self.count_input = QLineEdit()
        self.count_input.setPlaceholderText('生成数量')
        self.count_input.setFixedWidth(100)
        gen_layout.addWidget(self.count_input)
        
        gen_btn = QPushButton('生成卡密')
        gen_btn.clicked.connect(self.generate_cards)
        gen_layout.addWidget(gen_btn)
        
        export_btn = QPushButton('导出卡密')
        export_btn.clicked.connect(self.export_cards)
        gen_layout.addWidget(export_btn)
        
        gen_layout.addStretch()
        gen_group.setLayout(gen_layout)
        layout.addWidget(gen_group)

        # 搜索区域
        search_group = QGroupBox("搜索筛选")
        search_layout = QHBoxLayout()
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText('搜索卡密...')
        self.search_input.textChanged.connect(self.filter_table)
        search_layout.addWidget(self.search_input)
        
        self.status_filter = QComboBox()
        self.status_filter.addItems(['全部', '未使用', '已使用', '已过期'])
        self.status_filter.currentTextChanged.connect(self.filter_table)
        search_layout.addWidget(self.status_filter)
        
        # 添加操作按钮
        edit_btn = QPushButton('编辑')
        edit_btn.clicked.connect(self.edit_selected_card)
        edit_btn.setStyleSheet("""
            QPushButton {
                background-color: #409eff;
                color: white;
                border: none;
                padding: 5px 15px;
                border-radius: 3px;
                min-width: 60px;
            }
            QPushButton:hover {
                background-color: #3a8ee6;
            }
        """)
        search_layout.addWidget(edit_btn)
        
        del_btn = QPushButton('删除')
        del_btn.clicked.connect(self.delete_selected_card)
        del_btn.setStyleSheet("""
            QPushButton {
                background-color: #f56c6c;
                color: white;
                border: none;
                padding: 5px 15px;
                border-radius: 3px;
                min-width: 60px;
            }
            QPushButton:hover {
                background-color: #dd6161;
            }
        """)
        search_layout.addWidget(del_btn)
        
        unbind_btn = QPushButton('解绑')
        unbind_btn.clicked.connect(self.unbind_selected_card)
        unbind_btn.setStyleSheet("""
            QPushButton {
                background-color: #e6a23c;
                color: white;
                border: none;
                padding: 5px 15px;
                border-radius: 3px;
                min-width: 60px;
            }
            QPushButton:hover {
                background-color: #cf9236;
            }
        """)
        search_layout.addWidget(unbind_btn)
        
        # 添加刷新按钮
        refresh_btn = QPushButton('刷新数据')
        refresh_btn.clicked.connect(self.refresh_data)
        refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #409eff;
                color: white;
                border: none;
                padding: 5px 15px;
                border-radius: 3px;
                min-width: 60px;
            }
            QPushButton:hover {
                background-color: #3a8ee6;
            }
        """)
        search_layout.addWidget(refresh_btn)
        
        search_layout.addStretch()
        search_group.setLayout(search_layout)
        layout.addWidget(search_group)

        # 卡密列表
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            '卡密', '有效期', '创建时间', '状态', '使用时间', 
            '剩余天数', '机器码', '绑定时间'
        ])
        self.table.setColumnWidth(0, 220)  # 卡密列宽
        self.table.setColumnWidth(1, 80)   # 有效期列宽
        self.table.setColumnWidth(2, 160)  # 创建时间列宽
        self.table.setColumnWidth(3, 80)   # 状态列宽
        self.table.setColumnWidth(4, 160)  # 使用时间列宽
        self.table.setColumnWidth(5, 80)   # 剩余天数列宽
        self.table.setColumnWidth(6, 280)  # 机器码列宽
        self.table.setColumnWidth(7, 160)  # 绑定时间列宽
        
        # 禁用水平滚动条
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        # 设置表格的选择模式和行为
        self.table.setSelectionBehavior(QTableWidget.SelectRows)  # 整行选择
        self.table.setSelectionMode(QTableWidget.SingleSelection)  # 单行选择
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)   # 禁止编辑
        
        # 设置表头样式
        header = self.table.horizontalHeader()
        header.setStretchLastSection(False)  # 最后一列不自动拉伸
        header.setDefaultAlignment(Qt.AlignLeft)  # 表头左对齐
        
        layout.addWidget(self.table)

        # 定义为类属性，这样其他方法也能访问
        self.btn_style = """
            QPushButton {
                padding: 3px 8px;
                font-size: 12px;
                min-width: 45px;
                max-width: 45px;
                height: 24px;
                border-radius: 2px;
            }
            QPushButton[text="编辑"] {
                background-color: #409eff;
            }
            QPushButton[text="编辑"]:hover {
                background-color: #3a8ee6;
            }
            QPushButton[text="删除"] {
                background-color: #f56c6c;
            }
            QPushButton[text="删除"]:hover {
                background-color: #dd6161;
            }
            QPushButton[text="解绑"] {
                background-color: #e6a23c;
            }
            QPushButton[text="解绑"]:hover {
                background-color: #cf9236;
            }
        """

        # 修改刷新按钮样式
        refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #409eff;
                color: white;
                border: none;
                padding: 5px 15px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #3a8ee6;
            }
        """)

        # 修改表格样式
        self.table.setAlternatingRowColors(True)  # 交替行颜色
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: white;
                alternate-background-color: #fafafa;
            }
            QTableWidget::item:selected {
                background-color: #ecf5ff;
                color: #409eff;
            }
        """)

    def create_button_handler(self, func, card_key):
        def handler():
            func(card_key)
        return handler

    def update_database(self):
        """更新数据库显示"""
        connection = None
        try:
            # 确保之前的连接已关闭
            self.auth.db.close()
            
            connection = self.auth.db.connect()
            if not connection:
                QMessageBox.warning(self, '错误', '数据库连接失败')
                return

            with connection.cursor() as cursor:
                # 获取统计息
                cursor.execute("SELECT COUNT(*) as total FROM card_keys")
                total = cursor.fetchone()['total']
                self.stats_labels['总数'].setText(f"总数: {total}")
                
                cursor.execute("SELECT COUNT(*) as used FROM card_keys WHERE status = 1")
                used = cursor.fetchone()['used']
                self.stats_labels['已用'].setText(f"已用: {used}")
                
                self.stats_labels['未用'].setText(f"未用: {total - used}")
                
                cursor.execute("""
                    SELECT COUNT(*) as expired FROM card_keys 
                    WHERE status = 1 AND use_time + INTERVAL valid_days DAY < NOW()
                """)
                expired = cursor.fetchone()['expired']
                self.stats_labels['已过期'].setText(f"已过期: {expired}")

                # 获取卡密列表
                cursor.execute("""
                    SELECT card_key, valid_days, create_time, status, use_time,
                           CASE 
                               WHEN status = 1 AND use_time IS NOT NULL THEN
                                   GREATEST(0, DATEDIFF(use_time + INTERVAL valid_days DAY, NOW()))
                               ELSE valid_days
                           END as remaining_days,
                           device_id, bind_time
                    FROM card_keys 
                    ORDER BY create_time DESC
                """)
                cards = cursor.fetchall()

                self.table.setRowCount(len(cards))
                for row, card in enumerate(cards):
                    # 卡密
                    self.table.setItem(row, 0, QTableWidgetItem(card['card_key']))
                    # 有效期
                    self.table.setItem(row, 1, QTableWidgetItem(str(card['valid_days'])))
                    # 创建时间
                    self.table.setItem(row, 2, QTableWidgetItem(str(card['create_time'])))
                    # 状态
                    status = '已过期' if card['remaining_days'] == 0 and card['status'] == 1 else \
                            '已使用' if card['status'] == 1 else '未使用'
                    self.table.setItem(row, 3, QTableWidgetItem(status))
                    # 使用时间
                    use_time = str(card['use_time']) if card['use_time'] else '-'
                    self.table.setItem(row, 4, QTableWidgetItem(use_time))
                    # 剩余天数
                    self.table.setItem(row, 5, QTableWidgetItem(str(card['remaining_days'])))
                    
                    # 机器码
                    device_id = card['device_id'] if card['device_id'] else '-'
                    self.table.setItem(row, 6, QTableWidgetItem(device_id))
                    
                    # 绑定时间
                    bind_time = str(card['bind_time']) if card['bind_time'] else '-'
                    self.table.setItem(row, 7, QTableWidgetItem(bind_time))
                    
                    # 修改操作按钮组部分
                    btn_widget = QWidget()
                    btn_layout = QHBoxLayout(btn_widget)
                    btn_layout.setContentsMargins(1, 1, 1, 1)  # 减小边距
                    btn_layout.setSpacing(2)  # 减小按钮间距
                    
                    # 编辑按钮
                    edit_btn = QPushButton('编辑')
                    edit_btn.setFixedSize(42, 22)  # 减小按钮大小
                    edit_btn.clicked.connect(self.create_button_handler(self.edit_card_dialog, card['card_key']))
                    btn_layout.addWidget(edit_btn)
                    
                    # 删除按钮
                    del_btn = QPushButton('删除')
                    del_btn.setFixedSize(42, 22)  # 减小按钮大小
                    del_btn.clicked.connect(self.create_button_handler(self.delete_card, card['card_key']))
                    btn_layout.addWidget(del_btn)
                    
                    # 解绑按钮
                    if card['device_id']:
                        unbind_btn = QPushButton('解绑')
                        unbind_btn.setFixedSize(42, 22)  # 减小按钮大小
                        unbind_btn.clicked.connect(self.create_button_handler(self.unbind_device, card['card_key']))
                        btn_layout.addWidget(unbind_btn)
                    
                    # 设置按钮样式
                    btn_style = """
                        QPushButton {
                            background-color: #f8f8f8;
                            border: 1px solid #dcdfe6;
                            color: #606266;
                            padding: 0px;
                            font-size: 12px;
                            border-radius: 2px;
                            min-width: 42px;
                            max-width: 42px;
                            height: 22px;
                            margin: 0px;
                        }
                        QPushButton:hover {
                            color: #409eff;
                            border-color: #c6e2ff;
                            background-color: #ecf5ff;
                        }
                        QPushButton[text="编辑"] {
                            color: #409eff;
                            border-color: #b3d8ff;
                        }
                        QPushButton[text="编辑"]:hover {
                            background-color: #ecf5ff;
                            color: #409eff;
                        }
                        QPushButton[text="删除"] {
                            color: #f56c6c;
                            border-color: #fbc4c4;
                        }
                        QPushButton[text="删除"]:hover {
                            background-color: #fef0f0;
                            color: #f56c6c;
                        }
                        QPushButton[text="解绑"] {
                            color: #e6a23c;
                            border-color: #f5dab1;
                        }
                        QPushButton[text="解绑"]:hover {
                            background-color: #fdf6ec;
                            color: #e6a23c;
                        }
                    """
                    
                    for btn in btn_widget.findChildren(QPushButton):
                        btn.setStyleSheet(btn_style)
                    
                    self.table.setCellWidget(row, 8, btn_widget)

        except Exception as e:
            print(f"更新数据库显示失败: {str(e)}")
            QMessageBox.critical(self, '错误', f'更新数据库显示失败: {str(e)}')
        
        finally:
            if connection:
                self.auth.db.close()

    def filter_table(self):
        """筛选表格内容"""
        search_text = self.search_input.text().lower()
        status_filter = self.status_filter.currentText()
        
        for row in range(self.table.rowCount()):
            card_key = self.table.item(row, 0).text().lower()
            status = self.table.item(row, 3).text()
            
            # 检查是否匹配搜索条件
            matches_search = search_text in card_key
            matches_status = status_filter == '全部' or status == status_filter
            
            self.table.setRowHidden(row, not (matches_search and matches_status))

    def export_cards(self):
        """导出卡密"""
        try:
            file_path, _ = QFileDialog.getSaveFileName(
                self, "导出卡密", "", "CSV Files (*.csv);;All Files (*)"
            )
            
            if not file_path:
                return
                
            with open(file_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    '卡密', '有效期', '创建时间', '状态', '使用时间', 
                    '剩余天数', '机器码', '绑定时间'
                ])
                
                for row in range(self.table.rowCount()):
                    if not self.table.isRowHidden(row):
                        row_data = []
                        for col in range(8):  # 不包括操作列
                            item = self.table.item(row, col)
                            row_data.append(item.text() if item else '')
                        writer.writerow(row_data)
                        
            QMessageBox.information(self, '成功', '卡密导出成功')
            
        except Exception as e:
            QMessageBox.critical(self, '错误', f'导出卡密失败: {str(e)}')

    def generate_cards(self):
        """生成卡密"""
        try:
            days = int(self.days_input.text())
            count = int(self.count_input.text())
            
            if days <= 0 or count <= 0:
                QMessageBox.warning(self, '错误', '有效期和数量必须大于0')
                return
                
            cards = self.auth.generate_cards(days, count)
            if cards:
                QMessageBox.information(self, '成功', f'成功生成{len(cards)}个卡密')
                self.update_database()
            else:
                QMessageBox.warning(self, '错误', '生成卡密失败')
                
        except ValueError:
            QMessageBox.warning(self, '错误', '请输入有效的数字')
        except Exception as e:
            QMessageBox.critical(self, '错误', f'生成卡密失败: {str(e)}')

    def delete_card(self, card_key):
        """删除卡密"""
        try:
            reply = QMessageBox.question(self, '确认', 
                                       f'确定要删除卡密 {card_key} 吗？',
                                       QMessageBox.Yes | QMessageBox.No)
            
            if reply == QMessageBox.Yes:
                success, message = self.auth.delete_card(card_key)
                if success:
                    QMessageBox.information(self, '成功', message)
                    self.update_database()
                else:
                    QMessageBox.warning(self, '错误', message)
                    
        except Exception as e:
            QMessageBox.critical(self, '错误', f'删除卡密失败: {str(e)}')

    def unbind_device(self, card_key):
        """解绑机器码"""
        try:
            reply = QMessageBox.question(
                self, '确认', 
                f'确定要解绑卡密 {card_key} 的机器码吗？\n解绑后不会重置卡密状态和时间。',
                QMessageBox.Yes | QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                connection = self.auth.get_connection()
                if not connection:
                    QMessageBox.warning(self, '错误', '数据库连接失败')
                    return

                with connection.cursor() as cursor:
                    cursor.execute("""
                        UPDATE card_keys 
                        SET device_id = NULL, bind_time = NULL 
                        WHERE card_key = %s
                    """, (card_key,))
                    connection.commit()
                    
                    if cursor.rowcount > 0:
                        QMessageBox.information(self, '成功', '机器码解绑成功')
                        self.update_database()
                    else:
                        QMessageBox.warning(self, '错误', '卡密不存在')
                        
        except Exception as e:
            print(f"解绑机器码失败: {str(e)}")
            QMessageBox.critical(self, '错误', f'解绑机器码失败: {str(e)}')

    def refresh_data(self):
        """刷新数据"""
        try:
            # 保存当前的搜索和筛选条件
            search_text = self.search_input.text()
            status_filter = self.status_filter.currentText()
            
            # 设置鼠标等待状态
            QApplication.setOverrideCursor(Qt.WaitCursor)
            
            try:
                # 确保数据库连接已关闭
                self.auth.db.close()
                
                # 更新数据
                self.update_database()
                
                # 恢复搜索和筛选条件
                self.search_input.setText(search_text)
                self.status_filter.setCurrentText(status_filter)
                
                # 应用筛选
                self.filter_table()
                
                QMessageBox.information(self, '成功', '数据刷新成功')
                
            except Exception as e:
                print(f"刷新数据失败: {str(e)}")
                QMessageBox.critical(self, '错误', f'刷新数据失败: {str(e)}')
                
            finally:
                # 恢复鼠标状态
                QApplication.restoreOverrideCursor()
                
        except Exception as e:
            print(f"刷新操作失败: {str(e)}")
            QMessageBox.critical(self, '错误', f'刷新操作失败: {str(e)}')

    def edit_card_dialog(self, card_key):
        """编辑卡密对话框"""
        try:
            # 获取卡密信息
            connection = self.auth.db.connect()
            if not connection:
                QMessageBox.warning(self, '错误', '数据库连接失败')
                return
            
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT valid_days, status, device_id, use_time,
                           CASE 
                               WHEN status = 1 AND use_time IS NOT NULL THEN
                                   GREATEST(0, DATEDIFF(use_time + INTERVAL valid_days DAY, NOW()))
                               ELSE valid_days
                           END as remaining_days
                    FROM card_keys WHERE card_key = %s
                """, (card_key,))
                card_info = cursor.fetchone()
            
            if not card_info:
                QMessageBox.warning(self, '错误', '卡密不存在')
                return
            
            # 建对话框
            dialog = QDialog(self)
            dialog.setWindowTitle(f'编辑卡密 - {card_key}')
            dialog.setFixedWidth(400)
            dialog.setStyleSheet("""
                QDialog {
                    background-color: #1a1a1a;
                }
                QLabel {
                    color: #cccccc;
                }
                QLineEdit, QComboBox {
                    background-color: #2d2d2d;
                    border: 1px solid #3d3d3d;
                    color: #cccccc;
                    padding: 5px;
                }
                QPushButton {
                    background-color: #2d2d2d;
                    border: 1px solid #3d3d3d;
                    color: #cccccc;
                    padding: 5px;
                    min-width: 80px;
                }
                QPushButton:hover {
                    background-color: #3d3d3d;
                }
                QGroupBox {
                    border: 1px solid #3d3d3d;
                    margin-top: 10px;
                    color: #cccccc;
                }
            """)
            
            layout = QVBoxLayout(dialog)
            
            # 信息显示组
            info_group = QGroupBox("当前信息")
            info_layout = QGridLayout()
            
            info_items = [
                ('卡密:', card_key),
                ('状态:', '已使用' if card_info['status'] == 1 else '未使用'),
                ('有效期:', f"{card_info['valid_days']}天"),
                ('剩余天数:', f"{card_info['remaining_days']}天"),
                ('使用时间:', str(card_info['use_time']) if card_info['use_time'] else '-'),
                ('机器码:', card_info['device_id'] if card_info['device_id'] else '-')
            ]
            
            for row, (label, value) in enumerate(info_items):
                info_layout.addWidget(QLabel(label), row, 0)
                info_layout.addWidget(QLabel(value), row, 1)
            
            info_group.setLayout(info_layout)
            layout.addWidget(info_group)
            
            # 编辑选项组
            edit_group = QGroupBox("编辑选项")
            edit_layout = QGridLayout()
            
            # 有效期时间选择
            edit_layout.addWidget(QLabel('开始时间:'), 0, 0)
            start_time = QDateTimeEdit()
            start_time.setDateTime(QDateTime.currentDateTime())
            start_time.setCalendarPopup(True)
            start_time.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
            edit_layout.addWidget(start_time, 0, 1)
            
            edit_layout.addWidget(QLabel('结束时间:'), 1, 0)
            end_time = QDateTimeEdit()
            end_time.setDateTime(QDateTime.currentDateTime().addDays(card_info['valid_days']))
            end_time.setCalendarPopup(True)
            end_time.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
            edit_layout.addWidget(end_time, 1, 1)
            
            # 设置时间选择器样式
            time_style = """
                QDateTimeEdit {
                    background-color: #2d2d2d;
                    border: 1px solid #3d3d3d;
                    color: #cccccc;
                    padding: 5px;
                }
                QDateTimeEdit::drop-down {
                    border: 0px;
                    background: #3d3d3d;
                }
                QDateTimeEdit::down-arrow {
                    image: none;
                    width: 12px;
                    height: 12px;
                    background: #ffff00;
                }
            """
            start_time.setStyleSheet(time_style)
            end_time.setStyleSheet(time_style)
            
            # 状态选择
            edit_layout.addWidget(QLabel('修改状态:'), 2, 0)
            status_combo = QComboBox()
            status_combo.addItems(['不修改', '未使用', '已使用'])
            edit_layout.addWidget(status_combo, 2, 1)
            
            edit_group.setLayout(edit_layout)
            layout.addWidget(edit_group)
            
            # 按钮组
            btn_layout = QHBoxLayout()
            save_btn = QPushButton('保存')
            save_btn.setStyleSheet("background-color: #2d4d2d;")
            cancel_btn = QPushButton('取消')
            btn_layout.addWidget(save_btn)
            btn_layout.addWidget(cancel_btn)
            layout.addLayout(btn_layout)
            
            # 绑定事件
            save_btn.clicked.connect(lambda: self.save_card_edit(
                dialog, card_key, start_time, end_time, status_combo
            ))
            cancel_btn.clicked.connect(dialog.reject)
            
            # 显示对话框
            dialog.exec_()
            
        except Exception as e:
            QMessageBox.critical(self, '错误', f'打开编辑对话框失败: {str(e)}')
        finally:
            if connection:
                self.auth.db.close()

    def save_card_edit(self, dialog, card_key, start_time, end_time, status_combo):
        """保存卡密编辑"""
        try:
            # 获取开始和结束时间
            start_datetime = start_time.dateTime().toPyDateTime()
            end_datetime = end_time.dateTime().toPyDateTime()
            
            # 计算有效期（秒）
            valid_seconds = int((end_datetime - start_datetime).total_seconds())
            if valid_seconds <= 0:
                QMessageBox.warning(dialog, '错误', '结束时间必须大于开始时间')
                return
            
            # 转换为天数（向上取整）
            valid_days = (valid_seconds + 86399) // 86400  # 86400 = 24 * 60 * 60
            
            status = None
            if status_combo.currentText() != '不修改':
                status = 1 if status_combo.currentText() == '已使用' else 0
            
            # 更新卡密
            success, message = self.auth.edit_card(
                card_key, 
                valid_days=valid_days,
                status=status,
                use_time=start_datetime.strftime('%Y-%m-%d %H:%M:%S')
            )
            
            if success:
                QMessageBox.information(self, '成功', message)
                self.update_database()
                dialog.accept()
            else:
                QMessageBox.warning(dialog, '错误', message)
                
        except Exception as e:
            QMessageBox.critical(self, '错误', f'保存编辑失败: {str(e)}')

    def edit_selected_card(self):
        """编辑选中的卡密"""
        selected_items = self.table.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, '提示', '请先选择要编辑的卡密')
            return
        card_key = self.table.item(selected_items[0].row(), 0).text()
        self.edit_card_dialog(card_key)

    def delete_selected_card(self):
        """删除选中的卡密"""
        selected_items = self.table.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, '提示', '请先选择要删除的卡密')
            return
        card_key = self.table.item(selected_items[0].row(), 0).text()
        self.delete_card(card_key)

    def unbind_selected_card(self):
        """解绑选中的卡密"""
        selected_items = self.table.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, '提示', '请先选择要解绑的卡密')
            return
        row = selected_items[0].row()
        card_key = self.table.item(row, 0).text()
        device_id = self.table.item(row, 6).text()
        if device_id == '-':
            QMessageBox.warning(self, '提示', '该卡密未绑定机器码')
            return
        self.unbind_device(card_key)

def main():
    app = QApplication(sys.argv)
    window = AdminPanel()
    window.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main() 