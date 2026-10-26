"""生成一份可直接放进数据卷的干净数据库副本。

为什么需要它：
    · 本机数据库处于 WAL 模式，直接拷 `weather.db` 会留下未合并的 WAL，
      容器里若还存在**旧的** `weather.db-wal`，SQLite 会判定文件不匹配并把库重置。
    · `VACUUM INTO` 输出的是一个自包含、无碎片、无 WAL 依赖的单文件。

用法（在仓库根目录执行）：
    .venv\\Scripts\\python.exe deploy\\vacuum_db.py
    .venv\\Scripts\\python.exe deploy\\vacuum_db.py data\\weather.db data\\weather-clean.db
"""

from __future__ import annotations

import os
import sqlite3
import sys

src = sys.argv[1] if len(sys.argv) > 1 else os.path.join("data", "weather.db")
dst = sys.argv[2] if len(sys.argv) > 2 else os.path.join("data", "weather-clean.db")

if not os.path.exists(src):
    raise SystemExit(f"源数据库不存在: {src}")
if os.path.exists(dst):
    os.remove(dst)

TABLES = ("precip_hourly", "precip_daily", "region")

con = sqlite3.connect(src)
# 先把 WAL 合并回主文件，保证源文件本身是完整的
con.execute("PRAGMA wal_checkpoint(TRUNCATE)")
con.execute(f"VACUUM INTO '{dst.replace(os.sep, '/')}'")
src_counts = {t: con.execute(f"select count(*) from {t}").fetchone()[0] for t in TABLES}
con.close()

chk = sqlite3.connect(dst)
dst_counts = {t: chk.execute(f"select count(*) from {t}").fetchone()[0] for t in TABLES}
chk.close()

print(f"source : {src}")
print(f"target : {dst}  ({os.path.getsize(dst) / 1024 / 1024:.1f} MB)")

ok = True
for t in TABLES:
    same = src_counts[t] == dst_counts[t]
    ok = ok and same
    print(f"  {t:16} src={src_counts[t]:>8}  dst={dst_counts[t]:>8}  {'OK' if same else 'MISMATCH'}")

raise SystemExit(0 if ok else 1)
