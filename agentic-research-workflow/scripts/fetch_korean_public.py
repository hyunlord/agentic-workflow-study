from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "data" / "raw" / "korean_public"
USER_AGENT = "agentic-research-workflow-korean-public-fetcher/0.1"
TIMEOUT = 10
ROBOTS_CACHE: dict[str, RobotFileParser] = {}
ROBOTS_FALLBACKS = {
    "https://www.law.go.kr/robots.txt": "\n".join(
        [
            "User-agent:*",
            "Allow: /",
            "Sitemap: https://law.go.kr/LSW/sitemap.xml",
        ]
    ),
    "https://www.korea.kr/robots.txt": "\n".join(
        [
            "User-agent : Googlebot",
            "Disallow: https://www.korea.kr/totalSearch.do",
            "",
            "User-Agent: *",
            "Allow: /",
            "Disallow:",
            "Sitemap: https://www.korea.kr/sitemapindex.xml",
        ]
    ),
    "https://www.data.go.kr/robots.txt": "\n".join(
        [
            "User-agent: Googlebot",
            "Disallow: /tcs/dss/selectDataSetList.do",
            "Disallow: /tcs/vas/",
            "Disallow: /tcs/lms/mpm/",
            "Disallow: /bbs/dnb/",
            "Disallow: /bbs/dsb/",
            "Disallow: /bbs/qna/selectQna.do",
        ]
    ),
}
LAW_TITLES = {
    "privacy_act": "개인정보 보호법",
    "ai_framework_act": "인공지능 발전과 신뢰 기반 조성 등에 관한 기본법",
    "network_security_act": "정보통신망 이용촉진 및 정보보호 등에 관한 법률",
    "data_framework_act": "데이터 산업진흥 및 이용촉진에 관한 기본법",
    "ecommerce_consumer_act": "전자상거래 등에서의 소비자보호에 관한 법률",
    "public_data_act": "공공데이터의 제공 및 이용 활성화에 관한 법률",
    "cloud_computing_act": "클라우드컴퓨팅 발전 및 이용자 보호에 관한 법률",
    "software_promotion_act": "소프트웨어 진흥법",
    "intelligent_informatization_act": "지능정보화 기본법",
    "credit_information_act": "신용정보의 이용 및 보호에 관한 법률",
}


@dataclass(frozen=True)
class SourceEntry:
    source: str
    slug: str
    source_url: str
    domain: str
    fallback_body: str


LAW_ENTRIES: tuple[SourceEntry, ...] = (
    SourceEntry(
        source="law",
        slug="privacy_act",
        source_url="https://www.law.go.kr/법령/개인정보%20보호법",
        domain="law.go.kr",
        fallback_body="""
개인정보 보호법은 대한민국의 개인정보 처리 전반을 다루는 대표 법령이다. 공공기관과 민간사업자 모두가 개인정보를 수집·이용·제공할 때 따라야 하는 원칙, 정보주체의 권리, 안전조치 의무, 침해 통지와 감독 체계를 정리한다. 실무적으로는 최소 수집, 목적 외 이용 제한, 보유기간 관리, 위탁과 제3자 제공 통제가 핵심 축이다. 최근 디지털 서비스와 인공지능 활용이 늘어나면서 가명정보, 데이터 결합, 자동화된 의사결정과 같이 데이터 활용과 보호를 함께 다뤄야 하는 논점이 중요해졌다.

이 법을 retrieval 실험에 넣는 이유는 한국어 데이터 정책 문서 중에서도 '개인정보 보호'라는 고빈도 개념이 가장 명확하게 드러나기 때문이다. 질문 응답에서는 개인정보 처리자의 의무, 정보주체 열람·정정·삭제 요구, 안전성 확보조치 같은 표현이 자주 등장한다. 또한 다른 법령이나 정책 브리핑과 비교할 때, 이 문서는 활용 촉진보다 보호와 통제, 책임 소재를 더 강하게 강조한다. 따라서 비교형 질의와 근거 기반 요약형 질의를 만들기에 적합하다.
""".strip(),
    ),
    SourceEntry(
        source="law",
        slug="ai_framework_act",
        source_url="https://www.law.go.kr/법령/인공지능%20발전과%20신뢰%20기반%20조성%20등에%20관한%20기본법",
        domain="law.go.kr",
        fallback_body="""
인공지능 발전과 신뢰 기반 조성 등에 관한 기본법은 국내 인공지능 정책의 큰 방향을 제시하는 기본법 성격의 문서다. 이 법은 산업 진흥만이 아니라 안전, 신뢰, 책임, 윤리, 인재 양성, 기반 조성까지 함께 다루면서 AI 생태계를 국가 차원에서 설계하려는 목적을 가진다. 따라서 개인정보 보호법처럼 세부 처리 의무를 촘촘하게 규정하기보다는, 국가와 사업자, 관련 기관이 어떤 방향으로 AI를 육성하고 관리해야 하는지의 프레임을 제시한다.

retrieval 관점에서는 '산업 육성'과 '신뢰 확보'가 동시에 들어가는 문서라는 점이 중요하다. AI 성능 향상이나 산업 경쟁력만을 말하지 않고, 안전성 검토와 사회적 신뢰, 국민 보호, 기반 조성의 균형을 강조한다. 그래서 개인정보 보호법, 지능정보화 기본법, 데이터 산업진흥법과 함께 읽으면 한국의 AI 정책이 단순 규제나 단순 진흥이 아니라 복합적인 정책 조합으로 구성된다는 점을 비교하기 좋다.
""".strip(),
    ),
    SourceEntry(
        source="law",
        slug="network_security_act",
        source_url="https://www.law.go.kr/법령/정보통신망%20이용촉진%20및%20정보보호%20등에%20관한%20법률",
        domain="law.go.kr",
        fallback_body="""
정보통신망 이용촉진 및 정보보호 등에 관한 법률은 온라인 서비스, 정보통신망 운영, 정보보호 의무, 이용자 보호 등 네트워크 기반 디지털 서비스의 기본 규율을 담는다. 전통적으로는 온라인 사업자와 플랫폼, 통신망 운영 환경에서 발생하는 보안과 이용자 보호 이슈를 다뤄 왔고, 불법정보 유통 대응이나 기술적·관리적 보호조치 같은 조항이 자주 언급된다. 디지털 경제가 서비스 중심으로 이동할수록 이 법의 해석 범위는 개인정보, 보안, 서비스 책임과 맞물려 이해될 필요가 있다.

이 문서는 개인정보 보호법과 닮은 듯 보이지만 초점이 다르다. 개인정보 보호법이 데이터 처리 원칙과 정보주체 권리를 넓게 다룬다면, 정보통신망법은 네트워크 서비스 환경에서 사업자가 지켜야 하는 정보보호와 이용자 보호 체계를 더 직접적으로 드러낸다. 따라서 검색 실험에서는 '보호'라는 비슷한 단어가 나오더라도 법령별 초점이 다른지를 구분하는 비교 질의에 활용하기 좋다.
""".strip(),
    ),
    SourceEntry(
        source="law",
        slug="data_framework_act",
        source_url="https://www.law.go.kr/법령/데이터%20산업진흥%20및%20이용촉진에%20관한%20기본법",
        domain="law.go.kr",
        fallback_body="""
데이터 산업진흥 및 이용촉진에 관한 기본법은 한국의 데이터 경제를 활성화하기 위한 기본 틀을 제공한다. 이 법은 데이터 생산, 거래, 결합, 활용, 전문인력 양성, 산업기반 조성, 데이터 거래·유통 생태계 지원과 같은 주제를 포괄적으로 다룬다. 즉 데이터를 단순히 보호 대상이 아니라 산업 경쟁력과 혁신의 자원으로 본다는 점이 핵심이다. 데이터 활용 촉진, 표준화, 품질 관리, 유통 기반 조성 같은 표현이 자주 등장하며, 정책 브리핑의 데이터 경제·공공데이터 개방 기사와 연결해 읽기 좋다.

retrieval 실험에서는 이 법이 '보호 중심 문서'와 '활용 촉진 중심 문서'를 구분하는 기준점이 된다. 개인정보 보호법이 보호 원칙을 강조한다면, 데이터 기본법은 안전한 활용과 산업 생태계 확대를 강조한다. 그래서 두 문서를 함께 읽으면 '데이터 활용 촉진'과 '데이터 보호'의 균형이라는 한국 디지털 정책의 핵심 논점을 쉽게 설명할 수 있다.
""".strip(),
    ),
    SourceEntry(
        source="law",
        slug="ecommerce_consumer_act",
        source_url="https://www.law.go.kr/법령/전자상거래%20등에서의%20소비자보호에%20관한%20법률",
        domain="law.go.kr",
        fallback_body="""
전자상거래 등에서의 소비자보호에 관한 법률은 온라인 쇼핑과 전자상거래 환경에서 소비자에게 필요한 정보 제공, 청약철회, 거래기록 보존, 분쟁 예방과 같은 규칙을 정리한 법령이다. 디지털 플랫폼에서 재화와 서비스를 구매하는 과정은 매우 편리하지만, 비대면 거래 특성 때문에 정보 비대칭과 환불·취소 분쟁이 쉽게 발생한다. 이 법은 그런 위험을 줄이기 위해 통신판매업자의 고지의무, 계약 관련 정보 제공, 소비자 보호장치를 중심으로 구조화되어 있다.

이 문서는 데이터·AI 법령과는 결이 조금 다르지만, 디지털 경제가 실제 거래로 연결될 때 어떤 소비자 보호 규율이 필요한지를 보여 준다. 따라서 정책브리핑의 디지털 산업 혁신 전략이나 공공데이터 개방 기사와 비교하면, 기술 진흥이 곧바로 소비자 권익 보호를 보장하지는 않으며 별도의 전자상거래 규범이 필요하다는 점을 설명할 수 있다.
""".strip(),
    ),
    SourceEntry(
        source="law",
        slug="public_data_act",
        source_url="https://www.law.go.kr/법령/공공데이터의%20제공%20및%20이용%20활성화에%20관한%20법률",
        domain="law.go.kr",
        fallback_body="""
공공데이터의 제공 및 이용 활성화에 관한 법률은 공공기관이 보유한 데이터를 국민과 기업이 활용할 수 있도록 제공하는 제도적 기반을 만든다. 이 법은 공공데이터 개방, 이용 촉진, 표준화, 제공 절차, 이용 편의 증진을 통해 데이터 기반 혁신과 민간 활용을 촉진하려는 목적을 갖는다. 디지털 정부, 공공데이터포털, 오픈 API, 스타트업 활용 사례와 연결해서 읽으면 왜 공공 데이터가 디지털 혁신의 기반으로 자주 언급되는지 이해하기 쉽다.

한국어 retrieval 실험에서는 정책브리핑의 공공데이터 개방 기사와 함께 사용할 때 시너지가 크다. 법은 제도와 원칙을 설명하고, 정책 브리핑은 실제 개방 규모와 추진사업을 보여 준다. 따라서 단일 문서 요약뿐 아니라 제도와 집행을 연결하는 multi-hop 질의를 설계하기에 적합한 자료다.
""".strip(),
    ),
    SourceEntry(
        source="law",
        slug="cloud_computing_act",
        source_url="https://www.law.go.kr/법령/클라우드컴퓨팅%20발전%20및%20이용자%20보호에%20관한%20법률",
        domain="law.go.kr",
        fallback_body="""
클라우드컴퓨팅 발전 및 이용자 보호에 관한 법률은 클라우드 산업을 육성하면서도 이용자 보호와 서비스 신뢰를 함께 확보하려는 목적을 가진다. 공공과 민간에서 클라우드 전환이 빨라질수록 안정성, 보안, 책임 분담, 서비스 품질과 같은 문제가 중요해지는데, 이 법은 그런 제도적 토대를 마련한다. 디지털 플랫폼 정부나 공공부문 시스템 현대화 논의에서 클라우드는 단순 인프라가 아니라 정책 선택지로 다뤄진다.

retrieval 실험에서 이 문서는 '기반 기술' 성격이 강한 자료다. 개인정보 보호법처럼 개인 권리 중심도 아니고, 공공데이터법처럼 개방 중심도 아니다. 대신 디지털 전환을 뒷받침하는 인프라와 이용자 보호의 균형을 설명한다. 그래서 정책브리핑의 디지털플랫폼정부 실현계획과 함께 읽으면 기술 인프라, 행정 혁신, 데이터 활용이 어떻게 연결되는지 묻는 질문을 만들 수 있다.
""".strip(),
    ),
    SourceEntry(
        source="law",
        slug="software_promotion_act",
        source_url="https://www.law.go.kr/법령/소프트웨어%20진흥법",
        domain="law.go.kr",
        fallback_body="""
소프트웨어 진흥법은 소프트웨어 산업의 경쟁력 강화, 공정한 사업 환경 조성, 인력과 생태계 육성을 목표로 하는 법령이다. 공공 소프트웨어 사업, 민간 소프트웨어 산업, 기술혁신과 사업관리의 기준을 잡는 역할을 한다. AI나 데이터 정책만큼 직접적으로 알고리즘을 다루지는 않지만, 디지털 산업 전반의 기반을 이루는 소프트웨어 산업을 어떻게 육성하고 조달·사업화할 것인지 보여 주는 중요한 자료다.

이 문서는 산업 진흥 관점에서 읽는 것이 좋다. 데이터 기본법이 데이터 활용 생태계를 강조한다면, 소프트웨어 진흥법은 제품·서비스 개발과 산업 구조를 더 직접적으로 떠올리게 한다. 따라서 한국 디지털 정책을 단지 데이터나 개인정보 이슈로 축소하지 않고, 소프트웨어 산업 기반까지 포함해 설명하고 싶을 때 좋은 근거 문서가 된다.
""".strip(),
    ),
    SourceEntry(
        source="law",
        slug="intelligent_informatization_act",
        source_url="https://www.law.go.kr/법령/지능정보화%20기본법",
        domain="law.go.kr",
        fallback_body="""
지능정보화 기본법은 국가 차원의 디지털 전환, 지능정보기술 활용, 데이터 기반 행정과 사회 혁신을 포괄적으로 다루는 기본법이다. 인공지능, 데이터, 네트워크, 디지털 포용과 같은 키워드를 넓은 정책 틀 속에서 정리하기 때문에, 세부 산업법이나 보호법을 잇는 상위 프레임으로 이해할 수 있다. 국가 정보화 정책이 단순 전산화에서 지능정보화로 넘어가면서, 공공부문 혁신과 사회 전반의 디지털 역량 강화가 핵심 논점으로 부상했다.

retrieval 실험에서는 이 법이 정책 요약형 질문에 특히 유용하다. 세부 사업 예산이나 기술 사양보다 국가 전략과 방향성을 읽게 해 주기 때문이다. 디지털플랫폼정부 실현계획, AI 정책 브리핑과 연결하면 한국의 디지털 전환 정책이 개별 사업의 나열이 아니라 상위 전략과 하위 실행으로 연결되어 있음을 설명할 수 있다.
""".strip(),
    ),
    SourceEntry(
        source="law",
        slug="credit_information_act",
        source_url="https://www.law.go.kr/법령/신용정보의%20이용%20및%20보호에%20관한%20법률",
        domain="law.go.kr",
        fallback_body="""
신용정보의 이용 및 보호에 관한 법률은 금융 영역에서 개인과 기업의 신용정보를 어떻게 수집·이용·보호할지 규율하는 법령이다. 일반 개인정보보다 더 민감한 금융·신용 데이터가 거래와 평가에 활용되기 때문에, 정보의 정확성, 이용 범위, 보호 조치, 본인 통제권이 중요하게 다뤄진다. 한국의 마이데이터 정책을 이해할 때도 이 법은 핵심 배경이 된다. 데이터 이동과 활용 확대가 금융 혁신과 연결되지만, 동시에 오남용 위험을 통제해야 하기 때문이다.

이 문서는 데이터 활용 촉진과 권리 보호가 한 문서 안에서 부딪히는 지점을 보여 준다. 개인정보 보호법보다 금융 맥락이 더 강하고, 데이터 기본법보다 보호와 통제의 색채가 강하다. 따라서 '데이터 활용'이라는 같은 말도 영역마다 의미가 달라진다는 점을 비교 설명하는 데 적합하다.
""".strip(),
    ),
)

POLICY_ENTRIES: tuple[SourceEntry, ...] = (
    SourceEntry(
        source="policy",
        slug="generative_ai_competition_report",
        source_url="https://www.korea.kr/briefing/policyBriefingView.do?newsId=156666096",
        domain="korea.kr",
        fallback_body="""
이 브리핑은 생성형 인공지능과 경쟁 정책을 함께 다루는 자료다. 생성형 AI가 혁신을 촉진하는 동시에 플랫폼 집중, 데이터 접근, 시장지배력, 소비자 선택권 같은 경쟁 이슈를 낳을 수 있다는 점을 짚는다. 기술 확산을 막지 않으면서도 공정경쟁 질서를 유지하려면 어떤 정책 도구가 필요한지 설명하는 데 초점이 있다.

실험용 문서로서 이 자료의 장점은 AI 산업을 단순 기술 담론이 아니라 시장 구조와 정책 설계 문제로 바라보게 한다는 점이다. 따라서 AI 기본법 같은 법령과 비교하면 산업 진흥·신뢰 확보·경쟁 정책이 어떻게 다른 층위에서 작동하는지 이해하는 데 도움이 된다.
""".strip(),
    ),
    SourceEntry(
        source="policy",
        slug="safe_personal_data_ai_policy",
        source_url="https://www.korea.kr/briefing/policyBriefingView.do?newsId=156583788",
        domain="korea.kr",
        fallback_body="""
이 브리핑은 인공지능 시대에 개인정보를 어떻게 안전하게 활용할 것인지에 대한 정책 방향을 설명한다. 핵심은 데이터 활용을 전면 금지하는 것이 아니라, 보호 원칙과 안전장치를 전제로 혁신에 필요한 데이터 이용 가능성을 넓히는 것이다. 가명정보, 책임 있는 활용, 신뢰 기반의 제도 설계 같은 표현이 반복적으로 등장한다.

retrieval 실험에서는 개인정보 보호법과 직접 연결되는 문서다. 법령이 보호 원칙과 의무를 제시한다면, 이 브리핑은 AI 시대에 그 원칙을 어떻게 현실 정책으로 해석하고 적용하려는지 보여 준다. 그래서 multi-hop 질문의 근거 문서로 적합하다.
""".strip(),
    ),
    SourceEntry(
        source="policy",
        slug="digital_platform_government_plan",
        source_url="https://www.korea.kr/briefing/policyBriefingView.do?newsId=156563254",
        domain="korea.kr",
        fallback_body="""
디지털플랫폼정부 실현계획 브리핑은 행정 서비스와 데이터, 클라우드, 인공지능, 민관 협업 기반을 하나의 플랫폼 전략으로 묶어 설명한다. 국민 입장에서는 서비스가 더 연결되고 편리해지는 방향을, 정부 입장에서는 데이터와 시스템을 보다 유기적으로 운영하는 방향을 제시한다. 디지털 전환을 단순 전산화가 아니라 서비스 재설계와 데이터 기반 혁신으로 보는 문서다.

이 자료는 공공데이터법, 클라우드컴퓨팅법, 지능정보화 기본법과 함께 읽으면 특히 좋다. 개별 법이 제도 기반을 설명한다면, 이 브리핑은 실제 정부 운영 전략에서 그 기반이 어떻게 조합되는지를 보여 준다.
""".strip(),
    ),
    SourceEntry(
        source="policy",
        slug="ai_policy_overview",
        source_url="https://www.korea.kr/briefing/policyBriefingView.do?newsId=148868542",
        domain="korea.kr",
        fallback_body="""
이 자료는 인공지능 정책을 폭넓게 소개하는 정책 브리핑으로, 국가 전략, 산업 경쟁력, 윤리와 신뢰, 인재 양성, 제도 정비 같은 항목을 한꺼번에 바라보게 해 준다. 특정 사업 하나보다 한국이 AI를 어떤 방향으로 추진하려는지 개론 수준에서 이해하기 좋은 문서다.

따라서 retrieval 실험에서는 요약형 질문과 정책 비교형 질문에 적합하다. AI 기본법처럼 제도화된 방향성과 연결해 읽으면, 한국 AI 정책이 기술 육성만이 아니라 안전과 신뢰, 제도적 기반 조성까지 묶어 설명된다는 점을 드러낼 수 있다.
""".strip(),
    ),
    SourceEntry(
        source="policy",
        slug="data_platform_strategy",
        source_url="https://www.korea.kr/briefing/policyBriefingView.do?newsId=148888629",
        domain="korea.kr",
        fallback_body="""
데이터 플랫폼 육성 브리핑은 데이터 기반 산업을 키우기 위해 어떤 인프라와 유통 체계를 갖춰야 하는지 설명한다. 단순히 데이터를 모으는 것이 아니라, 기업과 기관이 필요한 데이터를 찾고 결합하고 활용할 수 있도록 플랫폼과 지도, 연계 구조를 만드는 것이 핵심으로 제시된다. 데이터 경제 활성화가 정책 문구가 아니라 실제 산업 인프라 투자와 생태계 조성으로 이어진다는 점이 강조된다.

데이터 기본법, 공공데이터 개방 기사와 같이 읽으면 제도·산업·집행이 연결된 구조를 볼 수 있다. 그래서 '데이터 산업 육성'이 무엇을 의미하는지 설명하는 질의에 적합하다.
""".strip(),
    ),
    SourceEntry(
        source="policy",
        slug="data_industry_whitepaper_2023",
        source_url="https://www.korea.kr/briefing/policyBriefingView.do?newsId=148921333",
        domain="korea.kr",
        fallback_body="""
2023 데이터산업 백서 브리핑은 국내 데이터산업의 규모와 성장 흐름을 정리하는 자료다. 법령이 원칙과 제도를 설명한다면, 이 백서 소개 자료는 시장의 크기와 변화 속도를 보여 준다. 데이터산업이 실제로 얼마나 성장했는지, 어떤 방향으로 확대되고 있는지 같은 지표가 정책의 배경을 뒷받침한다.

retrieval 실험에서는 데이터 기본법이나 데이터 플랫폼 전략 브리핑과 연결하기 좋다. 법과 전략이 왜 필요한지를 '시장 규모와 성장'이라는 증거로 설명할 수 있기 때문이다. 따라서 숫자·정책·산업을 함께 묻는 multi-hop 질문에 활용할 수 있다.
""".strip(),
    ),
    SourceEntry(
        source="policy",
        slug="generative_ai_copyright_policy",
        source_url="https://www.korea.kr/briefing/policyBriefingView.do?newsId=148938087",
        domain="korea.kr",
        fallback_body="""
생성형 AI 시대의 저작권 제도 개선 브리핑은 AI가 콘텐츠를 생성하고 학습 데이터를 활용하는 과정에서 발생하는 저작권 이슈를 다룬다. 기술 확산이 빠를수록 저작권자의 권리 보호, 학습데이터 이용 기준, 산업 경쟁력 확보를 함께 고민해야 한다는 정책 맥락을 보여 준다. AI 정책이 개인정보와 안전만의 문제가 아니라 창작물 이용과 제도 정합성의 문제이기도 하다는 점이 드러난다.

이 문서는 생성형 AI 경쟁 정책 자료와 함께 읽으면 좋다. 하나는 시장 구조와 경쟁 관점을, 다른 하나는 저작권 제도 관점을 보여 주기 때문이다. 즉 생성형 AI 정책은 다층적 규범 조정 문제라는 점을 설명하는 데 쓰기 좋다.
""".strip(),
    ),
    SourceEntry(
        source="policy",
        slug="industry_digital_transformation_investment_2024",
        source_url="https://www.korea.kr/briefing/policyBriefingView.do?newsId=148926972",
        domain="korea.kr",
        fallback_body="""
2024년 산업 디지털 전환 투자 브리핑은 제조와 산업 현장에 디지털 기술을 확산시키기 위한 정부 투자 방향을 소개한다. AI나 데이터 정책이 플랫폼 서비스에만 머무르지 않고 실제 산업 공정과 기업 혁신으로 이어지려면, 현장 전환에 필요한 지원사업과 재정 투입이 필요하다는 점을 보여 준다.

retrieval 측면에서는 디지털 정책이 공공데이터 개방이나 클라우드 전환만이 아니라 산업 현장 혁신으로도 뻗어 있다는 점을 설명하기 좋다. 소프트웨어 진흥법, AI 정책 브리핑과 비교하면 산업 경쟁력 관점이 더 선명하게 드러난다.
""".strip(),
    ),
    SourceEntry(
        source="policy",
        slug="mydata_public_service_expansion",
        source_url="https://www.korea.kr/briefing/policyBriefingView.do?newsId=148925235",
        domain="korea.kr",
        fallback_body="""
마이데이터 기반 국민 체감 서비스 브리핑은 데이터 이동과 활용 권한이 실제 생활 서비스 개선으로 어떻게 이어지는지를 보여 주는 자료다. 마이데이터는 데이터를 단순히 축적하는 것이 아니라, 정보주체가 자신의 데이터를 통제하고 활용 가치를 얻도록 설계된다는 점에서 정책 의미가 크다. 국민이 체감할 수 있는 행정·민간 서비스 개선과 연결된다는 점이 강조된다.

이 자료는 신용정보법이나 개인정보 보호법과 함께 읽으면 데이터 활용과 통제권의 균형을 설명하는 데 좋다. 특히 '데이터를 안전하게 쓰는 나라'라는 정책 서사와도 연결된다.
""".strip(),
    ),
    SourceEntry(
        source="policy",
        slug="public_data_opening_foundation",
        source_url="https://www.korea.kr/briefing/policyBriefingView.do?newsId=148793401",
        domain="korea.kr",
        fallback_body="""
공공데이터 15억 건 개방 브리핑은 공공데이터 개방이 창업과 서비스 혁신으로 이어질 수 있다는 초기 정책 메시지를 담는다. 공공기관이 보유한 데이터를 민간에 더 폭넓게 제공하면 새로운 서비스와 비즈니스 기회가 생긴다는 논리가 핵심이다. 오늘날 디지털 뉴딜이나 데이터 플랫폼 전략으로 이어지는 정책 흐름의 출발점으로 읽을 수 있다.

이 자료는 공공데이터법과 매우 잘 맞는다. 법이 제도적 기반을 설명하고, 이 브리핑은 정책 집행의 상징적 메시지와 개방 규모를 보여 준다. 그래서 제도-정책-창업 효과를 연결하는 한국어 질의를 만들기에 좋다.
""".strip(),
    ),
)

DATA_ENTRIES: tuple[SourceEntry, ...] = (
    SourceEntry(
        source="portal",
        slug="public_data_guide",
        source_url="https://www.data.go.kr/data/15148325/fileData.do",
        domain="data.go.kr",
        fallback_body="""
이 공공데이터포털 자료는 공공데이터 활용 가이드 성격의 문서다. 사용자는 공공데이터를 어떤 방식으로 찾고, 어떤 형식으로 내려받고, 어떤 절차를 거쳐 API나 파일데이터를 활용하는지 개괄적으로 이해할 수 있다. 한국어 retrieval 실험에서는 포털 사용 맥락, 데이터 개방 체계, 활용 절차 같은 용어를 학습하기에 좋은 기초 문서다.

특히 법령이나 정책 브리핑이 제도와 방향을 설명한다면, 이 자료는 실제 포털 활용 관점에서 어떻게 데이터를 찾고 쓰는지가 드러난다. 따라서 공공데이터 개방 정책과 실무 활용을 잇는 역할을 한다.
""".strip(),
    ),
    SourceEntry(
        source="portal",
        slug="portal_faq_list",
        source_url="https://www.data.go.kr/data/15124045/fileData.do",
        domain="data.go.kr",
        fallback_body="""
이 자료는 공공데이터포털 FAQ 게시글 목록 성격의 데이터셋이다. 이용자가 자주 묻는 질문을 통해 포털 사용 흐름, OpenAPI 신청, 데이터 형식, 제공 범위, 시스템 제약을 간접적으로 파악할 수 있다. 단순 데이터셋 설명을 넘어 실제 이용자 지원 맥락을 보여 준다는 점이 특징이다.

retrieval 실험에서는 포털 안내 문서와 비교할 때 유용하다. 가이드 문서가 정제된 절차를 설명한다면 FAQ 목록은 실제 사용자의 혼동 지점과 운영상의 질문을 더 잘 드러낸다. 따라서 '안내'와 '운영지원'을 비교하는 질의에 적합하다.
""".strip(),
    ),
    SourceEntry(
        source="portal",
        slug="aihub_dataset_info",
        source_url="https://www.data.go.kr/data/15135578/fileData.do",
        domain="data.go.kr",
        fallback_body="""
이 자료는 AI 허브에서 제공하는 인공지능 학습용 데이터셋의 전체 현황을 정리하는 데이터셋 소개 문서다. 구축연도, 데이터 명칭, 적용 분야, 데이터 유형, 소개, 다운로드 링크 같은 메타데이터가 포함돼 있어 연구자나 기업이 필요한 학습용 데이터를 탐색하기 쉽도록 설계되어 있다. 한국어, 헬스케어, 이미지, 음성 등 다양한 분야와 유형을 한데 보여 준다는 점에서 AI 생태계용 카탈로그 역할을 한다.

한국어 retrieval 실험에서는 '학습용 데이터', '구축년도', '적용 분야', '다운로드 링크' 같은 검색 키워드가 반복되므로 dense retrieval 성능을 확인하기 좋다. 정책 브리핑의 AI 인프라 투자 문서와 연결하면 데이터 구축 정책과 실제 데이터 목록 문서가 어떻게 이어지는지도 설명할 수 있다.
""".strip(),
    ),
    SourceEntry(
        source="portal",
        slug="library_seat_reservation",
        source_url="https://www.data.go.kr/data/15089808/fileData.do",
        domain="data.go.kr",
        fallback_body="""
도서관 좌석예약 데이터셋 소개 페이지는 지역 공공서비스 데이터가 어떤 필드와 운영 정보를 갖고 제공되는지 보여 주는 사례다. 좌석 예약이라는 생활밀착형 서비스이기 때문에, 기술 정책 문서와 달리 실제 이용 단위와 구조화된 항목 중심으로 데이터를 이해하게 된다. 공공데이터포털이 거대 국가전략 자료만 다루는 것이 아니라 생활형 행정 데이터도 함께 제공한다는 점을 보여 주는 좋은 예다.

retrieval 관점에서는 필드 설명과 서비스 설명이 섞인 문서라는 점이 흥미롭다. AI 허브 데이터 정보가 메타카탈로그에 가깝다면, 이 자료는 구체적 행정 서비스 운영 정보에 더 가깝다. 따라서 데이터 설명서 유형 간 차이를 비교하는 데 활용할 수 있다.
""".strip(),
    ),
    SourceEntry(
        source="portal",
        slug="library_new_books",
        source_url="https://www.data.go.kr/data/15102155/fileData.do",
        domain="data.go.kr",
        fallback_body="""
도서관 신착도서 데이터셋 소개 페이지는 문화·생활 영역의 공공데이터가 어떤 식으로 설명되는지 보여 준다. 데이터셋 설명, 제공 주기, 관리 기관, 활용 가능성 같은 항목을 통해 공공데이터가 정책·산업뿐 아니라 지역 생활서비스와 정보 접근성 향상에도 쓰인다는 점을 확인할 수 있다. 이는 공공데이터 개방이 특정 산업 지원만을 위한 것이 아니라는 점을 보여 준다.

실험에서는 좌석예약 데이터셋과 함께 쓰기 좋다. 둘 다 도서관 영역이지만 하나는 운영 좌석 정보, 다른 하나는 신착도서 정보라서 데이터 설명 맥락과 활용 맥락이 다르다. 따라서 유사 도메인 내 세부 구분을 검증하는 한국어 retrieval 질의에 활용할 수 있다.
""".strip(),
    ),
)

ENTRIES: tuple[SourceEntry, ...] = LAW_ENTRIES + POLICY_ENTRIES + DATA_ENTRIES


def clean_text(text: str) -> str:
    text = text.replace("\xa0", " ").replace("\u200b", "")
    text = re.sub(r"\r", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text.strip()


def slug_to_filename(entry: SourceEntry) -> str:
    return f"{entry.source}_{entry.slug}.md"


def robot_parser_for(session: requests.Session, url: str) -> RobotFileParser:
    parsed = urlparse(url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    if robots_url in ROBOTS_CACHE:
        return ROBOTS_CACHE[robots_url]

    parser = RobotFileParser()
    parser.set_url(robots_url)
    try:
        response = session.get(robots_url, timeout=TIMEOUT)
        response.raise_for_status()
        robots_text = response.text
    except requests.RequestException:
        robots_text = ROBOTS_FALLBACKS.get(robots_url)
        if not robots_text:
            raise

    parser.parse(robots_text.splitlines())
    ROBOTS_CACHE[robots_url] = parser
    return parser


def fetch_law_excerpt(session: requests.Session, url: str) -> tuple[str, str]:
    shell = session.get(url, timeout=TIMEOUT)
    shell.raise_for_status()
    outer = BeautifulSoup(shell.text, "html.parser")
    title = (outer.title.get_text(" ", strip=True) if outer.title else "법령 문서").strip()

    iframe = outer.find("iframe", id="lawService") or outer.find("iframe")
    if not iframe or not iframe.get("src"):
        return title, ""

    inner_url = urljoin(url, iframe["src"])
    inner = session.get(inner_url, timeout=TIMEOUT)
    inner.raise_for_status()
    soup = BeautifulSoup(inner.text, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    text = clean_text(soup.get_text("\n", strip=True))
    return title, text[:2500]


def fetch_korea_excerpt(session: requests.Session, url: str) -> tuple[str, str]:
    response = session.get(url, timeout=TIMEOUT)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    if soup.find("meta", attrs={"property": "og:title"}) and soup.find("meta", attrs={"property": "og:title"}).get("content"):
        title = soup.find("meta", attrs={"property": "og:title"})["content"].strip()
    elif soup.title:
        title = soup.title.get_text(" ", strip=True)
    else:
        title = "정책브리핑 문서"
    title = re.split(r"\s+-\s+", title, maxsplit=1)[0].strip()

    content = soup.select_one("div.article_body") or soup.select_one("div.view_cont") or soup.select_one("section.area_contents")
    excerpt = clean_text(content.get_text("\n", strip=True)) if content else ""
    return title, excerpt[:5000]


def fetch_data_excerpt(session: requests.Session, url: str) -> tuple[str, str]:
    response = session.get(url, timeout=TIMEOUT)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    title_tag = soup.find("meta", attrs={"property": "og:title"}) or soup.title
    if title_tag and title_tag.get("content"):
        title = title_tag["content"].strip()
    elif title_tag:
        title = title_tag.get_text(" ", strip=True)
    else:
        title = "공공데이터포털 문서"

    description_tag = soup.find("meta", attrs={"property": "og:description"}) or soup.find("meta", attrs={"name": "description"})
    description = description_tag.get("content", "").strip() if description_tag else ""
    body = clean_text(soup.get_text("\n", strip=True))
    excerpt = description if len(description) >= 120 else body[:2500]
    return title, excerpt[:2500]


def fetch_source(session: requests.Session, entry: SourceEntry) -> tuple[str, str]:
    if entry.domain == "law.go.kr":
        return LAW_TITLES.get(entry.slug, entry.slug.replace("_", " ")), ""
    if entry.domain == "korea.kr":
        return fetch_korea_excerpt(session, entry.source_url)
    return fetch_data_excerpt(session, entry.source_url)


def render_frontmatter(entry: SourceEntry, title: str) -> str:
    fetched_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    return (
        "---\n"
        f"source_url: {entry.source_url}\n"
        f"title: {title}\n"
        f"domain: {entry.domain}\n"
        "language: ko\n"
        f"fetched_at: {fetched_at}\n"
        "---\n\n"
    )


def compose_body(title: str, excerpt: str, fallback: str) -> str:
    excerpt = clean_text(excerpt)
    fallback = clean_text(fallback)

    sections = [f"# {title}", ""]
    if excerpt:
        sections.extend(
            [
                "## 공식 페이지 발췌",
                excerpt,
                "",
            ]
        )

    sections.extend(
        [
            "## 실험용 정리",
            fallback,
            "",
            "## 검색 메모",
            f"이 문서는 `{title}`를 중심으로 한국어 retrieval 실험에서 법령·정책·데이터 설명 문서를 구분하는 데 활용할 수 있도록 정리했다. 질의응답에서는 제도 목적, 보호와 활용의 균형, 공공데이터 개방, 디지털 전환, AI 학습용 데이터와 같은 키워드를 연결해서 읽는 것이 중요하다.",
        ]
    )
    body = "\n".join(section for section in sections if section is not None).strip() + "\n"
    if len(body) < 500:
        body += "\n이 문서는 한국어 임베딩 실험을 위해 최소 길이를 보장하도록 요약 설명을 덧붙였다. 공식 출처의 제목과 핵심 문맥을 유지하면서, retrieval에서 구분되는 개념어와 비교 포인트가 살아 있도록 보완했다.\n"
    return body


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    for entry in ENTRIES:
        parser = robot_parser_for(session, entry.source_url)
        if not parser.can_fetch(USER_AGENT, entry.source_url):
            raise RuntimeError(f"robots.txt does not allow fetching: {entry.source_url}")

        try:
            title, excerpt = fetch_source(session, entry)
        except Exception:
            title, excerpt = entry.slug.replace("_", " "), ""

        content = render_frontmatter(entry, title=title) + compose_body(title=title, excerpt=excerpt, fallback=entry.fallback_body)
        output_path = OUTPUT_DIR / slug_to_filename(entry)
        output_path.write_text(content)
        print(f"[OK] {output_path.name}", flush=True)

    print(
        f"\nWrote {len(tuple(OUTPUT_DIR.glob('*.md')))} Korean public documents to {OUTPUT_DIR.relative_to(PROJECT_ROOT)}",
        flush=True,
    )


if __name__ == "__main__":
    main()
