# Luckfox AI Projects
## 🚀 Luckfox AI Projects (NPU Vision Pipeline)

이 레포지토리는 Rockchip RV1106 NPU (Luckfox Pico Ultra)를 활용한 임베디드 AI 비전 프로젝트들을 단계별로 기록한 통합 저장소입니다.

## Project Status

| Project | Status | Evidence |
| :--- | :--- | :--- |
| `01_image_inference_mac` | Completed | `detections.txt`, `auto_draw.py`, `run.sh`, `result.jpg` |
| `02_rkmpi_wireless_streaming` - Static IP setup | Completed | `scripts/S99staticip.sh`, `troubleshooting.md` |
| `02_rkmpi_wireless_streaming` - RK-MPI/RTSP streaming | In Progress | README에 구현 계획 정리 |

## 📂 Projects

[01] RV1106 추론 및 로컬 Mac 시각화 자동화 (/01_image_inference_mac)

### 1. RV1106 추론 및 로컬 Mac 시각화 자동화 (/01_image_inference_mac)

Description: 정지 이미지(bus.jpg)에 대한 YOLOv5 NPU 추론을 수행하고, 결과를 로컬 Mac으로 전송하여 시각화합니다.

* **NPU Inference (보드):** C++ 기반 RKNN API를 이용해 YOLOv5 모델 추론 후 좌표 추출 (`detections.txt`)
* **Automated Pipeline (로컬 Mac):** Shell Script(`run.sh`)를 통한 SSH 데이터 통신 및 Python OpenCV 팝업 자동 렌더링
* **Tech Stack:** C/C++, Python, Bash, RKNN-Toolkit2, OpenCV

![result](https://github.com/user-attachments/assets/6fa12756-8aa4-4e12-89b2-dc933065f12a)

Structure:
01_image_inference_mac/
├── bus.jpg               # Input Image
├── detections.txt        # Serialized Inference Data (Generated)
├── auto_draw.py          # Visualization Logic
└── run.sh                # Automation Entry Point

## 🔑 Key Implementation Details

### 1. Custom Data Serialization Layer (C++)
**"From Ephemeral Logs to Structured Data"**

기존 SDK의 `rknn_yolov5_demo`는 추론 결과를 단순히 콘솔(`stdout`)에 출력하도록 설계되어 있어, 외부 프로그램이 이 데이터를 활용할 수 없는 **Data Silo(데이터 고립)** 문제가 존재했습니다. 이를 해결하기 위해 C++ 레벨에서 데이터 직렬화(Serialization) 계층을 직접 구현했습니다.

* **Logic Modification:** `main.cc` 내부의 결과 처리 로직을 수정하여, 감지된 객체(Object) 정보를 정형화된 텍스트 포맷으로 변환.
* **Protocol Design:** 각 라인마다 하나의 객체 정보를 담는 자체 프로토콜 정의.
    > `Format: [Label] [x1] [y1] [x2] [y2] [Confidence]`

**💻 Code Comparison:**

| Type | Implementation | Consequence |
| :--- | :--- | :--- |
| **Before** | `printf("%s @ (%d %d %d %d) %.3f\n", ...)` | 터미널에 출력되고 사라짐 (휘발성). 타 프로그램 연동 불가. |
| **After** | `fprintf(fp, "%s %d %d %d %d %f\n", ...)` | `detections.txt` 파일로 영구 저장. **IPC(프로세스 간 통신) 가능.** |

---

### 2. Automated Visualization Pipeline (Bash & Python)
**"Seamless Edge-to-Host Workflow"**

임베디드 보드(Edge)의 컴퓨팅 파워를 아끼고 개발 편의성을 높이기 위해, 데이터 전송과 시각화를 **원클릭(One-Click)**으로 처리하는 자동화 파이프라인을 구축했습니다.

#### A. Data Transport via Shell Script (`run.sh`)
Mac 로컬 환경에서 실행되는 Bash 스크립트로, SSH/SCP 프로토콜을 활용해 이기종 기기 간의 데이터 브리지 역할을 수행합니다.
* **Network Handshake:** 하드코딩된 Static IP(`*.*.*.*`)를 통해 NPU 보드에 접근.
* **Data Fetching:** 보드 내 생성된 `detections.txt` (좌표 데이터)를 로컬로 보안 전송(`scp`).
* **Trigger:** 전송 완료 직후 Python 시각화 스크립트를 자동으로 호출.

#### B. Rendering Engine via Python (`auto_draw.py`)
전송받은 텍스트 데이터를 파싱(Parsing)하여 시각적 정보로 복원합니다.
* **Parsing Logic:** `detections.txt`를 라인별로 읽어 좌표(ROI)와 클래스 정보를 추출.
* **OpenCV Rendering:** 원본 이미지(`bus.jpg`) 위에 Bounding Box와 Label, Confidence Score를 오버레이(Overlay) 드로잉.
* **Result:** 별도의 모니터 연결 없이(Headless), 로컬 PC에서 즉시 결과 확인 가능.

## 🔧 Troubleshooting & Issues

### 1. Wi-Fi 네트워크 불안정 및 SSH 연결 끊김 해결
**문제 상황 (Issue):**
보드 부팅 후 SSH 접속 시 연결이 자주 끊기거나(Timeout), 재부팅 시마다 IP 주소가 변경되어 매번 새로운 IP를 확인해야 하는 번거로움 발생.

**원인 (Cause):**
* DHCP(동적 할당)로 인해 IP가 유동적으로 변경됨.
* 절전 모드 진입이나 신호 불안정으로 인한 세션 종료.

**해결 (Solution): `nmcli`를 통한 고정 IP(Static IP) 할당 및 자동 연결 설정**
`nmcli` 명령어를 사용하여 와이파이에 연결하고, 해당 연결 설정(connection)을 수정하여 보드가 켜질 때마다 항상 같은 IP(`*.*.*.*`)를 잡도록 고정함.

```bash
# 1. 와이파이 스캔 및 연결
nmcli dev wifi
nmcli dev wifi connect "WIFI_NAME(SSID)" password "password"

# 2. 연결 확인 (연결 이름 확인)
nmcli connection show

# 3. 고정 IP 설정 (예: *.*.*.*) 및 자동 연결 활성화
# 'WIFI_NAME' 자리에는 위에서 확인한 연결 이름(보통 SSID) 입력
nmcli connection modify "WIFI_NAME" ipv4.addresses *.*.*.*/24
nmcli connection modify "WIFI_NAME" ipv4.gateway 192.168.45.1
nmcli connection modify "WIFI_NAME" ipv4.dns "8.8.8.8"
nmcli connection modify "WIFI_NAME" ipv4.method manual  # shell script(run.sh)내에서 하드코딩된 IP 주소를 사용하기 위해 고정 IP 할당
nmcli connection modify "WIFI_NAME" connection.autoconnect yes

# 4. 설정 적용 (재연결)
nmcli connection up "WIFI_NAME"
```

