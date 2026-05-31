#!/bin/bash
export PATH="/root/miniconda3/bin:$PATH"
cd /root/autodl-tmp
exec python3 /root/autodl-tmp/server-5090.py
