# 02. RK-MPI 기반 무선 비전 스트리밍 서버 구축 (Luckfox RV1106)

## 📌 Project Overview
이 프로젝트는 Rockchip의 하드웨어 가속 미디어 처리 인프라(RK-MPI)를 활용하여, Luckfox Pico Ultra BW 보드를 독립형(Headless) 무선 카메라 스트리밍 서버로 구축하는 과정을 담고 있습니다. 

센서(Camera)에서 입력받은 Raw 영상을 NPU 연산이나 외부 모니터링 시스템으로 전송하기 위한 필수적인 '눈'과 '통신망'을 만드는 파이프라인입니다.

## 🛠️ System Architecture & Tech Stack
* **Hardware:** Luckfox Pico Ultra BW (RV1106), CSI Camera Module
* **Framework:** RK-MPI (Rockchip Multimedia Process Infrastructure)
* **OS / Environment:** Embedded Linux (Buildroot), Shell Scripting
* **Network:** Wi-Fi (wlan0), Static IP Allocation, RTSP (Real-Time Streaming Protocol)

---

## 🚀 Step 1. Infrastructure Setup: 네트워크 독립성 확보
RK-MPI 스트리밍 서버를 디버그 케이블 없이 무선으로 원활하게 접근하기 위해, 시스템의 DHCP 강제 할당 메커니즘을 제어하고 고정 IP 인프라를 구축했습니다.

* **Implementation:** Booting 시 자동으로 wlan0 Interface(L1)를 동작시키고, Wi-Fi 연결(RUNNING Flag, L2) 후 Static IP(L3)를 부여하는 커스텀 데몬 스크립트`02_rkmpi_wireless_streaming/scripts/S99staticip` 작성. 해당 script를 보드의 `/etc/init.d/` 에 삽입.

* 우선 `/etc/wpa_supplicant.conf`에 AP(Access Point)의 SSID와 PWD를 입력해줍니다.
* **Target IP:** `02_rkmpi_wireless_streaming/scripts/S99staticip`에 원하는 IP 설정.
* 보드 reboot 후 ifconfig wlan0를 통해 IP 할당 확인.

* **상세 트러블슈팅 리포트:** [Network Connecting Problem](./troubleshooting.md)
---

## 🚀 Step 2. RK-MPI Streaming Implementation (WIP)
*(개발 진행 중 - 코드가 완성되면 이 부분을 업데이트할 예정입니다.)*

* **Video Capture:** VI (Video Input) 채널을 통한 카메라 센서 데이터 획득
* **Video Encoding:** VENC (Video Encoder) 모듈을 활용한 하드웨어 가속 H.264/H.265 인코딩
* **RTSP Server:** 인코딩된 스트림을 네트워크를 통해 전송하는 RTSP 서버 연동 (`rtsp://192.168.1.100/live/0`)

## 💡 How to Run (Execution Guide)
1. **네트워크 설정 적용**
