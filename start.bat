@echo off
echo 📄 启动文档分析系统...

REM 检查Python环境
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ 错误: 未找到Python
    echo 请安装Python 3.8或更高版本
    pause
    exit /b 1
)

REM 检查虚拟环境
if "%VIRTUAL_ENV%"=="" (
    echo ⚠️  建议在虚拟环境中运行此应用
    echo 创建虚拟环境: python -m venv venv
    echo 激活虚拟环境: venv\Scripts\activate
    echo.
)

REM 创建必要的目录
echo 📁 创建必要的目录...
if not exist "uploads" mkdir uploads
if not exist "logs" mkdir logs
if not exist "temp" mkdir temp

REM 检查依赖
echo 📦 检查依赖...
pip install -r requirements.txt
if errorlevel 1 (
    echo ❌ 依赖安装失败
    pause
    exit /b 1
)

REM 检查Ollama服务（如果使用）
where ollama >nul 2>&1
if not errorlevel 1 (
    echo 🤖 检查Ollama服务...
    ollama list >nul 2>&1
    if errorlevel 1 (
        echo ⚠️  Ollama服务未运行，正在启动...
        start /B ollama serve
        timeout /t 5 >nul
    )
    
    REM 检查模型
    ollama list | findstr "llama3.2" >nul
    if errorlevel 1 (
        echo 📥 下载llama3.2模型...
        ollama pull llama3.2
    )
) else (
    echo ℹ️  未安装Ollama，将使用OpenAI API
)

REM 设置环境变量
set PYTHONPATH=%PYTHONPATH%;%CD%

REM 启动应用
echo 🚀 启动Streamlit应用...
streamlit run app.py --server.port 8501 --server.address 0.0.0.0

echo ✅ 启动完成！
echo 🌐 访问地址: http://localhost:8501
pause
