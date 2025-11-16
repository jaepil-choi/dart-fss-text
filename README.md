# dart-fss-text

**한국 DART 사업보고서의 텍스트 데이터 추출 및 구조화 라이브러리**

`dart-fss-text`는 한국 금융감독원 전자공시시스템(DART)의 사업보고서에서 **텍스트 정보를 추출**하고 구조화하여 제공하는 Python 라이브러리입니다. [dart-fss](https://github.com/josw123/dart-fss)가 재무제표의 숫자 데이터를 제공하는 것과 달리, 본 라이브러리는 사업보고서의 **서술형 텍스트 내용**을 목차별로 정확하게 추출하여 NLP, 텍스트 분석, 정량 연구에 활용할 수 있도록 합니다.

**핵심 기능:**

- 🎯 **목차별 텍스트 추출**: 사업보고서의 각 섹션(예: "사업의 내용", "재무에 관한 사항" 등)을 정확하게 식별하고 추출
- 🤖 **고정밀 파싱**: XML 파싱, 정규식, fuzzy 매칭을 결합하여 목차 추출 정확도 극대화
- 💾 **MongoDB 연동**: 추출된 텍스트를 MongoDB에 자동 저장하여 대규모 데이터 관리 용이
- 📊 **다양한 분석 지원**: 단일 기업 조회, 횡단면 분석, 시계열 분석, 패널 데이터 구축
- 🏢 **상장 기업 전체 지원**: KOSPI, KOSDAQ, KONEX 상장 주식 전체 커버
- 🚀 **완전 자동화**: 검색 → 다운로드 → 파싱 → 저장 → 조회까지 원스톱 파이프라인

---

## 빠른 데모

**15줄 미만의 코드로 모든 상장사 사업보고서를 자동 수집하고 조회하기:**

```python
from dart_fss_text import StorageService, DisclosurePipeline, TextQuery

# 1. MongoDB 연결
storage = StorageService()

# 2. 모든 상장사의 보고서 다운로드, 파싱, 저장 (자동화)
pipeline = DisclosurePipeline(storage_service=storage)
stats = pipeline.download_and_parse(
    stock_codes="all",  # "all"이면 전체 상장사 자동 조회 (기본값)
    years=[2023, 2024],
    report_type="A001"  # 사업보고서 (연간) --> config/types.yaml 참조
)
# → 이미 다운로드된 XML이 있으면 자동으로 파싱하여 MongoDB에 추가
# → MongoDB에 이미 있는 데이터는 건너뛰기 (skip_existing=True가 기본값)

print(f"✓ {stats['reports']}개 보고서에서 {stats['sections']}개 섹션 저장 완료")

# 3. 파싱된 텍스트 조회
query = TextQuery(storage_service=storage)
result = query.get(
    stock_codes=["005930", "000660"],  # 특정 기업만 조회
    years=[2023, 2024],
    section_codes="020000"  # II. 사업의 내용 --> config/toc.yaml 참조
) # --> result: dictionary

# result 예시:
# {
#     "2023": {
#         "005930": Sequence객체,
#         "000660": Sequence객체,
#     }, 
#     "2024": { ... }
# }

# 4. 구조화된 데이터 접근
sequence = result["2024"]["005930"]
sequence.text
# 들어있는 SectionDocument (사업보고서 각 섹션의 텍스트)를 모두 붙여서 전체 텍스트를 반환

# > 당사는 본사를 거점으로 한국과 DX 부문 산하 해외 9개 지역총괄 및 DS 부문 산하 해외 5개 지역총괄의 생산ㆍ판매법인, SDC 및 Harman 산하 종속기업 등 232개의 종속기업으로 구성된 글로벌 전자 기업입니다...
```

---

## 설치

```bash
# PyPI 릴리스 시 설치 방법이 추가될 예정입니다
# 현재는 로컬에서 클론하여 설치:
git clone https://github.com/your-org/dart-fss-text.git
cd dart-fss-text
poetry install
```

### 환경 설정

라이브러리 사용을 위해 `.env` 파일을 생성해야 합니다. `.env.example` 파일을 참고하여 작성하세요:

```bash
# DART API 키 (필수) - https://opendart.fss.or.kr/ 에서 발급
OPENDART_API_KEY=your_api_key_here

# MongoDB 설정
MONGO_HOST=localhost:27017
DB_NAME=FS
COLLECTION_NAME=A001
```

**참고**: MongoDB가 로컬 또는 원격 서버에서 실행 중이어야 합니다.

---

## 주요 기능

### 📥 자동화된 데이터 파이프라인

- **전체 상장사 지원**: `stock_codes="all"`로 KOSPI/KOSDAQ/KONEX 전체 상장사 자동 수집
- **공시 검색**: 회사, 연도, 보고서 유형별 DART API 검색
- **문서 다운로드**: 자동 ZIP 다운로드 및 XML 추출
- **XML 파싱**: 계층 구조 재구성과 함께 섹션 추출
- **MongoDB 저장**: 최적화된 스키마로 영구 저장
- **자동 백필**: 이미 다운로드된 XML이 있으면 자동으로 파싱하여 MongoDB에 추가
- **중복 방지**: MongoDB에 이미 있는 데이터는 건너뛰기 (`skip_existing=True` 기본값)
- **텍스트 추출**: 표가 텍스트로 평탄화된 깨끗한 텍스트 (MVP)

### 🔍 유연한 쿼리 인터페이스

- **단일 조회**: 특정 회사/연도의 특정 섹션 가져오기
- **횡단면 분석**: 여러 회사의 섹션 비교
- **시계열 분석**: 한 회사의 공시 변화 추적
- **패널 데이터**: 계량경제 모델을 위한 다중 회사, 다중 연도 분석

### 🛡️ 프로덕션 준비 완료

- **탄력적 파싱**: 오래된 보고서를 위한 UTF-8/EUC-KR 인코딩 폴백
- **텍스트 기반 매칭**: XML 속성과 무관하게 작동 (2010-2024)
- **빠른 실패 오류**: 인증 및 유효성 검사 문제에 대한 명확한 오류 메시지
- **Config Facade**: 중앙집중식 설정 관리
- **의존성 주입**: 명시적 데이터베이스 제어를 통한 테스트 가능한 설계

---

## 데이터 모델

**SectionDocument** (MongoDB 스키마):
```python
{
    "document_id": "20240312000736_020000",    # {rcept_no}_{section_code}
    "rcept_no": "20240312000736",              # 공시 접수번호
    "stock_code": "005930",                     # 회사 종목코드
    "corp_name": "삼성전자",                     # 회사명
    "year": "2024",                             # 공시 연도
    "section_code": "020000",                   # 섹션 코드
    "section_title": "II. 사업의 내용",         # 섹션 제목
    "level": 1,                                 # 계층 수준
    "section_path": ["020000"],                 # 계층 경로
    "text": "당사는 본사를 거점으로...",          # 전체 텍스트 내용
    "char_count": 38037,                        # 통계
    "word_count": 7979,
    "parsed_at": "2024-03-15T10:30:00Z",
    "parser_version": "1.0.0"
}
```

**Sequence** (컬렉션 클래스):
```python
sequence = Sequence([doc1, doc2, doc3])

# 메타데이터 접근
sequence.corp_name      # "삼성전자"
sequence.year           # "2024"
sequence.section_count  # 3

# 섹션 접근
sequence[0]             # 첫 번째 섹션 → SectionDocument
sequence["020100"]      # 코드로 → SectionDocument
sequence[1:3]           # 슬라이스 → Sequence

# 병합된 텍스트
sequence.text           # 모든 섹션을 \n\n로 병합
sequence.total_word_count  # 단어 수 합계
```

---

## 사용 예제

### 예제 0: 전체 상장사 데이터 수집

```python
from dart_fss_text import StorageService, DisclosurePipeline

pipeline = DisclosurePipeline(storage_service=StorageService())

# 모든 상장사의 2024년 사업보고서 자동 수집 (2,900+ 기업)
stats = pipeline.download_and_parse(
    stock_codes="all",  # 기본값: 전체 상장사
    years=2024
)

# 자동으로: 1) 전체 상장사 조회, 2) 기존 XML 백필, 3) 중복 건너뛰기
# 실패한 기업은 data/failures/failures_2024.csv에 저장
```

### 예제 1: 단일 회사, 단일 연도

```python
from dart_fss_text import StorageService, TextQuery

storage = StorageService()
query = TextQuery(storage_service=storage)

result = query.get(
    stock_codes="005930",
    years=2024,
    section_codes="020100"  # 사업의 개요
)

samsung = result["2024"]["005930"]
print(f"{samsung.corp_name}: {samsung.text[:500]}...")
```

### 예제 2: 횡단면 분석

```python
# 반도체 회사들의 사업 설명 비교
result = query.get(
    stock_codes=["005930", "000660", "005380"],  # 삼성전자, SK하이닉스, 현대차
    years=2024,
    section_codes="020100"
)

for stock_code, seq in result["2024"].items():
    print(f"{seq.corp_name}: {seq.total_char_count:,} 자")
    
# 출력:
# 삼성전자: 40,656 자
# SK하이닉스: 43,139 자
# 현대차: 38,245 자
```

### 예제 3: 시계열 분석

```python
# 삼성전자의 사업 설명 5년간 변화 추적
result = query.get(
    stock_codes="005930",
    start_year=2020,
    end_year=2024,
    section_codes="020100"
)

for year in sorted(result.keys()):
    seq = result[year]["005930"]
    print(f"{year}: {seq.total_word_count:,} 단어")

# 출력:
# 2020: 7,243 단어
# 2021: 7,521 단어
# 2022: 7,832 단어
# 2023: 7,979 단어
# 2024: 8,496 단어
```

### 예제 4: 연구용 패널 데이터

```python
# 다중 회사, 다중 연도 데이터셋
result = query.get(
    stock_codes=["005930", "000660", "005380"],
    start_year=2020,
    end_year=2024,
    section_codes="020000"  # 하위 섹션을 포함한 상위 섹션
)

# pandas DataFrame으로 변환
import pandas as pd

panel_data = []
for year, firms in result.items():
    for stock_code, seq in firms.items():
        for doc in seq:  # SectionDocument 객체 순회
            panel_data.append({
                'year': year,
                'stock_code': stock_code,
                'corp_name': seq.corp_name,
                'section_code': doc.section_code,
                'section_title': doc.section_title,
                'text': doc.text,
                'word_count': doc.word_count,
            })

df = pd.DataFrame(panel_data)
print(df.shape)  # (75, 7) - 3개 회사 × 5년 × 5개 섹션
```

### 예제 5: NLP 통합

```python
from sentence_transformers import SentenceTransformer

# 임베딩 모델 로드
model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')

# 사업 설명 가져오기
result = query.get(
    stock_codes="005930",
    start_year=2020,
    end_year=2024,
    section_codes="020100"
)

# 의미적 유사도를 위한 임베딩 생성
embeddings = {}
for year, firms in result.items():
    text = firms["005930"].text
    embeddings[year] = model.encode(text)

# 2024년과 2020년 비교
from sklearn.metrics.pairwise import cosine_similarity
similarity = cosine_similarity([embeddings["2024"]], [embeddings["2020"]])
print(f"의미적 유사도 (2024 vs 2020): {similarity[0][0]:.3f}")
```

### 예제 6: 백필 서비스 (수동 백필이 필요한 경우)

```python
from dart_fss_text import BackfillService, StorageService

# 이미 다운로드된 XML을 MongoDB로 수동 백필
# (주의: DisclosurePipeline이 자동으로 백필하므로 일반적으로 불필요)
backfill = BackfillService(StorageService())
stats = backfill.backfill_from_directory("data", force=True)  # force=True로 재파싱
```

---

## 한계점

본 라이브러리는 MVP(Minimum Viable Product) 단계로, 다음과 같은 한계점이 있습니다:

### 1. 데이터 기간 제약 (2010년 이후만 지원)

**DART의 XML 형식 공시 데이터는 2010년부터 제공됩니다.** 2009년 이전 데이터는 XML 형식으로 제공되지 않아 본 라이브러리로 추출할 수 없습니다. 과거 데이터가 필요한 경우 PDF 파싱 등 별도의 접근 방법이 필요합니다.

### 2. 공시 형식의 불일치

DART 공시 문서는 기업과 연도에 따라 형식이 완벽히 통일되어 있지 않습니다. 본 라이브러리는 XML 파싱, 정규식, fuzzy 매칭을 결합하여 높은 정확도로 섹션을 추출하지만, 일부 문서에서는 특정 섹션이 누락되거나 구조가 다를 수 있습니다.

### 3. 보고서 개정판 처리

기업이 동일 회계연도에 대해 정정 공시(기재정정)를 제출하는 경우, **본 라이브러리는 가장 최신 버전만 반환합니다.** Forward-looking bias를 피하기 위해서는 모든 버전을 저장하고 원본 공시를 조회할 수 있어야 하지만, MVP 단계에서는 최신 버전만 지원합니다. 대부분의 연구 목적(특히 "사업의 내용" 섹션)에서는 최신 버전으로 충분합니다.

---

## 요구사항

### 시스템 요구사항
- **Python**: ≥ 3.12, < 3.13
- **MongoDB**: ≥ 4.0 (로컬 또는 Atlas)
- **DART API 키**: [DART OPEN API](https://opendart.fss.or.kr/)에서 발급받아야 함

### Python 라이브러리 의존성
- `dart-fss` (≥ 0.4.14) - DART API 연동
- `pymongo` (≥ 4.15.2) - MongoDB 데이터베이스 연결
- `lxml` (≥ 6.0.2) - XML 파싱
- `pydantic` (≥ 2.11.9) - 데이터 검증 및 모델링
- `pydantic-settings` (≥ 2.11.0) - 설정 관리
- `pyyaml` (≥ 6.0.3) - YAML 파일 처리
- `python-dotenv` (≥ 1.1.1) - 환경 변수 관리
- `pytest` (≥ 8.4.2) - 테스트 프레임워크

모든 의존성은 Poetry를 통해 자동으로 설치됩니다 (`pyproject.toml` 참조).

---

## 개발

### 테스트 실행

```bash
poetry install
poetry run pytest
```

### 쇼케이스 스크립트 실행

```bash
# 샘플 데이터 데모
poetry run python showcase/showcase_01_text_query.py

# 실제 DART 데이터 통합
poetry run python showcase/showcase_02_live_data_query.py

# 고수준 API 데모
poetry run python showcase/showcase_03_disclosure_pipeline.py
```

---

## 문서

이 라이브러리는 아래와 같이 문서로 스펙을 정의하여 AI 바이브 코딩으로 대부분의 코드를 작성하였습니다. 

- **[PRD (제품 요구사항)](docs/vibe_coding/prd.md)**: 제품 비전, 사용 사례, 기능 요구사항
- **[아키텍처](docs/vibe_coding/architecture.md)**: 기술 설계, 데이터 모델, 시스템 아키텍처
- **[구현 가이드](docs/vibe_coding/implementation.md)**: 개발 방법론, 테스트 전략, 코딩 표준
- **[발견사항](experiments/FINDINGS.md)**: 실험 결과 및 학습 내용

---

## 로드맵

### ✅ 현재 상태: MVP 완료 (v1.0.0)

- ✅ 완전한 파이프라인: 검색 → 다운로드 → 파싱 → 저장 → 조회
- ✅ 2010-2024년 데이터 지원 (15년)
- ✅ 상장 기업 전체 지원 (KOSPI/KOSDAQ/KONEX)
- ✅ 텍스트 기반 섹션 매칭 (XML 구조 변화에 강건함)
- ✅ 300+ 테스트, 90% 커버리지
- ✅ MongoDB 자동 저장 및 조회
- ✅ 다양한 분석 유형 지원 (단일/횡단면/시계열/패널)

### 향후 계획

**Phase 7: 다중 보고서 버전 관리**
- 원본 공시와 정정 공시를 모두 저장
- 시점별 조회 기능 (`as_of_date` 파라미터) 
- 기타 가능한 Forward-looking bias 완전 제거

**Phase 8: 고급 NLP 기능**
- 임베딩 모델 통합 (sentence-transformers 등)
- 연도별 텍스트 변화 자동 감지

**Phase 9: 프로덕션 강화**
- 성능 최적화 (커넥션 풀링, 캐싱)
- 안정성 향상 (재시도 로직, 에러 핸들링)
- CI/CD 자동화 (GitHub Actions)
- PyPI 패키지 배포

---

## 기여

현재 외부 기여는 받지 않고 있습니다. 향후 프로젝트가 안정화되면 기여 가이드라인을 공개할 예정입니다.

---

## 라이선스

본 프로젝트는 [MIT 라이선스](LICENSE) 하에 배포됩니다.

---

## 인용

학술 연구에서 `dart-fss-text`를 사용하는 경우 다음과 같이 인용해 주세요:

```bibtex
@software{dart_fss_text_2024,
  title={dart-fss-text: Structured Access to Korean DART Financial Statement Text},
  author={[저자명]},
  year={2024},
  version={1.0.0},
  url={https://github.com/your-org/dart-fss-text}
}
```

---



