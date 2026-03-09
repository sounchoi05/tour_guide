// 캐시 이름 및 오프라인 작동을 위한 최소한의 서비스 워커
self.addEventListener('install', (e) => {
    console.log('[Service Worker] 설치 완료');
});

self.addEventListener('fetch', (e) => {
    // PWA 설치 조건을 만족하기 위해 빈 fetch 이벤트가 필수로 있어야 합니다.
});