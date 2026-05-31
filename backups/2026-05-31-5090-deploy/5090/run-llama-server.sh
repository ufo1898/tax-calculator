#!/bin/bash
export LD_LIBRARY_PATH=/root/autodl-tmp/llama.cpp/build/bin:$LD_LIBRARY_PATH
exec /root/autodl-tmp/llama.cpp/build/bin/llama-server "$@"
