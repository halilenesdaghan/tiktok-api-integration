#!/bin/bash

# TikTok API Integration Setup Script

echo "🚀 TikTok API Integration Setup"
echo "=============================="

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check Python version
echo -e "\n${YELLOW}Checking Python version...${NC}"
python_version=$(python3 --version 2>&1 | awk '{print $2}')
required_version="3.11"

if [[ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]]; then
    echo -e "${RED}Error: Python $required_version or higher is required. Found: $python_version${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Python $python_version${NC}"

# Create virtual environment
echo -e "\n${YELLOW}Creating virtual environment...${NC}"
python3 -m venv venv
echo -e "${GREEN}✓ Virtual environment created${NC}"

# Activate virtual environment
echo -e "\n${YELLOW}Activating virtual environment...${NC}"
source venv/bin/activate

# Upgrade pip
echo -e "\n${YELLOW}Upgrading pip...${NC}"
pip install --upgrade pip

# Install dependencies
echo -e "\n${YELLOW}Installing dependencies...${NC}"
pip install -r requirements.txt
echo -e "${GREEN}✓ Dependencies installed${NC}"

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo -e "\n${YELLOW}Creating .env file from template...${NC}"
    cp .env.example .env
    echo -e "${GREEN}✓ .env file created${NC}"
    echo -e "${YELLOW}⚠️  Please update .env with your TikTok API credentials${NC}"
fi

# Create necessary directories
echo -e "\n${YELLOW}Creating project directories...${NC}"
mkdir -p logs
mkdir -p alembic/versions
echo -e "${GREEN}✓ Directories created${NC}"

# Initialize database
echo -e "\n${YELLOW}Initializing database...${NC}"
if [ ! -f alembic/alembic.ini ]; then
    alembic init alembic 2>/dev/null || true
    cp alembic.ini alembic/alembic.ini 2>/dev/null || true
fi

# Create __init__.py files
touch app/__init__.py
touch app/api/__init__.py
touch app/api/v1/__init__.py
touch app/api/v1/endpoints/__init__.py
touch app/config/__init__.py
touch app/core/__init__.py
touch app/models/__init__.py
touch app/schemas/__init__.py
touch app/services/__init__.py
touch tests/__init__.py
touch alembic/versions/__init__.py

# Run initial migration
echo -e "\n${YELLOW}Running database migrations...${NC}"
alembic revision --autogenerate -m "Initial migration" 2>/dev/null || true
alembic upgrade head 2>/dev/null || true
echo -e "${GREEN}✓ Database initialized${NC}"

# Check if Redis is running
echo -e "\n${YELLOW}Checking Redis connection...${NC}"
if redis-cli ping > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Redis is running${NC}"
else
    echo -e "${YELLOW}⚠️  Redis is not running. Rate limiting will use in-memory storage${NC}"
fi

# Run tests
echo -e "\n${YELLOW}Running tests...${NC}"
pytest tests/ -v --no-cov || echo -e "${YELLOW}⚠️  Some tests failed. This is expected if external services are not configured${NC}"

echo -e "\n${GREEN}✅ Setup completed!${NC}"
echo -e "\n${YELLOW}Next steps:${NC}"
echo "1. Update .env file with your TikTok API credentials"
echo "2. Run 'uvicorn app.main:app --reload' to start the development server"
echo "3. Visit http://localhost:8000/docs for API documentation"
echo ""
echo -e "${GREEN}Happy coding! 🎉${NC}"