#!/bin/bash
export LD_LIBRARY_PATH=/root/autodl-tmp/llama.cpp/build/bin:$LD_LIBRARY_PATH
exec /root/autodl-tmp/llama.cpp/build/bin/llama-server     -m /root/autodl-tmp/models/Qwen3.6-35B-A3B-Uncensored-Q4_K_M.gguf     --mmproj /root/autodl-tmp/models/mmproj-jailbreak-f16.gguf     -ngl 999     -c 131072     -n 8192     --host 127.0.0.1     --port 8080     --jinja     --alias 口袋AI     > /root/autodl-tmp/llama-server.log 2>&1
