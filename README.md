# 🚀 Luckfox AI Projects (NPU Vision Pipeline)

이 레포지토리는 Rockchip RV1106 NPU (Luckfox Pico Ultra BW)를 활용한 임베디드 AI 비전 프로젝트들을 단계별로 기록한 통합 저장소입니다. 

단일 이미지 기반의 추론 및 데이터 직렬화 시스템(`01_image_inference_mac`)에서 시작하여, 하드웨어 카메라 입력을 직접 받아 무선으로 실시간 전송하는 종단간(End-to-End) RTSP 스트리밍 파이프라인(`02_rkmpi_wireless_streaming`)으로 발전해 나가는 과정을 담고 있습니다.

## 📊 Project Status

| Project | Target OS | Status | Evidence & Artifacts |
| :--- | :--- | :--- | :--- |
| `01_image_inference_mac` | Ubuntu 22.04 (Community) | Completed | `src/main.cc`, `detections.txt`, `auto_draw.py`, `run.sh`, `result.jpg` |
| `02_rkmpi_wireless_streaming` | Buildroot (Official) | Completed | RK-MPI VI/VENC pipeline, `scripts/S99staticip.sh`, `troubleshooting.md` |

---

## 📂 Projects Overview

### [01] RV1106 추론 및 로컬 Mac 시각화 자동화 (`/01_image_inference_mac`)
정지 이미지(`bus.jpg`)에 대한 YOLOv5 NPU 추론을 수행하고, 결과를 로컬 Mac으로 전송하여 시각화하는 Host-Side 파이프라인입니다.
* **NPU Inference (보드):** C++ 기반 RKNN API를 이용해 YOLOv5 모델 추론 후 좌표 추출.
* **Data Serialization:** 단순 콘솔 출력이 아닌 `detections.txt`로 추론 데이터를 영구 직렬화하여 IPC(프로세스 간 통신) 기반 마련.
* **Automated Pipeline (Mac):** Shell Script(`run.sh`)를 통한 SSH 데이터 통신 및 Python OpenCV 팝업 자동 렌더링.

### [02] RK-MPI 기반 무선 객체 탐지 스트리밍 시스템 (`/02_rkmpi_wireless_streaming`)
SC3336 CSI 카메라 입력을 받아 NPU 추론 및 Bounding Box 오버레이를 보드 내부에서 처리한 뒤, RTSP 프로토콜을 통해 무선으로 실시간 스트리밍하는 Edge AI 파이프라인입니다.
* **Hardware Adaptation:** CSI 카메라 모듈 지원 제약으로 인해 OS를 **Ubuntu에서 Buildroot로 이관**.
* **RK-MPI Pipeline:** VI (비디오 입력) -> NPU 추론 -> On-Device BBOX 오버레이 -> VENC (비디오 인코딩) -> RTSP 스트리밍 구축.
* **Custom Network Infrastructure:** Buildroot 환경의 한계(`nmcli` 부재)를 극복하기 위해 `udhcpc`와 `wpa_supplicant`를 제어하는 Boot-time Static IP 스크립트 작성.

---

## 🔑 Key Engineering Achievements

### 1. Data Pipeline Evolution: From Ephemeral Logs to Real-time Stream
단순히 예제 코드를 실행하는 것을 넘어, 데이터의 활용성을 극대화하는 방향으로 아키텍처를 개선했습니다.
* **Step 1 (01 Project):** 터미널에 출력되고 사라지는 로그(`stdout`)를 C++ 파일 입출력(`fprintf`)을 통해 구조화된 텍스트(`detections.txt`)로 저장. 외부 프로그램(Python)과 연동 가능한 상태 구축.
* **Step 2 (02 Project):** 텍스트 기반 메타데이터 전송을 넘어, 렌더링까지 보드 내부에서 완료한 H.264/H.265 비디오 스트림을 실시간 무선 전송(RTSP)하는 수준으로 고도화.

### 2. OS 및 하드웨어 제약에 따른 유연한 인프라 대응 (Headless Network)
보드에 모니터를 연결하지 않는 Headless 환경에서 무선 통신을 유지하기 위해서는 **'재부팅 후에도 변하지 않는 고정 IP(Static IP)'** 확보가 필수적입니다. 프로젝트 요구사항에 따라 달라진 OS 환경에 맞춰 각각 최적의 네트워크 인프라를 구축했습니다.

#### A. Ubuntu 22.04 환경 (`01_image_inference_mac`)
`nmcli`와 같은 고수준 네트워크 관리 도구를 적극 활용하여 안정적인 Static IP 및 자동 연결 환경을 구성했습니다.

    # 고정 IP 설정 및 자동 연결 활성화 예시
    nmcli connection modify "WIFI_NAME" ipv4.addresses *.*.*.*/24
    nmcli connection modify "WIFI_NAME" ipv4.method manual
    nmcli connection modify "WIFI_NAME" connection.autoconnect yes
    nmcli connection up "WIFI_NAME"

#### B. Buildroot 환경 (`02_rkmpi_wireless_streaming`)
CSI 카메라 구동을 위해 Buildroot로 OS를 전환함에 따라 `nmcli`를 사용할 수 없는 제약이 발생했습니다. 
단순히 `ifconfig`로 IP를 강제 할당할 경우, 백그라운드 데몬(`udhcpc`)이 IP를 다시 공유기 할당 주소로 덮어쓰는 **Race Condition**이 발생함을 확인했습니다. 

이를 해결하기 위해 시스템 초기화 시퀀스(OS Boot Sequence)와 네트워크 계층(L2/L3)에 개입하는 커스텀 스크립트를 작성했습니다.
* **Root Cause Analysis:** `udhcpc` 바이너리 이름을 변경하여 강제 호출 차단.
* **L2 기반 제어:** `wpa_supplicant`가 Wi-Fi L2 인증을 마친 `RUNNING` 상태 플래그를 감지한 즉시 비동기(Background)로 Static IP를 주입.
* **Result:** 시스템 자동 복구 메커니즘과의 충돌을 완벽히 해결하고 부팅 지연 시간 0초의 커스텀 네트워크 인프라 완성. (상세 내용은 `02_rkmpi_wireless_streaming/troubleshooting.md` 참고)
