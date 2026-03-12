"""
서비스 컨테이너 (DI 패턴)
모든 서비스 인스턴스를 한 곳에서 생성·관리하여
모듈 레벨 전역 인스턴스 문제와 순환 임포트를 해결합니다.
테스트 시 Mock 주입도 용이합니다.
"""
from app.services.rag_service import LegalFactChecker
from app.services.hook_service import InputAnalyzer, OutputValidator
from app.services.agent_service import RoutingAgent
from app.services.vision_service import VisionAnalyzer
from app.services.template_service import DocumentTemplateGenerator
from app.services.check_service import CheckService
from app.services.pdf_ingest_service import PDFLawParser


class ServiceContainer:
    """모든 서비스의 싱글톤 인스턴스를 보관합니다."""

    def __init__(self):
        self.checker = LegalFactChecker()
        self.analyzer = InputAnalyzer()
        self.agent = RoutingAgent()
        self.validator = OutputValidator()
        self.vision = VisionAnalyzer()
        self.template_generator = DocumentTemplateGenerator()
        self.pdf_parser = PDFLawParser()

        self.check_service = CheckService(
            checker=self.checker,
            analyzer=self.analyzer,
            agent=self.agent,
            validator=self.validator,
            vision=self.vision,
        )


_container: ServiceContainer | None = None


def get_services() -> ServiceContainer:
    """서비스 컨테이너 싱글톤을 반환합니다."""
    global _container
    if _container is None:
        _container = ServiceContainer()
    return _container


def reset_services() -> None:
    """테스트용: 서비스 컨테이너를 리셋합니다."""
    global _container
    _container = None
