import os
import shutil

# 打包后的目录
dist_dir = 'dist/卡密系统'

# 需要删除的不必要文件
unnecessary_files = [
    '_asyncio.pyd',
    '_bz2.pyd',
    '_decimal.pyd',
    '_hashlib.pyd',
    '_lzma.pyd',
    '_queue.pyd',
    '_ssl.pyd',
    'unicodedata.pyd',
    'VCRUNTIME140.dll',
    'python3.dll',
    'select.pyd',
]

# 删除不必要的文件
for file in unnecessary_files:
    file_path = os.path.join(dist_dir, file)
    if os.path.exists(file_path):
        os.remove(file_path)

# 删除不必要的目录
unnecessary_dirs = [
    'PyQt5/Qt5/translations',
    'PyQt5/Qt5/resources',
]

for dir_path in unnecessary_dirs:
    full_path = os.path.join(dist_dir, dir_path)
    if os.path.exists(full_path):
        shutil.rmtree(full_path)

# 删除或替换数据库连接信息
DB_CONFIG = {
    'host': '',
    'user': '',
    'password': '',
    'database': '',
    'port': ''
}

print('优化完成') 