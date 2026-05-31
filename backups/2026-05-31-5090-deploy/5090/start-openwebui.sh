#!/bin/bash
export PATH="/root/miniconda3/bin:$PATH"
cd /root/autodl-tmp

export HF_ENDPOINT="https://hf-mirror.com"
export HF_HUB_ENABLE_HF_TRANSFER=0
export DATA_DIR="/root/autodl-tmp/open-webui/data"
export WEBUI_NAME="口袋AI"
export WEBUI_URL="https://koudai.cool"
export CORS_ALLOW_ORIGIN="https://koudai.cool"
export OPENAI_API_BASE_URL="http://127.0.0.1:8080/v1"
export OPENAI_API_KEY="sk-no-auth-needed"
export AIOHTTP_CLIENT_TIMEOUT=600
export RAG_EMBEDDING_ENGINE=""
export AUDIO_STT_ENGINE=""
export AUDIO_TTS_ENGINE=""
export IMAGE_GENERATION_ENGINE=""
export ENABLE_IMAGE_GENERATION="false"
export ENABLE_SIGNUP="true"
export DEFAULT_USER_ROLE="user"
export WEBUI_AUTH="true"

source /root/autodl-tmp/open-webui/venv/bin/activate
open-webui serve --host 0.0.0.0 --port 6006

