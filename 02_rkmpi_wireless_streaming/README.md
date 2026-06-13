# 02. RK-MPI 기반 무선 객체 탐지 스트리밍 시스템

Luckfox Pico Ultra BW(Rockchip RV1106 NPU) 보드에서 카메라 입력을 받아 객체 탐지를 수행하고, 보드 내부에서 bounding box를 렌더링한 뒤 RTSP로 무선 전송하는 Edge AI streaming project입니다.

이 프로젝트의 핵심은 단순히 보드에서 추론을 실행하는 것이 아니라, camera capture, NPU inference, bounding box overlay, video encoding, RTSP streaming, wireless static IP infrastructure를 하나의 end-to-end pipeline으로 연결한 점입니다.

## Project Status

| Component | Status | Evidence |
| :--- | :--- | :--- |
| Wireless static IP setup | Completed | `scripts/S99staticip.sh` |
| Network troubleshooting | Completed | `troubleshooting.md` |
| Camera input pipeline | Completed | RK-MPI VI pipeline |
| On-device object detection | Completed | RV1106 NPU inference |
| On-device bounding box overlay | Completed | 보드 내부 BBOX rendering |
| RTSP streaming | Completed | RTSP client demo video 필요 |
| Performance metrics | To be measured | FPS, latency, memory usage 등 추가 예정 |

## Repository Structure

```text
02_rkmpi_wireless_streaming/
├── README.md
├── troubleshooting.md
└── scripts/
    └── S99staticip.sh
```

> Note: 현재 README는 시스템 구조와 네트워크 인프라, 트러블슈팅 중심으로 정리합니다. RK-MPI streaming source code, 실행 로그, demo video, metric 결과는 추가 evidence로 보강할 예정입니다.

## System Overview

```text
CSI Camera
  └── RK-MPI VI
        └── Frame Capture
              └── RV1106 NPU Inference
                    └── Bounding Box Overlay on Board
                          └── RK-MPI VENC / Stream Encoding
                                └── RTSP Server
                                      └── Wireless Client
                                            └── RTSP Viewer
```

## Tech Stack and Hardware

| Category | Details |
| :--- | :--- |
| Board | Luckfox Pico Ultra BW |
| SoC | Rockchip RV1106 |
| AI Accelerator | RV1106 NPU |
| Camera | CSI camera module |
| Media Framework | RK-MPI |
| Network | Wi-Fi, static IP, RTSP |
| OS | Embedded Linux / Buildroot |
| Scripts | Shell script, init.d boot script |
| Client Viewer | VLC, ffplay, or RTSP-compatible viewer |

## Key Implementation Details

### 1. RK-MPI Camera Capture Pipeline

RK-MPI의 VI(Video Input) pipeline을 사용해 CSI camera module에서 frame을 입력받습니다. 이 단계는 실시간 video stream의 시작점이며, 이후 NPU inference와 encoding pipeline으로 연결됩니다.

일반적인 흐름은 다음과 같습니다.

```text
Camera Sensor
  └── VI channel
        └── Frame buffer
              └── Inference / Overlay stage
```

이 구조를 통해 CPU에서 직접 camera frame을 처리하는 방식보다 보드의 multimedia pipeline에 더 적합한 형태로 frame을 다룰 수 있습니다.

### 2. On-Device Object Detection

입력 frame에 대해 RV1106 NPU에서 객체 탐지를 수행합니다. 이 프로젝트에서는 객체 탐지 결과를 외부 PC로 보내서 그리는 방식이 아니라, 보드 내부에서 inference result를 기반으로 bounding box를 렌더링하는 구조를 목표로 합니다.

이 방식의 장점은 다음과 같습니다.

- host PC에 의존하지 않고 보드 단독으로 탐지 결과를 시각화할 수 있음
- RTSP stream을 수신하는 쪽에서는 이미 BBOX가 포함된 영상을 바로 확인할 수 있음
- Edge device가 inference와 visualization을 모두 담당하는 구조로 확장 가능

### 3. On-Device Bounding Box Overlay

NPU inference result에서 얻은 class, confidence, bounding box 좌표를 기반으로 보드 내부에서 영상 frame 위에 BBOX를 렌더링합니다.

```text
Inference result
  └── label / score / bbox 좌표
        └── frame overlay
              └── encoded stream
```

이 단계가 중요한 이유는, 단순히 detection metadata를 출력하는 수준을 넘어 실제 video stream에 탐지 결과를 포함시키기 때문입니다.

### 4. RK-MPI Encoding and RTSP Streaming

Bounding box가 overlay된 frame은 video encoding pipeline을 거쳐 RTSP stream으로 전송됩니다. 외부 client는 동일 네트워크에서 RTSP URL에 접속해 실시간 객체 탐지 영상을 확인할 수 있습니다.

예상 접속 형태는 다음과 같습니다.

```text
rtsp://<BOARD_STATIC_IP>:<PORT>/<STREAM_PATH>
```

예시:

```text
rtsp://172.30.1.100:8554/live/0
```

> 실제 RTSP URL은 구현 환경에 맞게 수정해야 합니다.

### 5. Wireless Static IP Infrastructure

RTSP streaming system은 client가 보드 주소를 안정적으로 알고 있어야 합니다. 하지만 DHCP 환경에서는 보드가 재부팅될 때마다 IP가 바뀔 수 있어, RTSP client가 지속적으로 접근하기 어렵습니다.

이를 해결하기 위해 boot-time static IP script를 작성했습니다.

```text
Boot
  └── wlan0 up
        └── wpa_supplicant association
              └── RUNNING flag 확인
                    └── static IP / gateway / DNS 설정
```

관련 script:

```text
scripts/S99staticip.sh
```

이 static IP infrastructure 덕분에 전원 재인가 후에도 client가 동일한 주소로 RTSP stream에 접근할 수 있습니다.

## How to Run

### 1. Wi-Fi 설정

보드의 `/etc/wpa_supplicant.conf`에 AP 정보를 입력합니다.

```conf
network={
    ssid="YOUR_WIFI_SSID"
    psk="YOUR_WIFI_PASSWORD"
}
```

### 2. Static IP script 설치

```bash
cp scripts/S99staticip.sh /etc/init.d/S99staticip
chmod +x /etc/init.d/S99staticip
reboot
```

### 3. IP 할당 확인

보드가 재부팅된 후 `wlan0`에 static IP가 설정되었는지 확인합니다.

```bash
ifconfig wlan0
route -n
cat /etc/resolv.conf
```

### 4. RTSP stream 실행

보드에서 RK-MPI streaming application을 실행합니다.

```bash
./<YOUR_RKMPI_STREAMING_APP>
```

> 실제 실행 파일명과 옵션은 구현 코드 기준으로 수정해야 합니다.

### 5. Client에서 RTSP 수신

VLC 또는 ffplay로 RTSP stream을 확인합니다.

```bash
ffplay rtsp://<BOARD_STATIC_IP>:<PORT>/<STREAM_PATH>
```

예시:

```bash
ffplay rtsp://172.30.1.100:8554/live/0
```

## Demo

### RTSP Streaming Demo

> 아래 링크는 GitHub issue/upload asset 또는 README에 업로드한 demo video URL로 교체하세요.

```text
Demo video: <ADD_DEMO_VIDEO_LINK>
```

추천 demo video 구성:

1. 보드 전원 인가
2. static IP 확인
3. RK-MPI streaming application 실행
4. client에서 RTSP URL 접속
5. 영상 위에 bounding box가 표시되는 장면 확인

### Screenshot

> RTSP client 화면 캡처 이미지를 추가하세요.

```md
![rtsp-demo](./assets/rtsp_demo.jpg)
```

추천 파일 위치:

```text
02_rkmpi_wireless_streaming/
└── assets/
    ├── rtsp_demo.jpg
    └── rtsp_demo.mp4
```

## Performance Metrics

현재 metric은 추가 측정 예정입니다. 아래 표를 기준으로 측정하면 README의 신뢰도가 크게 올라갑니다.

| Metric | Value | How to Measure |
| :--- | :--- | :--- |
| Input resolution | TBD | camera / RK-MPI config |
| Output resolution | TBD | RTSP client or encoder config |
| Stream FPS | TBD | ffplay log, application log |
| End-to-end latency | TBD | 화면 timestamp 비교 또는 slow-motion recording |
| Bitrate | TBD | RTSP client statistics |
| CPU usage | TBD | `top` |
| Memory usage | TBD | `free`, `top`, `/proc/meminfo` |
| NPU usage | TBD | board-specific NPU monitor or application log |
| Reboot stability | TBD | N회 재부팅 후 동일 IP 유지 여부 |

### Recommended Minimum Metrics

README에 최소한 아래 3개는 넣는 것을 추천합니다.

| Metric | Why It Matters |
| :--- | :--- |
| FPS | 실시간성 판단 |
| Resolution | stream 품질 판단 |
| Reboot stability | headless device 운용 안정성 판단 |

## Troubleshooting & Issues

### 1. Problem: DHCP로 인해 보드 IP가 재부팅마다 변경됨

RTSP client는 보드의 IP 주소를 기준으로 stream에 접속합니다. 하지만 DHCP 환경에서는 보드가 재부팅될 때마다 IP가 바뀔 수 있어, 매번 새로운 주소를 확인해야 하는 문제가 발생했습니다.

**Issue**

- 보드 재부팅 후 IP가 변경됨
- RTSP client가 기존 URL로 접속할 수 없음
- headless device 운용성이 떨어짐

**Root Cause**

- DHCP client인 `udhcpc`가 자동으로 IP를 재할당함
- 사용자 script에서 static IP를 설정해도 이후 시스템 daemon이 다시 DHCP 주소를 덮어쓸 수 있음
- 단순히 IP가 생겼는지 확인하는 방식은 DHCP와 충돌할 수 있음

**Solution**

IP 주소 할당 여부가 아니라, `wlan0`의 `RUNNING` flag를 기준으로 Wi-Fi association이 완료됐는지 확인한 뒤 static IP를 주입했습니다.

```sh
if ifconfig wlan0 | grep -q "RUNNING"; then
    ifconfig wlan0 172.30.1.100 netmask 255.255.255.0
    route add default gw 172.30.1.254
    echo "nameserver 8.8.8.8" > /etc/resolv.conf
fi
```

**Result**

- DHCP 의존도를 줄이고 static IP 기반 접근 가능
- RTSP client가 동일 URL로 보드에 접근 가능
- headless wireless device 운용 기반 확보

자세한 과정은 [`troubleshooting.md`](./troubleshooting.md)에 정리되어 있습니다.

### 2. Problem: DHCP client와 custom static IP script의 race condition

초기에는 boot-time script에서 IP를 직접 설정했지만, 이후 `udhcpc`가 다시 IP를 덮어쓰는 문제가 있었습니다.

**Issue**

- boot script에서 static IP 설정
- 일정 시간 후 DHCP 주소로 롤백
- static IP 설정이 안정적으로 유지되지 않음

**Root Cause**

- `udhcpc`가 boot sequence 또는 network daemon에 의해 재실행됨
- init.d 실행 순서 조정만으로는 DHCP client의 재실행을 완전히 제어하기 어려움

**Solution**

- `wpa_supplicant`를 통해 L2 Wi-Fi association을 먼저 확보
- `wlan0 RUNNING` 상태를 확인
- DHCP 주소가 아니라 static IP를 직접 주입
- script를 background로 실행하여 boot blocking을 줄임

**Result**

- boot-time network setup의 안정성 개선
- static IP 설정 타이밍을 L2 association 이후로 조정
- network initialization flow에 대한 이해 확보

### 3. Problem: RTSP stream을 안정적으로 확인하기 위한 evidence 부족

RTSP streaming은 동작 여부를 글로만 설명하면 설득력이 부족합니다. 특히 포트폴리오에서는 실제 영상과 측정값이 있어야 구현 완료 여부를 강하게 증명할 수 있습니다.

**Issue**

- README만으로는 BBOX overlay와 RTSP stream 완료 여부를 확인하기 어려움
- FPS, latency, resolution 등의 metric이 없으면 실시간성 판단이 어려움

**Solution**

- RTSP 수신 화면을 demo video로 업로드
- 최소 metric을 측정해 Performance Metrics 표에 기록
- 실행 명령, RTSP URL, client 환경을 README에 명시

**Result**

- 포트폴리오/README의 신뢰도 향상
- 구현 완료 범위가 명확해짐
- 향후 최적화 기준선 확보

## Evidence to Add

아래 evidence를 추가하면 프로젝트 완성도가 훨씬 높아집니다.

| Evidence | Priority | Description |
| :--- | :--- | :--- |
| RTSP demo video | High | BBOX가 포함된 실시간 stream 수신 화면 |
| RTSP screenshot | High | README에서 바로 확인 가능한 결과 이미지 |
| 실행 명령 | High | 보드에서 streaming app 실행 방법 |
| RTSP URL 형식 | High | client 접속 방법 |
| FPS | Medium | 실시간성 검증 |
| Resolution / bitrate | Medium | stream 품질 검증 |
| CPU / memory usage | Medium | 보드 자원 사용량 검증 |
| Reboot stability test | Medium | static IP 유지 여부 검증 |
| RK-MPI source code | High | 구현 근거 보강 |

## What This Project Demonstrates

이 프로젝트는 Luckfox RV1106 보드를 단순한 inference board가 아니라, 독립적으로 동작하는 wireless Edge AI streaming device로 구성하는 과정을 보여줍니다.

주요 역량은 다음과 같습니다.

- RK-MPI 기반 camera capture pipeline 구성
- RV1106 NPU 기반 on-device inference
- 보드 내부 bounding box overlay
- RTSP 기반 wireless video streaming
- Embedded Linux boot-time network configuration
- DHCP, Wi-Fi association, static IP 설정 문제의 root-cause analysis
- Headless edge device 운용을 위한 네트워크 안정화

## Current Limitations

현재 README에는 demo video, screenshot, metric 값이 아직 placeholder로 남아 있습니다. 실제 포트폴리오 제출 전에는 최소한 RTSP demo video와 screenshot을 추가하는 것을 권장합니다.

또한 RK-MPI streaming source code와 실행 로그가 함께 공개되면, 구현 완료 여부를 GitHub에서 직접 확인할 수 있어 신뢰도가 더 높아집니다.

## Next Improvements

- RTSP demo video 업로드
- RTSP client screenshot 추가
- FPS, latency, resolution, bitrate 측정
- CPU / memory usage 측정
- RK-MPI streaming source code 정리
- 실행 명령과 build 방법 문서화
- N회 재부팅 후 static IP 유지 여부 테스트
- 01 프로젝트의 still-image inference pipeline과 02 프로젝트의 realtime streaming pipeline 관계 정리
