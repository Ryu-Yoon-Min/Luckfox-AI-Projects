# 🚀 Luckfox AI Projects (NPU Vision Pipeline)

이 레포지토리는 Rockchip RV1106 NPU (Luckfox Pico Ultra BW)를 활용한 임베디드 AI 비전 프로젝트들을 단계별로 기록한 통합 저장소입니다. 

단일 이미지 기반의 추론 및 데이터 직렬화 시스템(`01_image_inference_mac`)에서 시작하여, 하드웨어 카메라 입력을 직접 받아 무선으로 실시간 전송하는 종단간(End-to-End) RTSP 스트리밍 파이프라인(`02_rkmpi_wireless_streaming`)으로 발전해 나가는 과정을 담고 있습니다.

## 📊 Project Status

| Project | Target OS | Status | Evidence & Artifacts |
| :--- | :--- | :--- | :--- |
| `01_image_inference_mac` | Ubuntu 22.04 (Community) | Completed | `src/main.cc`, `detections.txt`, `auto_draw.py`, `run.sh` |
| `02_rkmpi_wireless_streaming` | Buildroot (Official) | Completed | RK-MPI VI/VENC pipeline, `S99staticip.sh`, PTQ Models |

## 📂 Repository Structure

    Luckfox-AI-Projects/
    ├── 01_image_inference_mac/          # [Step 1] 정지 이미지 추론 및 Mac 로컬 시각화
    │   ├── bin/rknn_yolov5_demo         # Ubuntu (glibc) 타겟 크로스 컴파일 바이너리
    │   ├── board_src/                   # 파일 입출력(fprintf) 커스텀 C++ 소스
    │   └── run.sh / auto_draw.py        # SSH 데이터 통신 및 렌더링 스크립트
    │
    └── 02_rkmpi_wireless_streaming/     # [Step 2] 카메라 기반 실시간 무선 스트리밍
        ├── bin/luckfox_pico_rtsp_yolov5 # Buildroot (uClibc) 타겟 크로스 컴파일 바이너리
        ├── model/                       # RKNN 양자화 설정 및 NPU 전용 모델 파일
        ├── scripts/S99staticip.sh       # L2 계층 네트워크 트러블슈팅 스크립트
        └── src/                         # RKMPI 미디어 파이프라인 C++ 코어 소스

---

## 🔑 Key Engineering Achievements

### 1. Data Pipeline Evolution: From Ephemeral Logs to Real-time Stream
단순히 예제 코드를 실행하는 것을 넘어, 데이터의 활용성을 극대화하는 방향으로 아키텍처를 개선했습니다.
* **Step 1 (01 Project):** 터미널에 출력되고 사라지는 로그(`stdout`)를 C++ 파일 입출력(`fprintf`)을 통해 구조화된 텍스트(`detections.txt`)로 저장하여 IPC(프로세스 간 통신) 기반을 마련했습니다.
* **Step 2 (02 Project):** 텍스트 기반 메타데이터 전송을 넘어, 렌더링까지 보드 내부에서 완료한 H.264/H.265 비디오 스트림을 실시간 무선 전송(RTSP)하는 수준으로 고도화했습니다.

### 2. OS 및 하드웨어 제약에 따른 유연한 인프라 대응 (Headless Network)
보드에 모니터를 연결하지 않는 Headless 환경에서 무선 통신을 유지하기 위해서는 **'재부팅 후에도 변하지 않는 고정 IP(Static IP)'** 확보가 필수적입니다. 프로젝트 요구사항에 따라 달라진 OS 환경에 맞춰 각각 최적의 네트워크 인프라를 구축했습니다.

* **Ubuntu 22.04 (`01`):** `nmcli`와 같은 고수준 네트워크 관리 도구를 적극 활용하여 안정적인 Static IP 및 자동 연결 환경을 구성했습니다.
* **Buildroot (`02`):** CSI 카메라 구동을 위해 Buildroot로 OS를 전환함에 따라 `nmcli` 부재 및 백그라운드 데몬(`udhcpc`)에 의한 IP 덮어쓰기(**Race Condition**)가 발생했습니다. 이를 해결하기 위해 `wpa_supplicant`의 Wi-Fi L2 인증 완료(`RUNNING`) 플래그를 감지한 즉시 비동기로 Static IP를 주입하는 커스텀 스크립트를 작성하여 시스템 충돌을 완벽히 우회했습니다.

### 3. Cross-Compilation & Hardware-Specific Optimization
호스트 PC와 엣지 디바이스 간의 아키텍처 차이를 극복하고 NPU 자원을 100% 활용하기 위한 빌드 및 최적화 파이프라인을 구축했습니다.

* **타겟 맞춤형 크로스 컴파일 분리 적용:** OS 종속성을 고려하여 01 프로젝트는 `arm-rockchip830-linux-gnueabihf-gcc` (glibc 기반)로, 02 프로젝트는 카메라 제어에 필요한 초경량 환경을 위해 `arm-rockchip830-linux-uclibcgnueabihf-gcc` (uClibc 기반) 툴체인으로 분리하여 빌드를 완료했습니다.
* **NPU 추론을 위한 모델 양자화 (PTQ):**
  FP32 기반의 무거운 PyTorch 가중치(`.pt`)를 그대로 사용하지 않고, 벤더사(Rockchip) SDK가 제공하는 YOLOv5 최적화 설정 파일(`model_config.yml`)을 활용했습니다. 이를 통해 NPU 하드웨어 가속에 최적화된 INT8 기반의 직렬화 포맷(`.rknn`)으로 모델을 완벽하게 양자화 변환하여 보드에 통합했습니다.
