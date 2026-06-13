# 01. RV1106 추론 결과 및 로컬 Mac 시각화 자동화

Luckfox Pico Ultra BW(Rockchip RV1106 NPU) 보드에서 생성한 객체 탐지 결과를 로컬 Mac으로 가져와 OpenCV로 시각화하는 host-side pipeline입니다.

이 프로젝트의 목적은 Edge device에서 생성된 추론 결과를 단순 콘솔 출력이나 일회성 화면 확인으로 끝내지 않고, 재사용 가능한 데이터 파일과 후처리 코드로 분리하는 것입니다. 이를 통해 headless 환경의 보드에서도 로컬 개발 환경에서 탐지 결과를 빠르게 확인하고 기록할 수 있습니다.

## Project Status

| Component | Status | Evidence |
| :--- | :--- | :--- |
| Detection result file | Completed | `detections.txt` |
| Host-side visualization | Completed | `auto_draw.py` |
| Result transfer script | Completed | `run.sh` |
| Rendered output image | Completed | `result.jpg` |
| Target-side C++ inference source | Not included in this folder | 보드 측 SDK 수정 내용은 별도 보강 필요 |

## Repository Structure

```text
01_image_inference_mac/
├── README.md
├── auto_draw.py
├── run.sh
├── detections.txt
├── coco_80_labels_list.txt
├── bus.jpg
└── result.jpg
```

## Pipeline Overview

```text
RV1106 board
  └── YOLOv5 / RKNN inference
        └── detections.txt 생성
              └── scp로 Mac에 전송
                    └── auto_draw.py 실행
                          └── result.jpg 생성
```

## Input and Output

| File | Role |
| :--- | :--- |
| `bus.jpg` | 객체 탐지 결과를 시각화할 원본 이미지 |
| `detections.txt` | 보드에서 생성한 객체 탐지 결과 좌표 데이터 |
| `auto_draw.py` | 탐지 결과를 읽어 bounding box를 그리는 Python script |
| `run.sh` | 보드에서 `detections.txt`를 가져오고 시각화 script를 실행하는 자동화 script |
| `result.jpg` | bounding box와 label이 렌더링된 최종 이미지 |

## Detection Result Format

`detections.txt`는 한 줄에 하나의 detected object를 저장합니다.

```text
[label] [x1] [y1] [x2] [y2] [confidence]
```

예시는 다음과 같습니다.

```text
person 208 244 286 506 0.884140
person 479 238 560 526 0.863770
person 110 236 230 535 0.832502
bus 94 130 553 464 0.697392
person 79 354 122 516 0.349309
```

각 필드의 의미는 다음과 같습니다.

| Field | Description |
| :--- | :--- |
| `label` | 감지된 객체 class 이름 |
| `x1`, `y1` | bounding box의 left-top 좌표 |
| `x2`, `y2` | bounding box의 right-bottom 좌표 |
| `confidence` | 모델의 confidence score |

## How to Run

### 1. 보드에서 결과 파일 가져오기

`run.sh`는 보드 내부의 `detections.txt`를 로컬 폴더로 복사한 뒤, Python 시각화 script를 실행합니다.

```bash
bash run.sh
```

현재 `run.sh`에는 보드 IP가 마스킹되어 있으므로, 실제 실행 전에는 자신의 네트워크 환경에 맞게 보드 IP를 설정해야 합니다.

```bash
scp pico@<BOARD_IP>:/home/pico/yolo_test/detections.txt ./
```

### 2. 로컬 파일만으로 시각화 실행하기

이미 `detections.txt`와 `bus.jpg`가 로컬에 있다면, Python script만 직접 실행할 수 있습니다.

```bash
python3 auto_draw.py
```

실행 후 `result.jpg`가 생성됩니다.

## Implementation Details

### 1. Result Parsing

`auto_draw.py`는 `detections.txt`를 line-by-line으로 읽고, 각 줄을 공백 기준으로 분리합니다.

```python
label, x1, y1, x2, y2, score = data[0], int(data[1]), int(data[2]), int(data[3]), int(data[4]), float(data[5])
```

이를 통해 class label, bounding box 좌표, confidence score를 구조화된 값으로 복원합니다.

### 2. OpenCV Rendering

파싱한 좌표를 기반으로 원본 이미지 위에 bounding box와 label을 그립니다.

```python
cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 2)
cv2.putText(img, f"{label} {score:.2f}", (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
```

렌더링이 끝나면 결과 이미지를 `result.jpg`로 저장합니다.

```python
cv2.imwrite('result.jpg', img)
```

## Result

최종 결과는 `result.jpg`로 저장됩니다.

![result](./result.jpg)

이 이미지는 RV1106 보드에서 생성한 detection result를 로컬 Mac 환경에서 다시 시각화한 결과입니다. 이를 통해 보드가 headless 상태이더라도 추론 결과를 로컬에서 빠르게 확인할 수 있습니다.

## What This Project Demonstrates

이 프로젝트는 단순히 YOLO 결과 이미지를 보여주는 것이 아니라, Edge device와 host PC 사이의 데이터 흐름을 분리해 재현 가능한 pipeline으로 구성한 점에 의미가 있습니다.

주요 역량은 다음과 같습니다.

- Edge device에서 생성된 AI inference result의 구조화
- 보드와 host PC 사이의 SCP 기반 데이터 전송
- 텍스트 기반 detection result parsing
- OpenCV를 활용한 bounding box visualization
- Headless embedded board 개발을 위한 host-side debugging workflow 구성

## Current Limitations

현재 이 폴더에는 target board에서 실행한 C++ 추론 코드 원본이나 RKNN 변환 과정이 포함되어 있지 않습니다. 따라서 이 README에서는 보드 측 전체 inference implementation을 완성된 형태로 설명하기보다, 공개 레포에서 확인 가능한 host-side visualization pipeline을 중심으로 설명합니다.

## Next Improvements

- 보드 측 C++ inference result 저장 코드 추가
- PyTorch -> ONNX -> RKNN 변환 과정 문서화
- RKNN model file 생성 로그 및 설정 추가
- 실제 보드 실행 명령 정리
- 여러 입력 이미지에 대한 batch visualization 지원
- confidence threshold 조정 옵션 추가
- 결과 파일 format을 JSON 또는 CSV로 확장 검토
