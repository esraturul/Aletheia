#!/bin/bash
# Aletheia Local Runner Script


# Colors for logging
GREEN='\033[0;32m'
CYAN='\033[0;36m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${CYAN}====================================================${NC}"
echo -e "${GREEN}       ALETHEIA TRUTH ENGINE - LOCAL RUNNER         ${NC}"
echo -e "${CYAN}====================================================${NC}"

# Set Python Path
export PYTHONPATH=$PYTHONPATH:$(pwd)

# Activate Virtual Environment if exists
if [ -d "venv" ]; then
    echo -e "${GREEN}[Sistem] Sanal ortam (venv) aktif ediliyor...${NC}"
    source venv/bin/activate
fi

# Load .env file if it exists
if [ -f ".env" ]; then
    echo -e "${GREEN}[Sistem] .env dosyası yükleniyor...${NC}"
    set -a
    source .env
    set +a
fi

# Function to clean up background processes on exit
cleanup() {
    echo -e "\n${RED}[Sistem] Kapatma sinyali alındı. Sunucular sonlandırılıyor...${NC}"
    kill $BACKEND_PID $FRONTEND_PID 2>/dev/null
    exit 0
}

# Register the cleanup function for Ctrl+C (SIGINT) and SIGTERM
trap cleanup SIGINT SIGTERM

# 1. Start FastAPI Backend
echo -e "${GREEN}[1/2] FastAPI Backend Başlatılıyor (Port 8999)...${NC}"
python3 -u -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8999 > backend.log 2>&1 &
BACKEND_PID=$!

# Wait a second to check if it crashed immediately
sleep 2
if ! kill -0 $BACKEND_PID 2>/dev/null; then
    echo -e "${RED}[Hata] Backend başlatılamadı! Lütfen backend.log dosyasını inceleyin.${NC}"
    exit 1
fi
echo -e "${GREEN}[OK] Backend PID: $BACKEND_PID. Loglar 'backend.log' dosyasına yazılıyor.${NC}"

# 2. Start Streamlit Frontend
echo -e "${GREEN}[2/2] Streamlit UI Başlatılıyor (Port 8555)...${NC}"
streamlit run frontend/Verification_Hub.py --server.port 8555 > frontend.log 2>&1 &
FRONTEND_PID=$!

sleep 2
if ! kill -0 $FRONTEND_PID 2>/dev/null; then
    echo -e "${RED}[Hata] Frontend başlatılamadı! Lütfen frontend.log dosyasını inceleyin.${NC}"
    kill $BACKEND_PID 2>/dev/null
    exit 1
fi
echo -e "${GREEN}[OK] Frontend PID: $FRONTEND_PID. Loglar 'frontend.log' dosyasına yazılıyor.${NC}"

echo -e "${CYAN}----------------------------------------------------${NC}"
echo -e "${GREEN}Aletheia başarıyla başlatıldı!${NC}"
echo -e "${CYAN}Arayüze erişmek için: http://localhost:8555${NC}"
echo -e "${CYAN}----------------------------------------------------${NC}"

# Keep script running to monitor processes
while kill -0 $BACKEND_PID 2>/dev/null && kill -0 $FRONTEND_PID 2>/dev/null; do
    sleep 1
done

echo -e "${RED}[Uyarı] Sunuculardan biri durdu. Kapatılıyor...${NC}"
cleanup
