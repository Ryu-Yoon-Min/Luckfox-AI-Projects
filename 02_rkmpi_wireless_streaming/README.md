# 02. RK-MPI 기반 무선 객체 탐지 스트리밍 시스템

Luckfox Pico Ultra BW(Rockchip RV1106 NPU) 보드에서 카메라 입력을 받아 객체 탐지를 수행하고, 보드 내부에서 bounding box를 렌더링한 뒤 RTSP로 무선 전송하는 Edge AI streaming project

단순히 보드에서 추론을 실행하는 것이 아닌 model conversion, model quantization, camera capture, NPU inference, bounding box overlay, video encoding, RTSP streaming, wireless static IP infrastructure를 하나의 end-to-end pipeline으로 구축
이를 위해 공식 툴킷을 활용한 모델 양자화(PTQ)와 Docker 기반 크로스 컴파일 환경 구축을 직접 수행

## Project Status

| Component | Status | Evidence |
| :--- | :--- | :--- |
| OS & Hardware Setup | Completed | Buildroot (Official Image) 사용 |
| Model Conversion (PTQ) | Completed | `model/model_config.yml`, `yolov5.rknn` |
| Cross-Compilation | Completed | `src/CMakeLists.txt` (uClibc 타겟) |
| Wireless static IP setup | Completed | `scripts/S99staticip.sh` |
| Network troubleshooting | Completed | L2 기반 레이어 제어 로직 구현 |
| RK-MPI pipeline | Completed | VI / NPU / VENC / RTSP 연동 (`src/main.cc`) |

## Repository Structure

    02_rkmpi_wireless_streaming/
    ├── README.md
    ├── bin/
    │   └── luckfox_pico_rtsp_yolov5    # uClibc 크로스 컴파일 완료된 실행 바이너리
    ├── model/
    │   ├── coco_80_labels_list.txt
    │   ├── model_config.yml            # RKNN 양자화 최적화 설정 파일
    │   └── yolov5.rknn                 # RV1106 NPU 전용으로 직접 변환한 모델
    ├── scripts/
    │   └── S99staticip.sh              # 고정 IP 할당용 커스텀 Boot 스크립트
    └── src/
        ├── CMakeLists.txt              # 크로스 컴파일 빌드 스크립트 (공식 예제 기반)
        └── main.cc                     # RKMPI 스트리밍 & 추론 핵심 소스

## System Overview

    [Host: Mac Local / Docker]
    PyTorch ➔ ONNX ➔ rknn-toolkit2 (PTQ 양자화) ➔ yolov5.rknn 생산
    C/C++ Source ➔ Luckfox SDK (uClibc 툴체인) ➔ luckfox_pico_rtsp_yolov5 생산
                        │
                        ▼ (Deploy)
    [Edge: RV1106 Board]
    CSI Camera
      └── RK-MPI VI (Frame Capture)
            └── RV1106 NPU Inference
                  └── Bounding Box Overlay on Board
                        └── RK-MPI VENC / Stream Encoding
                              └── RTSP Server
                                    └── Wireless Client
                                          └── RTSP Viewer

## Tech Stack and Hardware

| Category | Details |
| :--- | :--- |
| Board | Luckfox Pico Ultra BW |
| SoC | Rockchip RV1106 |
| AI Accelerator | RV1106 NPU |
| Camera | SC3336 3MP CSI Camera Module |
| Media Framework | RK-MPI |
| Network | Wi-Fi, static IP, RTSP |
| OS | Embedded Linux / **Buildroot (Official Image)** |
| Scripts | Shell script, init.d boot script |
| Client Viewer | VLC, ffplay, or RTSP-compatible viewer |


## Key Implementation Details

### 1. OS Selection: Why Buildroot?
이전 이미지 추론 프로젝트(`01_image_inference`)에서는 네트워크 설정이 편리한 Ubuntu 22.04(Community Image)를 사용
하지만 Luckfox 공식 위키에 따르면, 프로젝트에 사용된 SC3336 CSI 카메라 모듈 튜토리얼은 오직 Buildroot 시스템에만 적용 가능, 현재 Ubuntu 환경은 지원하지 않음
이러한 하드웨어 드라이버 지원 제약으로 인해 OS를 이관, 이는 네트워크 설정 및 크로스 컴파일 타겟의 전면적인 변경을 요구

### 2. C++ Source Cross-Compilation (Luckfox SDK & uClibc)
보드에서 실행될 C++ 소스 코드(`main.cc`)의 크로스 컴파일은 **Luckfox 공식 SDK 환경**을 활용
OS가 Buildroot로 변경됨에 따라, Ubuntu 환경에서 쓰던 `glibc` 대신 초경량 C 라이브러리인 **`uClibc`** 환경에 맞춰 빌드 파이프라인 구축 필요

* 벤더사(Luckfox)에서 제공하는 공식 RKMPI 예제 저장소의 `CMakeLists.txt` 구조를 활용

생성된 바이너리(`luckfox_pico_rtsp_yolov5`)는 `file` 명령어 검증 시 `/lib/ld-uClibc.so.0` 인터프리터를 정확히 지목하여 보드 커널과 충돌 없이 단독 구동됨을 확인

<img width="2300" height="380" alt="luckfox_pico_rtsp_yolov5" src="https://github.com/user-attachments/assets/861ea765-3d01-4030-95af-0ba116af4310" />

### 3. Model Conversion & PTQ Quantization (rknn-toolkit2)
C++ 소스코드 크로스 컴파일(SDK 활용)과 별개로, AI 모델을 보드의 NPU가 연산할 수 있는 언어로 변환하기 위해 Python 기반의 **`rknn-toolkit2`** 도구를 사용
무거운 PyTorch 가중치를 직렬화 포맷(`.rknn`)으로 2단계에 걸쳐 변환 및 양자화

1. **ONNX 구조 추출:** YOLOv5 환경에서 `export.py` 스크립트에 `--rknpu` 옵션을 주입하여 RV1106 NPU 최적화 가중치 그래프 포맷을 확보

        python export.py --weights yolov5s.pt --rknpu

2. **INT8 양자화(PTQ):** `luckfox-builder` 도커 환경에서 벤더사(Rockchip)가 공식 제공하는 최적화 설정 파일(`model_config.yml`)을 주입하여 타겟 플랫폼(`RV1106`) 전용 INT8 압축을 완수

        cd /work/rknn-toolkit2/rknn-toolkit2/examples/onnx/yolov5/
        python3 -m rknn.api.rknn_convert -t rv1106 -i ./model_config.yml -o ./

**명령어 상세 분석:**
* `-m rknn.api.rknn_convert`: `rknn-toolkit2` 패키지에 내장된 변환 모듈을 실행
* `-t rv1106`: 모델이 구동될 타겟 NPU 아키텍처를 RV1106 칩으로 명확히 지정
* `-i ./model_config.yml`: 양자화 방식(INT8)과 보정을 위한 데이터셋 파라미터가 담긴 입력(Input) 설정 파일을 주입
* `-o ./`: 양자화가 완료된 `.rknn` NPU 전용 모델을 현재 경로에 출력(Output)

### 4. RK-MPI Camera Capture Pipeline
RK-MPI의 VI(Video Input) pipeline을 사용해 CSI camera module에서 frame을 입력받음
이 단계는 실시간 video stream의 시작점이며, 이후 NPU inference와 encoding pipeline으로 연결
이 구조를 통해 CPU에서 직접 camera frame을 처리하는 방식보다 보드의 multimedia pipeline에 더 적합한 형태로 frame을 다룰 수 있음

### 5. On-Device Object Detection & BBOX Overlay
입력 frame에 대해 RV1106 NPU에서 객체 탐지를 수행, 결과를 외부 PC로 보내는 방식이 아니라 보드 내부에서 inference result를 기반으로 bounding box를 직접 렌더링(OpenCV-mobile)

- host PC에 의존하지 않고 보드 단독으로 시각화 가능
- Edge device가 inference와 visualization을 모두 담당하는 구조로 실시간 처리에 유리
- RTSP stream 수신 시 이미 BBOX가 포함된 영상 확인 가능

### 6. RK-MPI Encoding and RTSP Streaming
Bounding box가 overlay된 frame은 하드웨어 비디오 인코더(`RK_MPI_VENC`)를 거쳐 H.264로 압축된 후 RTSP stream으로 전송, 외부 client는 동일 네트워크에서 RTSP URL에 접속해 실시간 객체 탐지 영상을 확인 가능

### 7. Wireless Static IP Infrastructure
RTSP streaming system은 client가 보드 주소를 안정적으로 알고 있어야 하므로 Boot-time static IP script를 직접 작성하여 DHCP와 충돌하지 않는 네트워크 환경을 구축 (상세 내용은 아래 Troubleshooting 섹션 참조)


## How to Run

### 1. 호스트 환경 빌드 및 컴파일 (Host)

Docker 컨테이너(Luckfox SDK 환경)에서 크로스 컴파일을 수행
본 저장소의 `bin/` 디렉토리에 이미 빌드된 바이너리가 포함되어 있으므로, 단순 실행만 확인할 경우 이 단계는 생략 가능

Luckfox 공식 RK-MPI example SDK의 `build.sh`를 사용해 크로스 컴파일을 수행
- `build.sh`는 본 저장소에 포함된 파일이 아닌 SDK(`luckfox_pico_rkmpi_example/`)에 포함된 공식 빌드 스크립트

    cd /rkmpi_work/luckfox_pico_rkmpi_example
    ./build.sh

    1) libc 선택: uclibc
    2) example 선택: luckfox_pico_rtsp_yolov5

본 저장소는 SDK 전체를 포함하지 않고, RK-MPI example 기반으로 수정한 소스와 배포 스크립트, 모델 구성 파일을 정리

### 2. Wi-Fi 및 Static IP 설정 (Edge)
Buildroot 환경에서는 nmcli를 사용할 수 없으므로 `/etc/wpa_supplicant.conf`에 Wi-Fi 접속 정보를 등록하고, 직접 제작한 `/etc/init.d/S99staticip` 스크립트에서 wlan0 연결 상태(`RUNNING`)를 확인한 뒤 static IP를 주입

    # /etc/wpa_supplicant.conf
    ctrl_interface=/var/run/wpa_supplicant
    ap_scan=1

    network={
        ssid="<WIFI_SSID>"
        psk="<WIFI_PASSWORD>"
    }
    
본 프로젝트에서는 `scripts/S99staticip.sh`를 `/etc/init.d/S99staticip`로 배치하여 부팅 시 자동 실행되도록 구성
스크립트는 기존 `wpa_supplicant`, `udhcpc` 프로세스를 정리한 뒤 `wlan0`을 활성화하고, Wi-Fi association이 완료되어 RUNNING flag가 확인되면 static IP, gateway, DNS를 설정

아래는 `S99staticip.sh`의 전체 원문이 아니라, 실제 스크립트의 핵심 static IP 설정 흐름을 요약한 내용
    
    killall -9 wpa_supplicant 2>/dev/null
    killall -9 udhcpc 2>/dev/null
    
    ifconfig wlan0 up
    wpa_supplicant -B -i wlan0 -c /etc/wpa_supplicant.conf
    
    # wlan0의 RUNNING flag 확인 후 static IP 주입
    ifconfig wlan0 172.30.1.100 netmask 255.255.255.0
    route add default gw 172.30.1.254
    echo "nameserver 8.8.8.8" > /etc/resolv.conf

설정 후 보드에서 아래 명령으로 IP와 routing table을 확인

    ifconfig wlan0
    route -n
    cat /etc/resolv.conf

### 3. 보드로 배포 (Host ➔ Edge)
생성된 실행 파일, 모델(.rknn), 라벨 파일을 보드의 작업 폴더로 전송, 보드의 IP는 앞 단계에서 `/etc/init.d/S99staticip`로 적용한 static IP를 사용한다고 가정

    scp ./bin/luckfox_pico_rtsp_yolov5 pico@<BOARD_STATIC_IP>:/root/
    scp ./model/* pico@<BOARD_STATIC_IP>:/root/model/

### 4. 보드에서 무선 스트리밍 시작 (Edge)
보드에 SSH로 접속하여 기본 카메라 점유 데몬을 끄고 스트리밍 애플리케이션을 실행

    # 기본 백그라운드 카메라 앱 중지
    RkLunch-stop.sh

    chmod +x luckfox_pico_rtsp_yolov5
    ./luckfox_pico_rtsp_yolov5

### 5. Client에서 RTSP 수신 (Client)
동일 네트워크에 있는 PC 또는 스마트폰에서 VLC Player를 열고 아래 RTSP URL로 접속

    rtsp://<BOARD_STATIC_IP>:554/live/0


## Demo

### RTSP Streaming Demo
https://github.com/user-attachments/assets/c397766c-768e-4e58-b90c-1e39d002bc95

- RTSP 해상도: 측정 후 기입
- FPS: 측정 후 기입
- latency 대략값: 측정 후 기입 
- 테스트 시간: 30분 이상
- 재부팅 테스트 횟수: 10회
- 사용한 공유기/네트워크 환경: 측정 후 기입

### Screenshot
<img width="3514" height="1958" alt="vlc_addr" src="https://github.com/user-attachments/assets/8081be58-0b81-4d69-b6c5-7dce07f6e99d" />

<img width="5712" height="4284" alt="IMG_4203" src="https://github.com/user-attachments/assets/a5524483-d227-46de-8997-97e12a743239" />


## Troubleshooting & Issues

### Problem: WLAN Static IP Override by udhcpc

Ubuntu 환경과 달리 Buildroot 환경에서는 `nmcli`를 사용할 수 없어 `wpa_supplicant.conf`를 통해 Wi-Fi를 연결
RTSP client는 보드의 IP 주소를 기준으로 stream에 접속, 하지만 DHCP 환경에서는 보드가 재부팅될 때마다 IP가 바뀔 수 있어 매번 새로운 주소를 확인해야 하는 문제가 발생

**Issue**
- 보드 재부팅 후 IP가 변경 가능성
- RTSP client가 기존 URL로 접속할 수 없음
- headless device 운용성이 떨어짐

**Root Cause**
- DHCP client인 `udhcpc`가 자동으로 IP를 재할당
- 사용자 script에서 static IP를 설정해도 이후 시스템 daemon이 다시 DHCP 주소를 덮어씀
- 단순히 IP가 생겼는지 확인하는 방식은 DHCP와 충돌할 수 있음

**Solution**
IP 주소 할당 여부가 아니라, `wlan0`의 `RUNNING` flag를 기준으로 Wi-Fi association이 완료됐는지 확인한 뒤 static IP를 주입

    if ifconfig wlan0 | grep -q "RUNNING"; then
        ifconfig wlan0 172.30.1.100 netmask 255.255.255.0
        route add default gw 172.30.1.254
        echo "nameserver 8.8.8.8" > /etc/resolv.conf
    fi

### Trouble Shooting Flow

**[Phase 1] Simple Application Script & Race Condition**
* **시도:** `/etc/init.d/S99staticip` 스크립트를 생성하여 부팅 시 IP 수동 할당
* **증상:** 재부팅 시 IP가 다시 공유기 할당 주소로 회귀함(IP 주소 재할당)
* **분석:** 백그라운드에서 실행되는 `udhcpc`(DHCP 클라이언트)가 사용자 설정을 무시하고 주소를 다시 덮어쓰는 **Race Condition(경쟁 상태)** 발생 확인

**[Phase 2] Process Kill & Asynchronous Optimization**
* **전략:** IP가 할당될 때까지 Polling, `killall -9 udhcpc`로 방해 요소를 제거, 고정 IP를 주입하는 로직 구현
* **최적화:** 네트워크 안정화 대기 시간 동안 부팅 시퀀스가 멈추는 것을 방지하기 위해 함수를 **Background(`&`)**로 실행하여 부팅 속도 보호
* **한계:** 특정 시점에 인터페이스가 재시작되며 주소가 롤백, `udhcpc` 프로세스를 죽여도 시스템 데몬에 의해 재실행(Respawn)되는 끈질긴 간섭 확인

**[Phase 3] Root Cause Discovery**
* **분석:** `grep -rn "udhcpc" /etc/init.d/`를 통해 부팅시 `udhcpc`를 소환하는 근본 스크립트 추적
* **발견:** `/etc/init.d/S99hciinit` 스크립트가 인터페이스 활성화와 동시에 DHCP 요청을 강제하고 있음을 식별. 커스텀 스크립트와 동일한 우선순위(`S99`)에서 발생하는 시스템 레이어의 충돌임을 확신
<img width="1764" height="830" alt="스크린샷 2026-06-29 오전 2 43 44" src="https://github.com/user-attachments/assets/91ccbd53-25e6-414b-a704-0ec054db95cf" />

**[Phase 4] Execution Priority Adjustment (Init.d Sequence)**
* **시도:** 기본 스크립트를 S90hciinit으로 앞당기고 커스텀 스크립트는 S99staticip로 유지, 시스템이 먼저 Wi-Fi를 초기화, 마지막에 고정 IP 스크립트가 실행되어 주도권을 뺏어오는 전략 시도
* **한계:** 여전히 공유기 할당 주소로 IP가 덮어씌워지거나 설정 자체가 실패
* **분석:** init.d의 실행 순서를 조작하더라도 **Rockchip 전용 네트워크 데몬**이 부팅 이후에도 L2 이벤트를 실시간 감시하며 udhcpc를 강제 호출, 텍스트 스크립트 수정만으로는 하드코딩된 '상시 감시 및 자동 복구 메커니즘'을 막을 수 없음을 깨달음


**[Phase 5] Strategy Shift: L2 vs L3**
* **문제점:** DHCP 기능을 원천 차단하기 위해 바이너리를 `udhcpc_backup`으로 Renaming하자, 기존 커스텀 스크립트(`S99staticip`) 내의 IP 주소가 할당되기를 기다리는 로직(L3)이 조건을 충족하지 못해 무한 대기에 빠지는 논리적 모순 발생
* **기술적 통찰:** IP 주소 할당(L3 Network Layer) 과정이 없더라도, `wpa_supplicant` 데몬을 통한 와이파이 인증 및 연결(L2 Data Link Layer)이 완료되면 인터페이스에 `RUNNING` 플래그가 활성화된다는 점에 착안
* **최종 해결:**
  1. **바이너리 무력화:** `udhcpc`의 이름을 변경하여 시스템의 자동 DHCP 요청 수단 자체를 물리적으로 제거
  2. **로직 개선:** IP 존재 여부가 아닌 L2 인터페이스의 **`RUNNING`(연결 신호)** 상태를 감지하여 즉시 고정 IP를 주입하는 방식으로 스크립트 고도화

**Result**
- DHCP 의존도를 줄이고 static IP 기반 접근 가능
- RTSP client가 동일 URL로 보드에 접근 가능
- headless wireless device 운용 기반 확보

#### Key Achievements
* **인프라 확정:** 시스템의 자동 복구 메커니즘과 충돌 없이 타겟 주소 고정 성공
* **성능 및 안정성:** Static IP 설정 루틴을 background task로 실행하여 부팅 시퀀스가 네트워크 안정화 대기 때문에 멈추지 않도록 했고, DHCP로 할당되는 임시 주소 대신 고정 RTSP URL로 접근할 수 있는 구조를 구성
* **역량:** OS 환경의 제약(Buildroot)으로 인한 하위 레벨 제어 필요성을 인지, **OS 초기화 시퀀스, 프로세스 생명주기, 네트워크 레이어(L2/L3)** 전반을 관통하는 임베디드 인프라 제어 역량 확보

## What This Project Demonstrates

이 프로젝트는 Luckfox RV1106 보드를 단순한 inference board가 아닌, 독립적으로 동작하는 wireless Edge AI streaming device로 구성하는 과정을 증명

주요 역량:
- 하드웨어 제약(CSI Camera)에 따른 OS 환경 전환 및 Buildroot(uClibc) 적응
- NPU 최적화를 위한 ONNX ➔ RKNN 모델 변환 및 PTQ 양자화 파이프라인(rknn-toolkit2) 구축
- C++ 소스 코드 및 CMakeLists.txt 기반의 크로스 컴파일(Luckfox SDK) 수행
- RK-MPI 기반 camera capture 및 hardware encoding(VENC) 구성
- RV1106 NPU 기반 on-device inference 및 OpenCV BBOX overlay
- RTSP 기반 wireless video streaming 시스템 구축
- DHCP, Wi-Fi association, static IP 설정 문제의 root-cause analysis 및 L2 제어
