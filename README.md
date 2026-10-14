# 김해공항 주차장 잔여석 기록 (10/14 ~ 10/30)

GitHub Actions가 매시간 한국공항공사 실시간 주차정보 API를 호출해
김해공항 주차장별 잔여면수를 `data/gimhae_parking.csv`에 쌓고,
10/21·10/28에 최근 7일 그래프, 10/30 밤에 전체 기간 그래프를 `reports/`에 만듭니다.

## 설정 (10분)

1. **저장소 만들기** — github.com → New repository → 이름 예: `gimhae-parking`
   → **Private** 선택 → Create.
2. **파일 올리기** — 압축을 풀고 *Add file → Upload files*로 폴더 안의 모든 파일을 올립니다.
   `.github` 폴더(숨김 폴더)까지 꼭 포함하세요. 안 보이면 탐색기에서 '숨긴 항목 표시'를 켜고
   폴더째 드래그합니다.
3. **서비스키 등록** — 저장소 *Settings → Secrets and variables → Actions → New repository secret*
   - Name: `DATA_GO_KR_KEY`
   - Secret: 공공데이터포털 일반 인증키(Decoding 키 권장)
4. **쓰기 권한 확인** — *Settings → Actions → General → Workflow permissions*에서
   **Read and write permissions** 선택 → Save.
5. **첫 실행 테스트** — *Actions* 탭 → "김해공항 주차 잔여석 수집" → *Run workflow*.
   초록색 체크가 뜨고 `data/gimhae_parking.csv`가 생기면 성공입니다.
   이후로는 매시 7분 무렵 자동 실행됩니다 (GitHub 사정으로 몇 분~십수 분 늦을 수 있음).

## 결과 보기

- 원자료: `data/gimhae_parking.csv` (수집시각, 주차장, 잔여, 전체, 점유)
- 그래프: `reports/YYYYMMDD_YYYYMMDD.png`, 요약표 `..._summary.csv`
- 원하는 때 그래프를 다시 그리려면 *Actions → 주간 잔여석 리포트 → Run workflow*
  (전체 기간은 체크박스 선택)

## 문제가 생기면

- 수집이 빨간 X로 실패 → 실행 로그의 마지막 메시지를 확인하세요.
  - `SERVICE_KEY_IS_NOT_REGISTERED` 등: 키 등록 직후엔 반영에 1~2시간 걸릴 수 있습니다. Encoding/Decoding 키를 바꿔 등록해 보세요.
  - "김해공항 주차장 항목을 찾지 못했습니다": `data/raw/`에 원본 응답이 남아 있으니 그 파일을 보여주시면 필드 매핑을 맞춰드릴 수 있습니다.
- 10/30 23:59 이후엔 수집 스크립트가 자동으로 아무것도 하지 않습니다.
  깔끔하게 끄려면 *Actions → 워크플로 → ··· → Disable workflow*.
