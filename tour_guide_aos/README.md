# tour_guide_aos

`tour_guide` Flask 웹앱을 안드로이드에서 동일 기능으로 사용할 수 있도록 만든 WebView 기반 앱입니다.

## 기능
- 여행 일정(`/`)
- 오디오 가이드(`/audio`)
- 지출 관리(`/expense`)
- 앱 내 뒤로가기, 새로고침, 홈 이동

## 실행 방법
1. 기존 서버 실행
   ```bash
   cd /workspace/tour_guide
   python app.py
   ```
2. Android Studio에서 `tour_guide_aos` 폴더를 열고 실행
3. 에뮬레이터 기준 기본 서버 주소는 `http://10.0.2.2:5000`

## 주소 변경
- `app/build.gradle.kts`의 `BuildConfig.BASE_URL` 값을 수정하면 됩니다.

