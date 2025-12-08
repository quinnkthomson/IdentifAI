#!/bin/bash

# IdentifAI Startup Script
# This script starts both the face detection capture system and the web app

echo "🎯 Starting IdentifAI - Face Detection System"
echo "=============================================="

# Check if we're in the right directory
if [ ! -d "raspberry_pi" ] || [ ! -d "web_app" ]; then
    echo "❌ Error: Please run this script from the IdentifAI root directory"
    echo "   cd ~/IdentifAI"
    echo "   ./run_identifai.sh"
    exit 1
fi

echo ""
echo "📋 Starting services..."
echo ""

# Start web app in background
echo "🌐 Starting web app on port 5001..."
cd web_app
python3 app.py &
WEB_APP_PID=$!
cd ..

echo "📷 Starting face detection capture system..."
cd raspberry_pi
python3 capture.py &
CAPTURE_PID=$!
cd ..

echo ""
echo "✅ Both services started!"
echo ""
echo "🌐 Web Dashboard: http://localhost:5001/dashboard"
echo "📺 Live Stream:    http://localhost:5001"
echo ""
echo "📊 To stop both services:"
echo "   kill $WEB_APP_PID $CAPTURE_PID"
echo "   or press Ctrl+C in each terminal"
echo ""
echo "📝 Logs:"
echo "   Web app logs appear in terminal where you ran this script"
echo "   Capture logs are in raspberry_pi/capture.log"
echo ""

# Wait for user interrupt
trap "echo ''; echo '🛑 Stopping services...'; kill $WEB_APP_PID $CAPTURE_PID 2>/dev/null; exit" INT

echo "Press Ctrl+C to stop both services..."
wait