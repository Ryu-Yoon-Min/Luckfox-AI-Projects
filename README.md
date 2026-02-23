# Luckfox AI Projects
# 🚀 Luckfox AI Projects (NPU Vision Pipeline)

이 레포지토리는 Rockchip RV1106 NPU (Luckfox Pico Ultra)를 활용한 임베디드 AI 비전 프로젝트들을 단계별로 기록한 통합 저장소입니다.

## 📂 Projects

### [01] RV1106 추론 및 로컬 Mac 시각화 자동화 (`/01_image_inference_mac`)
임베디드 보드의 리소스 한계를 극복하기 위해 **추론(C++)**과 **시각화(Python)**의 역할을 분리하는 이원화된 시스템 아키텍처를 구현했습니다.

* **NPU Inference (보드):** C++ 기반 RKNN API를 이용해 YOLOv5 모델 추론 후 좌표 추출 (`detections.txt`)
* **Automated Pipeline (로컬 Mac):** Shell Script(`run.sh`)를 통한 SSH 데이터 통신 및 Python OpenCV 팝업 자동 렌더링
* **Tech Stack:** C/C++, Python, Bash, RKNN-Toolkit2, OpenCV

![result](https://github.com/user-attachments/assets/6fa12756-8aa4-4e12-89b2-dc933065f12a)
