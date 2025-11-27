#!/bin/bash
# Script to run Azure Blob Storage integration tests
# This script helps set up Azurite and run the tests

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Azure Blob Storage Integration Tests${NC}"
echo "======================================"
echo ""

# Check if pytest is installed
if ! command -v pytest &> /dev/null; then
    echo -e "${RED}Error: pytest is not installed${NC}"
    echo "Install it with: pip install pytest pytest-asyncio"
    exit 1
fi

# Check if azure-storage-blob is installed
if ! python -c "import azure.storage.blob" 2>/dev/null; then
    echo -e "${RED}Error: azure-storage-blob is not installed${NC}"
    echo "Install it with: pip install azure-storage-blob"
    exit 1
fi

# Function to check if Azurite is running
check_azurite() {
    if curl -s http://localhost:10000 > /dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

# Function to start Azurite with Docker
start_azurite_docker() {
    echo -e "${YELLOW}Starting Azurite with Docker...${NC}"
    
    # Check if Docker is available
    if ! command -v docker &> /dev/null; then
        echo -e "${RED}Error: Docker is not installed${NC}"
        echo "Please install Docker or start Azurite manually"
        return 1
    fi
    
    # Check if container already exists
    if docker ps -a --format '{{.Names}}' | grep -q "^azurite-test$"; then
        echo "Removing existing Azurite container..."
        docker rm -f azurite-test > /dev/null 2>&1
    fi
    
    # Start Azurite
    docker run -d --name azurite-test \
        -p 10000:10000 \
        mcr.microsoft.com/azure-storage/azurite \
        azurite-blob --blobHost 0.0.0.0 > /dev/null 2>&1
    
    # Wait for Azurite to be ready
    echo "Waiting for Azurite to start..."
    for i in {1..30}; do
        if check_azurite; then
            echo -e "${GREEN}✓ Azurite is running${NC}"
            return 0
        fi
        sleep 1
    done
    
    echo -e "${RED}Error: Azurite failed to start${NC}"
    return 1
}

# Function to stop Azurite
stop_azurite_docker() {
    if docker ps --format '{{.Names}}' | grep -q "^azurite-test$"; then
        echo -e "${YELLOW}Stopping Azurite...${NC}"
        docker stop azurite-test > /dev/null 2>&1
        docker rm azurite-test > /dev/null 2>&1
        echo -e "${GREEN}✓ Azurite stopped${NC}"
    fi
}

# Parse command line arguments
AUTO_START=false
STOP_AFTER=false
VERBOSE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --auto-start)
            AUTO_START=true
            shift
            ;;
        --stop-after)
            STOP_AFTER=true
            shift
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --auto-start    Automatically start Azurite if not running"
            echo "  --stop-after    Stop Azurite after tests complete"
            echo "  -v, --verbose   Show detailed test output"
            echo "  -h, --help      Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0                          # Run tests (Azurite must be running)"
            echo "  $0 --auto-start             # Start Azurite and run tests"
            echo "  $0 --auto-start --stop-after # Start, test, and stop Azurite"
            echo "  $0 -v                       # Run with verbose output"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Check if Azure credentials are set
if [ -n "$AZURE_STORAGE_CONNECTION_STRING" ]; then
    echo -e "${GREEN}Using Azure credentials from environment${NC}"
    echo "Container: ${AZURE_STORAGE_CONTAINER_NAME:-test-container}"
    echo ""
else
    # Check if Azurite is running
    if check_azurite; then
        echo -e "${GREEN}✓ Azurite is running${NC}"
        echo ""
    else
        if [ "$AUTO_START" = true ]; then
            if ! start_azurite_docker; then
                echo -e "${RED}Failed to start Azurite${NC}"
                echo ""
                echo "You can start Azurite manually with:"
                echo "  docker run -p 10000:10000 mcr.microsoft.com/azure-storage/azurite azurite-blob --blobHost 0.0.0.0"
                exit 1
            fi
            echo ""
        else
            echo -e "${YELLOW}⚠ Azurite is not running${NC}"
            echo ""
            echo "Options:"
            echo "1. Run this script with --auto-start to automatically start Azurite"
            echo "2. Start Azurite manually:"
            echo "   docker run -p 10000:10000 mcr.microsoft.com/azure-storage/azurite azurite-blob --blobHost 0.0.0.0"
            echo "3. Set Azure credentials:"
            echo "   export AZURE_STORAGE_CONNECTION_STRING='your_connection_string'"
            echo ""
            exit 1
        fi
    fi
fi

# Run the tests
echo -e "${GREEN}Running integration tests...${NC}"
echo ""

PYTEST_ARGS="API/datasources/test_azure_blob_integration.py"

if [ "$VERBOSE" = true ]; then
    PYTEST_ARGS="$PYTEST_ARGS -v -s"
else
    PYTEST_ARGS="$PYTEST_ARGS -v"
fi

# Run tests and capture exit code
if pytest $PYTEST_ARGS; then
    echo ""
    echo -e "${GREEN}✓ All integration tests passed!${NC}"
    TEST_EXIT_CODE=0
else
    echo ""
    echo -e "${RED}✗ Some integration tests failed${NC}"
    TEST_EXIT_CODE=1
fi

# Stop Azurite if requested
if [ "$STOP_AFTER" = true ] && [ "$AUTO_START" = true ]; then
    echo ""
    stop_azurite_docker
fi

exit $TEST_EXIT_CODE
