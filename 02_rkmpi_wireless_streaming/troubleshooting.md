# Trouble Shooting

## Network Connecting Problem(WLAN)
[1] uDHCPc Problem

### Trouble Shooting Flow

#### [Phase 1] Simple Application Script & Race Condition
* **시도:** `/etc/init.d/S99staticip` 스크립트를 생성하여 부팅 시 IP 수동 할당.
* **증상:** 재부팅 시 IP가 다시 공유기 할당 주소(`.23`)로 회귀함.
* **분석:** 백그라운드에서 실행되는 `udhcpc`(DHCP 클라이언트)가 사용자 설정을 무시하고 주소를 다시 덮어쓰는 **Race Condition(경쟁 상태)** 발생 확인.

#### [Phase 2] Process Kill & Asynchronous Optimization
* **전략:** IP가 할당될 때까지 Polling, `killall -9 udhcpc`로 방해 요소를 제거, 고정 IP를 주입하는 로직 구현.
* **최적화:** 네트워크 안정화 대기 시간 동안 부팅 시퀀스가 멈추는 것을 방지하기 위해 함수를 **Background(`&`)**로 실행하여 부팅 속도 보호.
* **한계:** 특정 시점에 인터페이스가 재시작되며 주소가 롤백됨. `udhcpc` 프로세스를 죽여도 시스템 데몬에 의해 즉시 재실행(Respawn)되는 끈질긴 간섭 확인.

#### [Phase 3] Root Cause Discovery
* **분석:** `grep -rn "udhcpc" /etc/init.d/`를 통해 부팅시 `udhcpc`를 소환하는 근본 스크립트 추적.
* **발견:** `/etc/init.d/S99hciinit` 스크립트가 인터페이스 활성화와 동시에 DHCP 요청을 강제하고 있음을 식별. 커스텀 스크립트와 동일한 우선순위(`S99`)에서 발생하는 시스템 레이어의 충돌임을 확신.

#### [Phase 4] Execution Priority Adjustment (Init.d Sequence)
* **시도:** 기본 스크립트를 S90hciinit으로 앞당기고, 커스텀 스크립트는 S99staticip로 유지함. 시스템이 먼저 Wi-Fi를 초기화, 마지막에 고정 IP 스크립트가 실행되어 주도권을 뺏어오는 전략 시도.
* **한계:** 여전히 .23으로 IP가 덮어씌워지거나 설정 자체가 실패함.
* **분석:** init.d의 실행 순서를 조작하더라도, **Rockchip 전용 네트워크 데몬(rkwifi_server 등 컴파일된 바이너리)**이 부팅 이후에도 L2 이벤트를 실시간 감시하며 udhcpc를 강제 호출함. 텍스트 스크립트 수정만으로는 하드코딩된 '상시 감시 및 자동 복구 메커니즘'을 막을 수 없음을 깨달음.

#### [Phase 5] Strategy Shift: L2 vs L3
* **문제점:** DHCP 기능을 원천 차단하기 위해 바이너리를 `udhcpc_backup`으로 Renaming하자, 기존 커스텀 스크립트(`S99staticip`) 내의 "IP 주소(`inet`)가 할당되기를 기다리는" 로직이 조건을 충족하지 못해 무한 대기에 빠지는 논리적 모순 발생.
* **기술적 통찰:** IP 주소 할당(L3 Network Layer) 과정이 없더라도, `wpa_supplicant` 데몬을 통한 와이파이 인증 및 연결(L2 Data Link Layer)이 완료되면 인터페이스에 `RUNNING` 플래그가 활성화된다는 점에 착안.
* **최종 해결:** 1. **바이너리 무력화:** `udhcpc`의 이름을 변경하여 시스템의 자동 DHCP 요청 수단 자체를 물리적으로 제거.
  2. **로직 개선:** IP 존재 여부가 아닌 L2 인터페이스의 **`RUNNING`(연결 신호)** 상태를 감지하여 즉시 고정 IP를 주입하는 방식으로 스크립트 고도화.
---

### Key Achievements
* **인프라 확정:** 시스템의 자동 복구 메커니즘과 충돌 없이 타겟 주소 고정 성공.
* **성능 및 안정성:** 비동기 설계를 통해 부팅 지연 시간 0초 달성 및 외부 환경(DHCP 서버) 의존성 완벽 제거.
* **역량 증명:** 단순 쉘 스크립팅을 넘어 **OS 초기화 시퀀스, 프로세스 생명주기, 네트워크 레이어(L2/L3)** 전반을 관통하는 임베디드 인프라 제어 역량 확보.