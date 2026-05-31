#!/bin/bash
# ==========================================
#  5090 Full Stack — One-Click Startup
#  Run after GPU mode is restored
#  Usage: ssh -p 37169 root@connect.westd.seetacloud.com
#         bash /root/autodl-tmp/start-all.sh
# ==========================================
set -e
export PATH="/root/miniconda3/bin:$PATH"
cd /root/autodl-tmp

LOG="/root/autodl-tmp/startup-$(date +%m%d-%H%M).log"
exec > >(tee -a $LOG) 2>&1

echo "========================================="
echo "$(date): 5090 FULL STACK START"
echo "========================================="

# Check GPU
HAS_GPU=false
if nvidia-smi > /dev/null 2>&1; then
    HAS_GPU=true
    echo "GPU: AVAILABLE"
else
    echo "GPU: NOT AVAILABLE (no-GPU mode — skipping llama-server)"
fi

# ==========================================
# Step 1: llama-server (GPU Inference)
# ==========================================
echo ""
echo "[1/3] Starting llama-server..."

if [ "$HAS_GPU" = true ]; then
    if curl -s --max-time 3 http://127.0.0.1:8080/health 2>/dev/null | grep -q ok; then
        echo "  llama-server already running"
    else
        pkill -f llama-server 2>/dev/null || true
        sleep 2

        MODEL=/root/autodl-tmp/models/Qwen3.6-35B-A3B-Uncensored-Q4_K_M.gguf
        if [ ! -f "$MODEL" ]; then
            echo "  ERROR: Model not found at $MODEL"
            echo "  Run: bash /root/autodl-tmp/deploy-5090-new.sh first"
            exit 1
        fi

        export LD_LIBRARY_PATH=/root/autodl-tmp/llama.cpp/build/bin:$LD_LIBRARY_PATH

        nohup /root/autodl-tmp/llama.cpp/build/bin/llama-server \
            -m "$MODEL" \
            -ngl 999 \
            -c 131072 \
            -n 8192 \
            --host 127.0.0.1 \
            --port 8080 \
            --alias "口袋AI" --mmproj /root/autodl-tmp/models/mmproj-jailbreak-f16.gguf --jinja \
            > /root/autodl-tmp/llama-server.log 2>&1 &

        echo "  llama-server PID: $!"

        echo "  Loading model into GPU..."
        for i in $(seq 1 60); do
            sleep 3
            if curl -s --max-time 2 http://127.0.0.1:8080/health 2>/dev/null | grep -q ok; then
                echo "  llama-server READY (${i}x3s)"
                break
            fi
            [ $((i % 10)) -eq 0 ] && echo "  ... still loading ($i)"
        done

        VRAM=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader 2>/dev/null || echo "N/A")
        echo "  GPU VRAM: $VRAM"
    fi
else
    echo "  [SKIP] No GPU — llama-server requires GPU"
fi

# ==========================================
# Step 2: Open WebUI (Commercial Chat UI)
# ==========================================
echo ""
echo "[2/3] Starting Open WebUI on port 6006..."

if curl -s --max-time 3 http://127.0.0.1:6006/ 2>/dev/null | grep -q "html\|WebUI\|Qwen"; then
    echo "  Open WebUI already running"
else
    fuser -k 6006/tcp 2>/dev/null || true
    sleep 1

    setsid bash /root/autodl-tmp/start-openwebui.sh \
        > /root/autodl-tmp/openwebui.log 2>&1 &
    echo "  Open WebUI PID: $!"

    echo "  Initializing (first start downloads assets)..."
    for i in $(seq 1 40); do
        sleep 3
        HTTP=$(curl -s --max-time 5 -o /dev/null -w "%{http_code}" http://127.0.0.1:6006/ 2>/dev/null)
        if [ "$HTTP" = "200" ]; then
            echo "  Open WebUI READY on port 6006 (${i}x3s)"
            break
        fi
        [ $((i % 10)) -eq 0 ] && echo "  ... still initializing ($i)"
    done
fi

# ==========================================
# Step 3: server-5090.py (API Bridge)
# ==========================================
echo ""
echo "[3/3] Starting server-5090 on port 6008..."

if curl -s --max-time 3 http://127.0.0.1:6008/health 2>/dev/null | grep -q ok; then
    echo "  server-5090 already running"
else
    fuser -k 6008/tcp 2>/dev/null || true
    sleep 1

    setsid bash /root/autodl-tmp/start-server.sh \
        > /root/autodl-tmp/server-5090.log 2>&1 &
    echo "  server-5090 PID: $!"

    sleep 4
    if curl -s --max-time 3 http://127.0.0.1:6008/health 2>/dev/null | grep -q ok; then
        echo "  server-5090 READY on port 6008"
    else
        echo "  WARNING: server-5090 may have failed"
    fi
fi

# ==========================================
# Done
# ==========================================
echo ""
echo "========================================="
echo "$(date): ALL SERVICES STARTED"
echo "========================================="
echo ""
echo "  llama-server : http://127.0.0.1:8080 (GPU)"
echo "  Open WebUI   : http://36.103.198.249:6006 (Chat UI)"
echo "  API Bridge   : http://36.103.198.249:6008 (OpenAI API)"
echo ""
echo "  GPU: $(nvidia-smi --query-gpu=memory.used --format=csv,noheader 2>/dev/null || echo 'check nvidia-smi')"
echo "  Log: $LOG"
