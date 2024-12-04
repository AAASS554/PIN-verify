# 卡密系统 (License Key System)

[English](#english) | [中文](#中文)

## 中文

### 项目介绍
这是一个基于 PyQt5 开发的卡密管理系统，包含卡密管理和验证两个主要功能模块。

### 功能特点
- 卡密管理：生成、查询、删除卡密
- 卡密验证：验证卡密有效性
- 加密存储：使用 cryptography 确保数据安全
- 图形界面：友好的用户交互界面

### 系统要求
- Windows 7 及以上操作系统
- Python 3.7+
- PyQt5
- cryptography

### 安装说明
1. 克隆仓库
```bash
git clone https://github.com/yourusername/license-key-system.git
```

2. 安装依赖
```bash
pip install -r requirements.txt
```

3. 配置环境
- 确保已安装 Python 3.7 或更高版本
- 确保系统环境变量正确配置

### 使用说明
1. 运行卡密管理系统
```bash
python 卡密管理.py
```
- 可以生成新的卡密
- 查询现有卡密状态
- 删除过期卡密

2. 运行卡密验证系统
```bash
python 卡密验证.py
```
- 输入卡密进行验证
- 查看卡密详细信息

### 打包说明
使用 PyInstaller 进行打包：
```bash
pyinstaller -F -w -i icon.ico 卡密管理.py
pyinstaller -F -w -i icon.ico 卡密验证.py
```

### 目录结构
```
├── 卡密管理.py          # 卡密管理主程序
├── 卡密验证.py          # 卡密验证主程序
├── icon.ico            # 程序图标
├── requirements.txt    # 项目依赖
└── README.md          # 项目说明文档
```

### 常见问题
1. 如果运行时提示缺少依赖，请检查是否正确安装所有依赖包
2. 如果打包失败，请确保 PyInstaller 安装正确
3. 如果程序无法启动，请检查 Python 版本是否符合要求

### 作者
记得晚安

### 联系方式
- GitHub: [记得晚安](https://github.com/AAASS554)

### 许可证
本项目采用 Apache License 2.0 许可证

---

## English

### Project Description
This is a License Key Management System developed with PyQt5, including two main modules: key management and verification.

### Features
- Key Management: Generate, query, and delete license keys
- Key Verification: Verify key validity
- Encrypted Storage: Data security using cryptography
- GUI: User-friendly interface

### Requirements
- Windows 7 or above
- Python 3.7+
- PyQt5
- cryptography

### Installation
1. Clone repository
```bash
git clone https://github.com/yourusername/license-key-system.git
```

2. Install dependencies
```bash
pip install -r requirements.txt
```

3. Environment Setup
- Ensure Python 3.7 or higher is installed
- Verify system environment variables are properly configured

### Usage
1. Run key management program
```bash
python key_management.py
```
- Generate new license keys
- Query existing key status
- Delete expired keys

2. Run key verification program
```bash
python key_verification.py
```
- Input key for verification
- View key details

### Packaging
Package with PyInstaller:
```bash
pyinstaller -F -w -i icon.ico key_management.py
pyinstaller -F -w -i icon.ico key_verification.py
```

### Directory Structure
```
├── key_management.py   # Key management main program
├── key_verification.py # Key verification main program
├── icon.ico           # Program icon
├── requirements.txt   # Project dependencies
└── README.md         # Project documentation
```

### Troubleshooting
1. If missing dependencies, verify all required packages are installed
2. If packaging fails, ensure PyInstaller is properly installed
3. If program fails to start, check Python version compatibility

### Author
JiDeWanAn

### Contact
- GitHub: [JiDeWanAn](https://github.com/AAASS554)

### License
This project is licensed under the Apache License 2.0

### 数据库配置示例
```ini
[Database]
host = localhost
port = 3306
database = license_system
username = your_username
password = your_password
```

请将以上配置保存为 `config.ini` 并根据实际情况修改。注意不要将实际配置文件提交到版本控制系统中。
