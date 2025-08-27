FROM python:3.10

# 設定工作目錄
RUN mkdir -p /app
WORKDIR /app/

# 環境變量設置
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Asia/Taipei
ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# 安装必要的包（包含 Chrome 和圖像處理套件）
RUN apt-get update && apt-get install -y \
    wget \
    curl \
    gnupg \
    unzip \
    iputils-ping \
    --no-install-recommends

# 安装 Google Chrome（為其他專案保留）
RUN wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | apt-key add - && \
    echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list && \
    apt-get update && \
    apt-get install -y google-chrome-stable

# 安装 ChromeDriver（為其他專案保留）
RUN CHROMEDRIVER_VERSION=`curl -sS chromedriver.storage.googleapis.com/LATEST_RELEASE` && \
    mkdir -p /opt/chromedriver-$CHROMEDRIVER_VERSION && \
    curl -sS -o /tmp/chromedriver_linux64.zip https://chromedriver.storage.googleapis.com/$CHROMEDRIVER_VERSION/chromedriver_linux64.zip && \
    unzip -qq /tmp/chromedriver_linux64.zip -d /opt/chromedriver-$CHROMEDRIVER_VERSION && \
    rm /tmp/chromedriver_linux64.zip && \
    chmod +x /opt/chromedriver-$CHROMEDRIVER_VERSION/chromedriver && \
    ln -fs /opt/chromedriver-$CHROMEDRIVER_VERSION/chromedriver /usr/local/bin/chromedriver

# 清理安裝快取
RUN rm -rf /var/lib/apt/lists/*

# 複製並安裝 Python 依賴
COPY requirements.txt /app/requirements.txt 
RUN pip3 install --upgrade pip
RUN pip3 install -r requirements.txt 

# 複製專案檔案
COPY . /app/

# 🚀 確保字型檔案被正確複製並可訪問
RUN ls -la /app/fonts/ && echo "✅ 字型檔案已複製到容器"

# 🚀 確保重要目錄存在
RUN mkdir -p /app/logs /app/app/emptyDR /app/app/emptyOBS

# 🚀 移除健康檢查，避免干擾日誌
# HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
#     CMD curl -f http://localhost:8000/docs || exit 1

# 設定啟動命令（生產環境使用）
CMD ["python", "start_server.py"]