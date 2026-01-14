# 주간 리포트 API 명세서

## Base URL
```
https://api.aws11.shop
```

## 인증
Cognito JWT 토큰을 `Authorization` 헤더에 Bearer 형식으로 전달합니다.

```
Authorization: Bearer <access_token>
```

---

## 엔드포인트

### 1. 헬스 체크
서비스 상태를 확인합니다.

**Request**
```
GET /report/health
```

**Response** `200 OK`
```json
{
  "status": "healthy",
  "service": "weekly-report"
}
```

---

### 2. 주간 리포트 생성
인증된 사용자의 일기를 분석하여 주간 리포트를 생성합니다.

**Request**
```
POST /report/create
Authorization: Bearer <access_token>
Content-Type: application/json
```

**Request Body** (선택)
```json
{
  "start_date": "2026-01-06",
  "end_date": "2026-01-12"
}
```
- `start_date`, `end_date`: 분석 기간 (생략 시 지난 주 월~일 자동 계산)

**Response** `200 OK`
```json
{
  "report_id": 1,
  "user_id": "44681408-c0b1-70f3-2d06-2a725f290f8b",
  "nickname": "poporis609@gmail.com",
  "week_period": {
    "start": "2026-01-06",
    "end": "2026-01-12"
  },
  "average_score": 6.5,
  "evaluation": "positive",
  "daily_analysis": [
    {
      "date": "2026-01-06",
      "score": 7.0,
      "sentiment": "행복",
      "diary_content": "오늘 좋은 일이 있었다...",
      "key_themes": ["운동", "친구"]
    }
  ],
  "patterns": [
    {
      "type": "activity",
      "value": "운동",
      "correlation": "positive",
      "frequency": 3,
      "average_score": 7.5
    }
  ],
  "feedback": [
    "2026-01-06에 감정 점수가 7.0점으로 높았습니다. 이 날의 긍정적인 경험을 기억하세요.",
    "운동 활동이 3회 있었고, 평균 점수가 7.5점으로 높았습니다. 이 활동을 계속 유지하세요.",
    "이번 주는 전반적으로 긍정적인 한 주였습니다. 좋은 습관을 계속 유지하세요!"
  ],
  "has_partial_data": false,
  "created_at": "2026-01-14T10:30:00"
}
```

**Error Responses**
| 상태 코드 | 설명 |
|----------|------|
| 400 | 분석 기간에 일기가 없음 |
| 401 | 인증 실패 (토큰 없음/만료) |
| 503 | AI 분석 서비스 일시 불가 |
| 504 | AI 분석 타임아웃 |

---

### 3. 닉네임으로 리포트 조회
닉네임으로 가장 최근 리포트 요약을 조회합니다. (인증 불필요)

**Request**
```
GET /report/create/{nickname}
```

**Path Parameters**
- `nickname`: Cognito preferred_username (예: `poporis609@gmail.com`)

**Response** `200 OK`
```json
{
  "report_id": 1,
  "nickname": "poporis609@gmail.com",
  "created_at": "2026-01-14T10:30:00",
  "summary": {
    "diary_content": ["오늘 좋은 일이...", "비가 와서..."],
    "current_date": "2026-01-14T15:00:00",
    "author_nickname": "poporis609@gmail.com",
    "average_score": 6.5,
    "evaluation": "positive",
    "week_period": {
      "start": "2026-01-06",
      "end": "2026-01-12"
    }
  }
}
```

**Error Responses**
| 상태 코드 | 설명 |
|----------|------|
| 404 | 사용자 또는 리포트를 찾을 수 없음 |

---

### 4. 리포트 상세 조회
리포트 ID로 상세 정보를 조회합니다. (본인 리포트만 조회 가능)

**Request**
```
GET /report/{report_id}
Authorization: Bearer <access_token>
```

**Path Parameters**
- `report_id`: 리포트 ID (정수)

**Response** `200 OK`
```json
{
  "id": 1,
  "user_id": "44681408-c0b1-70f3-2d06-2a725f290f8b",
  "nickname": "poporis609@gmail.com",
  "week_start": "2026-01-06",
  "week_end": "2026-01-12",
  "average_score": 6.5,
  "evaluation": "positive",
  "daily_analysis": [...],
  "patterns": [...],
  "feedback": ["...", "..."],
  "created_at": "2026-01-14T10:30:00"
}
```

**Error Responses**
| 상태 코드 | 설명 |
|----------|------|
| 401 | 인증 실패 |
| 403 | 다른 사용자의 리포트 접근 시도 |
| 404 | 리포트를 찾을 수 없음 |

---

### 5. 내 리포트 목록 조회
인증된 사용자의 리포트 목록을 조회합니다.

**Request**
```
GET /report/?limit=10
Authorization: Bearer <access_token>
```

**Query Parameters**
- `limit`: 조회할 개수 (기본값: 10)

**Response** `200 OK`
```json
{
  "reports": [
    {
      "id": 2,
      "user_id": "44681408-c0b1-70f3-2d06-2a725f290f8b",
      "nickname": "poporis609@gmail.com",
      "week_start": "2026-01-06",
      "week_end": "2026-01-12",
      "average_score": 6.5,
      "evaluation": "positive",
      "daily_analysis": [...],
      "patterns": [...],
      "feedback": ["...", "..."],
      "created_at": "2026-01-14T10:30:00"
    }
  ],
  "total": 1
}
```

---

## 데이터 타입

### Evaluation (평가 유형)
| 값 | 설명 |
|----|------|
| `positive` | 평균 점수 5.0 이상 (긍정적) |
| `negative` | 평균 점수 5.0 미만 (부정적) |

### DailyAnalysis (일일 분석)
```typescript
interface DailyAnalysis {
  date: string;           // YYYY-MM-DD
  score: number;          // 1-10 감정 점수
  sentiment: string;      // 주요 감정 (행복, 슬픔, 불안 등)
  diary_content: string;  // 일기 내용 요약
  key_themes: string[];   // 주요 테마 (활동, 날씨 등)
}
```

### Pattern (패턴)
```typescript
interface Pattern {
  type: string;           // 패턴 유형 (activity | experience | weather)
  value: string;          // 패턴 값 (운동, 날씨, 친구 등)
  correlation: string;    // positive | negative
  frequency: number;      // 발생 빈도
  average_score: number;  // 해당 패턴 발생 시 평균 점수
}
```

---

## Cognito 설정

프론트엔드에서 Cognito 연동 시 필요한 정보:

| 항목 | 값 |
|------|-----|
| User Pool ID | `[AWS Secrets Manager에서 관리]` |
| Client ID | `[AWS Secrets Manager에서 관리]` |
| Region | `us-east-1` |

### 토큰 사용 예시 (JavaScript)
```javascript
// Amplify 사용 시
import { Auth } from 'aws-amplify';

const session = await Auth.currentSession();
const token = session.getAccessToken().getJwtToken();

// API 호출
const response = await fetch('https://api.aws11.shop/report/create', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    start_date: '2026-01-06',
    end_date: '2026-01-12'
  })
});
```

---

## 에러 응답 형식

모든 에러는 다음 형식으로 반환됩니다:

```json
{
  "detail": "에러 메시지"
}
```

| 상태 코드 | 설명 |
|----------|------|
| 400 | 잘못된 요청 (날짜 형식 오류, 데이터 없음 등) |
| 401 | 인증 실패 |
| 403 | 권한 없음 |
| 404 | 리소스를 찾을 수 없음 |
| 500 | 서버 내부 오류 |
| 503 | 서비스 일시 불가 (Retry-After 헤더 포함) |
| 504 | 게이트웨이 타임아웃 |
