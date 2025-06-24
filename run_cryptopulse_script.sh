#!/bin/bash

# Configuration
LOG_FILE="script_cryptopulse_output.log"
SCRIPT_NAME="main.py"
VENV_PATH="venv"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting CryptoPulse Trading Bot (Refactored Version)...${NC}"

# Activate virtual environment if it exists
if [ -d "$VENV_PATH" ]; then
    echo -e "${YELLOW}Activating virtual environment...${NC}"
    source "$VENV_PATH/bin/activate" || { echo -e "${RED}Failed to activate virtual environment${NC}"; exit 1; }
    echo -e "${GREEN}Virtual environment activated${NC}"
fi

# Check if we're in development mode
if [ "$1" == "--dev" ]; then
    echo -e "${YELLOW}Running in development mode...${NC}"
    DEV_FLAG="--dev"
else
    DEV_FLAG=""
fi

# Check if running in background mode
if [ "$1" == "--background" ] || [ "$2" == "--background" ]; then
    echo -e "${YELLOW}Running in background mode...${NC}"
    # Run in background with logging
    nohup python3 "$SCRIPT_NAME" $DEV_FLAG >> "$LOG_FILE" 2>&1 &
    disown
    echo -e "${GREEN}CryptoPulse is running in the background. Logs: $LOG_FILE${NC}"
else
    # Run in foreground with logging
    echo -e "${GREEN}Running $SCRIPT_NAME...${NC}"
    python3 "$SCRIPT_NAME" $DEV_FLAG 2>&1 | tee "$LOG_FILE"
fi

