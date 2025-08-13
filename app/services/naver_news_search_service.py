from langchain_community.document_loaders import WebBaseLoader
from typing import Optional, List, Dict
from langchain_core.documents import Document
from app.services.naver_news_api_service import NaverNewsAPIClient
from urllib.parse import urlparse
from collections import Counter
import time


class NaverNewsSearchService:
    """네이버 뉴스 검색 서비스 (Singleton)"""

    _instance: Optional['NaverNewsSearchService'] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        # Singleton 패턴에서 중복 초기화 방지
        if not hasattr(self, '_initialized'):
            self._initialized = True
            self._api_client = NaverNewsAPIClient()

    def __extract_news_metadata_from_url(self, urls: List[str]) -> List[Document]:
        loader = WebBaseLoader(web_paths=urls)
        docs = loader.load()
        return docs

    def __preprocess_page_content(self, content: str) -> str:
        """
        페이지 콘텐츠 전처리

        Args:
            content: 원본 텍스트

        Returns:
            전처리된 텍스트 (줄바꿈 제거, 연속 공백 제거)
        """
        import re
        # \n 제거
        content = content.replace('\n', ' ')
        # 연속된 공백을 하나로 치환
        content = re.sub(r'\s+', ' ', content)
        # 양쪽 공백 제거
        content = content.strip()
        return content

    def search_news(
        self,
        query: str,
        display: int = 10,
        start: int = 1,
        sort: str = "date"
    ) -> Dict:
        # response = NaverNewsResponse
        response = self._api_client.fetch_news(
            query=query,
            display=display,
            start=start,
            sort=sort
        )

        originallinks = [item.originallink for item in response.items]
        docs = self.__extract_news_metadata_from_url(originallinks)

        # 각 문서의 page_content 전처리 및 URL별 매핑
        docs_by_url = {}
        for doc in docs:
            doc.page_content = self.__preprocess_page_content(doc.page_content)
            # metadata에서 source URL 추출
            url = doc.metadata.get('source', '')
            docs_by_url[url] = doc

        # 각 item에 해당하는 doc 추가
        items_with_docs = []
        for item in response.items:
            item_dict = item.model_dump()
            doc = docs_by_url.get(item.originallink)

            if doc:
                item_dict['document'] = {
                    'metadata': doc.metadata,
                    'page_content': doc.page_content
                }
            else:
                item_dict['document'] = None

            items_with_docs.append(item_dict)

        return {
            "status": "success",
            "message": f"'{query}' 관련 뉴스 {len(response.items)}건을 가져왔습니다.",
            "data": {
                "lastBuildDate": response.lastBuildDate,
                "total": response.total,
                "start": response.start,
                "display": response.display,
                "items": items_with_docs
            }
        }

    def analyze_news_site_distribution(
        self,
        query: str,
        iterations: int,
        display: int
    ) -> Dict:
        """
        뉴스 사이트 분포도 분석

        Args:
            query: 검색어
            iterations: 반복 횟수 (기본 10번)
            display: 한 번에 가져올 뉴스 개수 (기본 100개)

        Returns:
            뉴스 사이트별 분포 통계
        """
        print(f"\n========== 뉴스 사이트 분포 분석 시작 ==========")
        print(f"검색어: {query}")
        print(f"반복 횟수: {iterations}")
        print(f"반복당 뉴스 개수: {display}")
        print(f"예상 총 뉴스 개수: {iterations * display}")
        print("=" * 50)

        all_links = []

        # STEP 1: iterations번 반복하여 뉴스 수집
        print(f"\n[STEP 1] 뉴스 링크 수집 시작 ({iterations}번 반복)")
        for i in range(iterations):
            # 시작 위치 계산 (1, 101, 201, ...)
            start_position = i * display + 1
            print(f"\n  [{i+1}/{iterations}] API 호출 - start: {start_position}, display: {display}")

            try:
                # Naver News API 호출
                response = self._api_client.fetch_news(
                    query=query,
                    display=display,
                    start=start_position,
                    sort="date"
                )
                print(f"  ✓ API 응답 성공 - 받은 뉴스 개수: {len(response.items)}")

                # originallink만 추출
                links = [item.originallink for item in response.items]
                all_links.extend(links)
                print(f"  ✓ 링크 추출 완료 - 현재까지 총 {len(all_links)}개")

                # API Rate Limiting 방지: 다음 호출 전 3초 대기 (마지막 iteration 제외)
                if i < iterations - 1:
                    print(f"  ⏳ API Rate Limiting 방지 - 3초 대기...")
                    time.sleep(3)

            except Exception as e:
                # 에러 발생 시 해당 iteration 건너뛰기
                print(f"  ✗ 에러 발생: {str(e)}")
                print(f"  → 해당 iteration 건너뛰기")
                continue

        print(f"\n[STEP 1 완료] 총 수집된 링크: {len(all_links)}개")

        # STEP 2: URL에서 도메인 추출
        print(f"\n[STEP 2] URL에서 도메인 추출 시작")
        domains = []
        for idx, link in enumerate(all_links):
            try:
                parsed = urlparse(link)
                domain = parsed.netloc

                # www. 제거
                if domain.startswith('www.'):
                    domain = domain[4:]

                domains.append(domain)

                # 진행상황 표시 (매 100개마다)
                if (idx + 1) % 100 == 0:
                    print(f"  진행중... {idx + 1}/{len(all_links)} 처리 완료")

            except Exception as e:
                print(f"  ✗ URL 파싱 실패 ({link}): {str(e)}")
                continue

        print(f"[STEP 2 완료] 총 추출된 도메인: {len(domains)}개")

        # STEP 3: 도메인별 카운트
        print(f"\n[STEP 3] 도메인별 통계 계산 시작")
        domain_counter = Counter(domains)
        print(f"[STEP 3 완료] 고유 도메인 수: {len(domain_counter)}개")

        # STEP 4: 통계 정보 생성
        print(f"\n[STEP 4] 최종 통계 생성")
        total_count = len(all_links)
        unique_domains = len(domain_counter)

        # 상위 도메인 리스트 (많은 순서대로)
        top_domains = [
            {
                "domain": domain,
                "count": count,
                "percentage": round((count / total_count * 100), 2)
            }
            for domain, count in domain_counter.most_common()
        ]

        # 상위 5개 도메인 출력
        print(f"\n  📊 상위 5개 뉴스 사이트:")
        for i, item in enumerate(top_domains[:5], 1):
            print(f"    {i}. {item['domain']}: {item['count']}개 ({item['percentage']}%)")

        print(f"\n========== 분석 완료 ==========\n")

        return {
            "status": "success",
            "message": f"'{query}' 검색어로 {total_count}개 뉴스 사이트 분포 분석 완료",
            "data": {
                "query": query,
                "total_news_count": total_count,
                "unique_domains_count": unique_domains,
                "iterations": iterations,
                "display_per_iteration": display,
                "domain_distribution": top_domains
            }
        }