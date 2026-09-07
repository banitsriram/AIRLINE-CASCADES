#!/bin/bash
cd "$(dirname "$0")/.."
source .env
export FLASK_APP=app.py
python3 app.py
