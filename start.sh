#!/bin/bash

# 文档分析系统启动脚本

echo "📄 启动文档分析系统..."

# 检查Python环境
if ! command -v python3 &> /dev/null; then
    echo "❌ 错误: 未找到Python3"
    echo "请安装Python 3.8或更高版本"
    exit 1
fi

# 检查是否在虚拟环境中
if [ -z "$VIRTUAL_ENV" ]; then
    echo "⚠️  建议在虚拟环境中运行此应用"
    echo "创建虚拟环境: python3 -m venv venv"
    echo "激活虚拟环境: source venv/bin/activate"
fi

# 创建必要的目录
echo "📁 创建必要的目录..."
mkdir -p uploads
mkdir -p logs
mkdir -p temp

# 检查依赖
echo "📦 检查依赖..."
pip install -r requirements.txt

# 检查Ollama服务（如果使用）
if command -v ollama &> /dev/null; then
    echo "🤖 检查Ollama服务..."
    if ! ollama list &> /dev/null; then
        echo "⚠️  Ollama服务未运行，正在启动..."
        ollama serve &
        sleep 5
    fi
    
    # 检查模型
    if ! ollama list | grep -q "llama3.2"; then
        echo "📥 下载llama3.2模型..."
        ollama pull llama3.2
    fi
else
    echo "ℹ️  未安装Ollama，将使用OpenAI API"
fi

# 设置环境变量
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# 启动应用
echo "🚀 启动Streamlit应用..."
streamlit run app.py --server.port 8501 --server.address 0.0.0.0

echo "✅ 启动完成！"
echo "🌐 访问地址: http://localhost:8501"
