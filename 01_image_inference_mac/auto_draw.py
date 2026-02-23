import cv2
import os

print("1. 파이썬 스크립트 시작됨")

# 파일 체크
if not os.path.exists('bus.jpg'):
    print("❌ 에러: bus.jpg가 없습니다.")
    exit()
if not os.path.exists('detections.txt'):
    print("❌ 에러: detections.txt가 없습니다.")
    exit()

print("2. 이미지 로드 중...")
img = cv2.imread('bus.jpg')
if img is None:
    print("❌ 에러: 이미지를 읽을 수 없습니다.")
    exit()

print("3. 좌표 데이터 읽는 중...")
with open('detections.txt', 'r') as f:
    lines = f.readlines()

print(f"4. 그리기 시작 (객체 수: {len(lines)})")
for line in lines:
    data = line.strip().split()
    if len(data) < 6: continue
    label, x1, y1, x2, y2, score = data[0], int(data[1]), int(data[2]), int(data[3]), int(data[4]), float(data[5])
    cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 2)
    print(f"   - {label} 그렸음: ({x1}, {y1})")

print("5. 파일로 저장 중...")
cv2.imwrite('result.jpg', img)

if os.path.exists('result.jpg'):
    print("✅ 성공: result.jpg가 생성되었습니다!")
else:
    print("❌ 에러: 파일 저장 실패")

# Mac에서 창 띄우기 시도
try:
    print("6. 화면에 창 띄우는 중 (아무 키나 누르면 종료)")
    cv2.imshow('Luckfox', img)
    cv2.waitKey(0)
    cv2.destroyAllWindows()
except Exception as e:
    print(f"ℹ️ 참고: 창 띄우기 실패 (사유: {e})")
