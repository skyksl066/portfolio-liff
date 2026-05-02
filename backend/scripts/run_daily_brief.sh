#!/bin/bash
set -e
cd "$(dirname "$0")"

echo "===== $(date '+%Y-%m-%d %H:%M:%S') ====="

if [ ! -f "venv/bin/activate" ]; then
    rm -rf venv
    python3 -m venv --without-pip venv
    curl -sS https://bootstrap.pypa.io/pip/3.9/get-pip.py | venv/bin/python3
fi

source venv/bin/activate
pip install argparse requests pymysql --quiet
python3 daily_brief.py --dry-run
