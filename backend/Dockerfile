# 後端容器：Python + FastAPI
#
# python:3.13-slim 是「精簡版」官方映像（約 150MB）。
# 不用 alpine 是因為 Python 套件常需要編譯，alpine 的 musl libc
# 會讓很多套件裝不起來或變超慢。slim 是 Python 專案的標準選擇。
FROM python:3.13-slim

WORKDIR /app

# PYTHONUNBUFFERED=1：讓 print 和 log 立刻輸出，不要卡在緩衝區。
#   不設的話，容器的 log 會延遲出現，除錯時很痛苦。
# PYTHONDONTWRITEBYTECODE=1：不要產生 .pyc 檔，容器裡不需要。
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# ⚠ 先只複製 requirements.txt，裝完套件再複製程式碼。
# 為什麼分兩步：Docker 會把每一行指令的結果快取起來。
# 只要 requirements.txt 沒變，重新 build 時「裝套件」那一層就直接用快取，
# 不用重抓幾十個套件。改程式碼只會重跑最後那一層，build 從三分鐘縮到三秒。
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# 啟動時先跑 migration 再開服務。
# 這樣隊友 clone 下來、或部署到新環境，資料表會自動建好。
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
