#!/bin/bash
echo "보드에서 좌표 가져오는 중..."
scp pico@192.168.45.85:/home/pico/yolo_test/detections.txt ./

echo "결과 그리기 시작!"
python3 auto_draw.py
EOF

