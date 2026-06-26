# 02. RK-MPI 기반 무선 객체 탐지 스트리밍 시스템

Luckfox Pico Ultra BW(Rockchip RV1106 NPU) 보드에서 카메라 입력을 받아 객체 탐지를 수행하고, 보드 내부에서 bounding box를 렌더링한 뒤 RTSP로 무선 전송하는 Edge AI streaming project입니다.

이 프로젝트는 Luckfox SDK에서 제공하는 RKMPI 예제 코드를 기반으로 구동되며, 개발자는 단순 예제 실행을 넘어 **① 공식 툴킷을 활용한 AI 모델의 NPU 포맷 변환(PTQ)**, **② Docker 기반 uClibc 크로스 컴파일 환경 구축**, **③ Headless 무선 환경을 위한 L2 레벨의 네트워크 인프라 설계**를 수행하여 End-to-End 스트리밍 파이프라인을 완성하는 데 목적을 두었습니다.

## Project Status

| Component | Status | Evidence |
| :--- | :--- | :--- |
| OS & Hardware Setup | Completed | Buildroot (SC3336 Camera 지원 이미지) |
| Model Conversion | Completed | ONNX ➔ `.rknn` 변환 (공식 설정 활용) |
| Cross-Compilation | Completed | Docker `uClibc` 타겟 빌드 확인 |
| Wireless static IP setup | Completed | `scripts/S99staticip.sh` |
| On-device BBOX overlay | Completed | `main.cc` 내 OpenCV-mobile 렌더링 연동 |
| RTSP streaming | Completed | VLC Player 실시간 수신 검증 |

## Repository Structure

    02_rkmpi_wireless_streaming/
    ├── README.md
    ├── troubleshooting.md
    ├── scripts/
    │   └── S99staticip.sh
    ├── src/
    │   └── main.cc                 (RKMPI 스트리밍 & 추론 코어 코드)
    └── model/
        └── model_config.yml        (Rockchip 제공 양자화 설정 파일 활용)

## Pipeline Overview

Host(Mac/Docker)와 Edge(RV1106 보드) 환경이 명확히 분리된 파이프라인으로 동작합니다.

    [Host: Mac Local / Docker]
    PyTorch (YOLOv5) ➔ ONNX 추출 (export.py) ➔ rknn-toolkit2 양자화 ➔ yolov5.rknn
    C/C++ Source ➔ uClibc Cross-Compile ➔ luckfox_pico_rtsp_yolov5
                        │
                        ▼ (SCP Transfer)
    [Edge: RV1106 Board]
    CSI Camera ➔ RK-MPI VI (영상 캡처)
                        ▼
    RV1106 NPU ➔ Inference (yolov5.rknn)
                        ▼
    OpenCV-mobile ➔ Bounding Box Overlay
                        ▼
    RK-MPI VENC ➔ H.264 인코딩 ➔ RTSP Server
                        │
                        ▼ (Wi-Fi)
    [Client Viewer]
    VLC Player ➔ rtsp://<BOARD_STATIC_IP>:554/live/0 접속

## Key Implementation Details

### 1. Model Optimization & Conversion (PyTorch ➔ ONNX ➔ RKNN)

본 프로젝트에 사용된 YOLOv5 모델은 타겟 보드(RV1106)의 NPU 하드웨어 가속을 100% 활용하기 위해, 일반적인 PyTorch 모델(`.pt`)에서 NPU 전용 직렬화 모델(Serialized Model, IR)인 `.rknn` 포맷으로 구조 압축 및 양자화 과정을 거쳤습니다. 

이 변환 작업은 `rknn-toolkit2`가 사전 설치된 Luckfox 제공 Ubuntu Docker 이미지 환경(`luckfox-builder`)에서 수행했습니다.

#### 1.1. PyTorch ➔ ONNX 추출
YOLOv5 환경의 `export.py` 스크립트를 사용하여, Rockchip NPU 호환성을 보장하는 `--rknpu` 옵션과 함께 ONNX 모델로 추출합니다.

    python export.py --rknpu --weights yolov5s.pt

#### 1.2. ONNX ➔ RKNN 양자화 및 컴파일
추출된 ONNX 파일을 타겟 플랫폼(`rv1106`)에 맞게 컴파일합니다. 
본 과정은 Rockchip 공식 툴킷 경로(`/work/rknn-toolkit2/rknn-toolkit2/examples/onnx/yolov5/`) 내에서 진행되었습니다. 양자화 파라미터를 임의로 수정하는 대신, 벤더사(Rockchip) SDK에서 제공하는 YOLOv5 최적화 설정 파일(`model_config.yml`)을 적극 활용하여 안정적인 PTQ 변환을 수행했습니다.

    cd /work/rknn-toolkit2/rknn-toolkit2/examples/onnx/yolov5/
    python3 -m rknn.api.rknn_convert -t rv1106 -i ./model_config.yml -o ./

#### 1.3. 스트리밍 프로젝트 통합
위 과정을 통해 생성된 최종 NPU 추론 모델(`yolov5.rknn`)은 C++ 기반의 실시간 스트리밍 프로젝트 환경(`luckfox-sdk-env` 컨테이너)으로 복사됩니다. 

이전 정지 이미지 추론 프로젝트(`01_image_inference`)에서는 터미널 실행 시 Argument Vector(`argv`)를 통해 모델 경로를 주입받았으나, 본 스트리밍 프로젝트에서는 독립적인 백그라운드 구동 및 실시간 성능을 위해 소스 코드(`main.cc`) 내부에 모델 경로를 하드코딩하여 파이프라인을 완전히 통합했습니다.

    // main.cc 내부 모델 로드 구조
    const char *model_path = "./model/yolov5.rknn";
    init_yolov5_model(model_path, &rknn_app_ctx);

### 2. Cross-Compilation & OS Environment

SC3336 CSI 카메라 모듈의 드라이버가 공식 지원되는 **Buildroot OS**를 타겟으로 크로스 컴파일을 진행했습니다. 본 과정은 Mac(Apple Silicon) 위에서 Docker 에뮬레이션을 통해 이루어졌습니다.

- **Toolchain:** `arm-rockchip830-linux-uclibcgnueabihf-gcc`
- 빌드 시스템(`build.sh`)에서 `uClibc`를 명시적으로 선택하여, 보드의 OS 환경(Buildroot)에 완벽히 호환되는 바이너리를 컴파일했습니다.
- **바이너리 검증 (Smoking Gun):**

      $ file luckfox_pico_rtsp_yolov5
      luckfox_pico_rtsp_yolov5: ELF 32-bit LSB executable, ARM, EABI5 version 1 (SYSV), dynamically linked, interpreter /lib/ld-uClibc.so.0, with debug_info, not stripped

### 3. Media Pipeline Architecture (RKMPI)

본 프로젝트의 C++ 코어(`main.cc`)는 Luckfox SDK의 RKMPI 예제를 기반으로 연동되었습니다. 주요 미디어 파이프라인은 다음과 같이 작동합니다.

1. **VI (Video Input):** `RK_MPI_VI_GetChnFrame` 함수를 통해 카메라에서 원본 프레임을 가져옵니다.
2. **NPU Inference:** 캡처된 프레임을 OpenCV-mobile의 `letterbox`로 전처리(640x640)한 뒤 NPU로 넘겨 객체를 탐지합니다.
3. **OSD Overlay:** 탐지된 BBOX 좌표를 기반으로 `cv::rectangle`, `cv::putText`를 이용해 영상 프레임 위에 렌더링합니다. (Host PC가 아닌 Edge 디바이스 단독 렌더링)
4. **VENC & RTSP:** 오버레이된 영상을 하드웨어 비디오 인코더(`RK_MPI_VENC`)를 통해 H.264 포맷으로 압축하고, `rtsp_tx_video`를 통해 무선 네트워크로 송출합니다.

### 4. Wireless Static IP Infrastructure

RTSP 클라이언트가 무선 환경에서 보드에 안정적으로 접속하려면 IP가 고정되어야 합니다. 하지만 Buildroot 환경은 고수준 네트워크 관리 도구인 `nmcli`를 지원하지 않아, `wpa_supplicant`를 직접 제어하는 커스텀 초기화 스크립트(`S99staticip.sh`)를 작성했습니다.

- 단순 IP 주소 할당 여부가 아닌, `wlan0` 인터페이스의 `RUNNING` (L2 Data Link Layer 연결 완료) 플래그를 감지한 뒤 Static IP를 주입하여, DHCP 데몬(`udhcpc`)과의 충돌을 물리적으로 우회했습니다.

## How to Run

### 1. 호스트에서 크로스 컴파일 및 모델 준비
Luckfox RKMPI 예제 폴더 내에서 빌드 스크립트를 실행하고 `uClibc`를 선택합니다.

    ./build.sh
    # 옵션 1) uclibc 선택
    # 옵션 5) luckfox_pico_rtsp_yolov5 예제 선택

변환이 완료된 `yolov5.rknn` 파일을 빌드된 `install/luckfox_pico_rtsp_yolov5_demo/model/` 폴더 내에 배치합니다.

### 2. 보드로 배포 (Host ➔ Edge)
생성된 배포 폴더 전체를 보드로 전송합니다. 보드의 IP는 작성한 Static IP 스크립트에 의해 고정되어 있다고 가정합니다.

    scp -r ./install/luckfox_pico_rtsp_yolov5_demo pico@<BOARD_STATIC_IP>:/root/

### 3. 보드에서 스트리밍 서버 실행 (Edge)
보드에 SSH로 접속하여 카메라 점유 데몬을 끄고 스트리밍을 시작합니다. 바이너리 실행 시 하드코딩된 경로에 맞게 `.rknn` 모델이 로드됩니다.

    # 기본 백그라운드 카메라 앱 중지
    RkLunch-stop.sh

    cd /root/luckfox_pico_rtsp_yolov5_demo
    chmod +x luckfox_pico_rtsp_yolov5
    ./luckfox_pico_rtsp_yolov5

### 4. 실시간 영상 수신 (Client)
동일 네트워크에 있는 PC 또는 스마트폰에서 VLC Player를 열고 아래 주소로 접속합니다.

    rtsp://<BOARD_STATIC_IP>:554/live/0

## Troubleshooting & Issues

### Problem: DHCP 환경 하에서의 무선 IP 불안정 및 Race Condition

Ubuntu와 달리 Buildroot 환경에서는 `nmcli` 부재로 `udhcpc` 데몬이 지속적으로 IP를 자동 덮어쓰는 **Race Condition**이 발생했습니다. 이로 인해 보드 재부팅 시 RTSP 클라이언트가 기존 주소로 접속하지 못하는 문제가 있었습니다.

**Root Cause:**
- `udhcpc`가 사용자 스크립트의 Static IP 설정을 무시하고 주소를 DHCP 대역으로 롤백시킴.
- 부팅 시퀀스(Init.d) 순서를 조정하더라도 시스템 백그라운드에서 주기적으로 IP를 재할당함.

**Solution (L2 기반 제어):**
IP 주소 할당 확인(L3)이 아닌, `wpa_supplicant`에 의한 물리적 Wi-Fi 인증(L2 Layer) 완료 신호인 `RUNNING` 플래그를 기준으로 트리거를 구성했습니다. 또한 DHCP 클라이언트 동작을 억제하기 위해 `udhcpc` 바이너리를 우회하고 직접 네트워크 설정을 주입했습니다.

    if ifconfig wlan0 | grep -q "RUNNING"; then
        ifconfig wlan0 172.30.1.100 netmask 255.255.255.0
        route add default gw 172.30.1.254
    fi

이를 통해 headless wireless 기기가 전원 인가 후 항상 동일한 RTSP 주소를 안정적으로 확보할 수 있게 되었습니다.

## Next Improvements

- **성능 측정 보강:** 현재 스트리밍 FPS, End-to-end latency, CPU/Memory/NPU 점유율 수치 측정 및 문서화 대기 중
- **Zero-Copy 최적화 검토:** 프레임 버퍼 간의 메모리 복사 병목을 줄이기 위한 RKMPI Zero-Copy 메모리 할당 방식 분석
- 실시간 Demo Video 및 구동 스크린샷 추가 업로드
