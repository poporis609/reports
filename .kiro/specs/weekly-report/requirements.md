# Requirements Document

## Introduction

주간 리포트 시스템은 사용자가 일주일 동안 작성한 일기를 분석하여 감정 상태, 생활 패턴, 그리고 개선 방안을 제공하는 기능입니다. AWS Bedrock을 활용한 AI 분석을 통해 사용자의 일주일 동안의 감정 변화를 추적하고, 긍정적/부정적 패턴을 식별하여 맞춤형 피드백을 제공합니다.

## Glossary

- **Weekly_Report_System**: 일주일 단위로 일기를 분석하고 리포트를 생성하는 시스템
- **Diary_Entry**: 사용자가 작성한 개별 일기 항목
- **Sentiment_Score**: 일기 내용을 분석하여 산출된 감정 점수 (1-10점 척도)
- **User**: Cognito로 인증된 사용자 (sub 값으로 식별)
- **Bedrock_Flow**: AWS Bedrock의 AI 분석 플로우 (report-assistant-flow)
- **Analysis_Period**: 분석 대상 기간 (일주일, 예: 12일~18일)
- **Pattern**: 사용자의 행동, 경험, 날씨 등과 감정 점수 간의 상관관계
- **Feedback**: AI가 생성한 개선 방안 또는 긍정적 패턴 강화 제안

## Requirements

### Requirement 1: 사용자 일기 데이터 수집

**User Story:** As a system, I want to collect user diary entries for a specific week, so that I can analyze emotional patterns over time.

#### Acceptance Criteria

1. WHEN a weekly report is requested, THE Weekly_Report_System SHALL retrieve all Diary_Entry records for the specified User within the Analysis_Period
2. WHEN retrieving diary entries, THE Weekly_Report_System SHALL identify the User by their Cognito sub value
3. WHEN the Analysis_Period is not specified, THE Weekly_Report_System SHALL default to the most recent complete week (Monday to Sunday)
4. WHEN a User has no diary entries for the Analysis_Period, THE Weekly_Report_System SHALL return an error indicating insufficient data
5. THE Weekly_Report_System SHALL retrieve the User's preferred_username from Cognito user attributes

### Requirement 2: AI 감정 분석 수행

**User Story:** As a user, I want my diary entries to be analyzed by AI, so that I can understand my emotional patterns throughout the week.

#### Acceptance Criteria

1. WHEN diary entries are collected, THE Weekly_Report_System SHALL send them to the Bedrock_Flow for sentiment analysis
2. THE Weekly_Report_System SHALL use the Bedrock Flow ID "BZKT7TJGPT" and Alias ID "QENFHYZ1KE"
3. WHEN sending data to Bedrock_Flow, THE Weekly_Report_System SHALL format each Diary_Entry as a document containing diary content, creation date, and author nickname
4. WHEN Bedrock_Flow completes analysis, THE Weekly_Report_System SHALL receive a Sentiment_Score for each day (1-10 scale)
5. THE Weekly_Report_System SHALL associate each Sentiment_Score with the corresponding date and diary content

### Requirement 3: 감정 점수 기반 평가 생성

**User Story:** As a user, I want to receive an evaluation of my week based on my emotional scores, so that I can understand my overall well-being.

#### Acceptance Criteria

1. WHEN all Sentiment_Score values are calculated, THE Weekly_Report_System SHALL compute the average score for the week
2. WHEN the average Sentiment_Score is below 5, THE Weekly_Report_System SHALL generate a negative evaluation with improvement suggestions
3. WHEN the average Sentiment_Score is 5 or above, THE Weekly_Report_System SHALL generate a positive evaluation highlighting successful patterns
4. THE Weekly_Report_System SHALL identify correlations between activities, experiences, weather conditions and Sentiment_Score values
5. THE Weekly_Report_System SHALL include specific examples from diary entries to support the evaluation

### Requirement 4: 부정적 패턴 분석 및 피드백

**User Story:** As a user with low emotional scores, I want to understand what factors contributed to negative feelings, so that I can make improvements.

#### Acceptance Criteria

1. WHEN the average Sentiment_Score is below 5, THE Weekly_Report_System SHALL identify days with the lowest scores
2. THE Weekly_Report_System SHALL extract common themes from low-scoring diary entries (activities, experiences, weather)
3. THE Weekly_Report_System SHALL generate actionable Feedback for improving emotional well-being
4. THE Feedback SHALL reference specific diary entries and dates to provide context
5. THE Weekly_Report_System SHALL prioritize the most impactful negative patterns in the Feedback

### Requirement 5: 긍정적 패턴 분석 및 강화

**User Story:** As a user with high emotional scores, I want to understand what factors contributed to positive feelings, so that I can reinforce those behaviors.

#### Acceptance Criteria

1. WHEN the average Sentiment_Score is 5 or above, THE Weekly_Report_System SHALL identify days with the highest scores
2. THE Weekly_Report_System SHALL extract common themes from high-scoring diary entries (activities, experiences, weather)
3. THE Weekly_Report_System SHALL generate Feedback encouraging continuation of positive patterns
4. THE Feedback SHALL reference specific diary entries and dates to provide context
5. THE Weekly_Report_System SHALL highlight the most impactful positive patterns in the Feedback

### Requirement 6: 리포트 생성 API 엔드포인트

**User Story:** As a client application, I want to request weekly report generation via API, so that users can access their analysis.

#### Acceptance Criteria

1. THE Weekly_Report_System SHALL expose an endpoint at "POST /report/create" for report generation
2. WHEN a request is received at "/report/create", THE Weekly_Report_System SHALL authenticate the User via Cognito
3. THE Weekly_Report_System SHALL accept optional parameters for Analysis_Period start and end dates
4. WHEN report generation is successful, THE Weekly_Report_System SHALL return HTTP 200 with the complete report
5. WHEN report generation fails, THE Weekly_Report_System SHALL return appropriate HTTP error codes (400, 401, 500) with error messages

### Requirement 7: 리포트 요약 조회 API 엔드포인트

**User Story:** As a user, I want to retrieve a summary of my weekly report by nickname, so that I can quickly review my analysis.

#### Acceptance Criteria

1. THE Weekly_Report_System SHALL expose an endpoint at "GET /report/create/{nickname}" for retrieving report summaries
2. WHEN a request is received with a nickname, THE Weekly_Report_System SHALL retrieve the User's preferred_username from Cognito
3. THE Weekly_Report_System SHALL return the most recent weekly report for the specified User
4. THE report summary SHALL include diary content, current date, and author nickname
5. WHEN no report exists for the User, THE Weekly_Report_System SHALL return HTTP 404 with an appropriate message

### Requirement 8: MSA 아키텍처 통합

**User Story:** As a system architect, I want the weekly report service to integrate with existing MSA infrastructure, so that it operates seamlessly with other services.

#### Acceptance Criteria

1. THE Weekly_Report_System SHALL be deployed as an independent microservice in the MSA architecture
2. THE Weekly_Report_System SHALL communicate with other services via the Application Load Balancer (ALB)
3. THE Weekly_Report_System SHALL be accessible through the domain "api.aws11.shop"
4. THE Weekly_Report_System SHALL include Kubernetes ingress configuration for routing
5. THE Weekly_Report_System SHALL include CI/CD workflow configuration (deployment.yaml) for automated deployment

### Requirement 9: 데이터 보안 및 프라이버시

**User Story:** As a user, I want my diary data to be handled securely, so that my personal information remains private.

#### Acceptance Criteria

1. THE Weekly_Report_System SHALL only access diary entries belonging to the authenticated User
2. THE Weekly_Report_System SHALL transmit data to Bedrock_Flow over encrypted connections
3. THE Weekly_Report_System SHALL not store raw diary content in logs or temporary storage
4. WHEN authentication fails, THE Weekly_Report_System SHALL reject the request and return HTTP 401
5. THE Weekly_Report_System SHALL validate User authorization before retrieving Cognito user attributes

### Requirement 10: 자동 주간 분석 스케줄링

**User Story:** As a user, I want my weekly diary analysis to be automatically generated every Sunday at midnight, so that I receive timely insights without manual intervention.

#### Acceptance Criteria

1. THE Weekly_Report_System SHALL trigger automatic report generation every Sunday at 00:00 (midnight)
2. WHEN Sunday midnight arrives, THE Weekly_Report_System SHALL identify all Users who have at least one Diary_Entry from the previous week (Monday-Sunday)
3. THE Weekly_Report_System SHALL generate a weekly report for each eligible User automatically
4. THE Weekly_Report_System SHALL use AWS Lambda for scheduled execution of the weekly analysis
5. WHEN automatic report generation fails for a User, THE Weekly_Report_System SHALL log the error and continue processing other Users

### Requirement 11: 이메일 알림 발송

**User Story:** As a user, I want to receive an email notification when my weekly analysis is complete, so that I am informed about my emotional insights.

#### Acceptance Criteria

1. WHEN a weekly report is successfully generated, THE Weekly_Report_System SHALL send an email notification to the User
2. THE Weekly_Report_System SHALL retrieve the User's email address from Cognito user attributes
3. THE Weekly_Report_System SHALL use AWS SES (Simple Email Service) for sending email notifications
4. THE email SHALL include a summary of the weekly analysis and a link to view the full report
5. WHEN email delivery fails, THE Weekly_Report_System SHALL log the error but SHALL NOT fail the report generation process

### Requirement 12: 에러 처리 및 복원력

**User Story:** As a system operator, I want the service to handle errors gracefully, so that users receive meaningful feedback when issues occur.

#### Acceptance Criteria

1. WHEN Bedrock_Flow is unavailable, THE Weekly_Report_System SHALL return HTTP 503 with a retry-after header
2. WHEN diary data retrieval fails, THE Weekly_Report_System SHALL log the error and return HTTP 500 with a generic error message
3. WHEN Cognito authentication fails, THE Weekly_Report_System SHALL return HTTP 401 with authentication guidance
4. THE Weekly_Report_System SHALL implement timeout handling for Bedrock_Flow requests (maximum 30 seconds)
5. WHEN partial data is available, THE Weekly_Report_System SHALL generate a report with a warning about incomplete data
