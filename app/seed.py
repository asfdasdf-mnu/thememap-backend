"""Explicit sample import, never overwrites existing records."""
from .database import Base, make_engine, session_factory
from .models import Stock, Theme, ThemeStock

THEMES = [(1, '반도체', '반도체 설계·생산·장비 분야 예시'), (2, '인공지능', 'AI 서비스 및 인프라 분야 예시'), (3, '이차전지', '배터리와 소재 분야 예시')]
STOCKS = [('900001', '샘플반도체'), ('900002', '샘플클라우드'), ('900003', '샘플배터리'), ('900004', '샘플소재')]
LINKS = [(1, '900001', '반도체를 생산한다는 가상 사업 설정'), (2, '900001', 'AI 연산용 반도체를 공급한다는 가상 사업 설정'), (2, '900002', 'AI 클라우드를 제공한다는 가상 사업 설정'), (3, '900003', '배터리를 생산한다는 가상 사업 설정'), (3, '900004', '배터리 소재를 공급한다는 가상 사업 설정')]

def seed(session):
    for id_, name, description in THEMES:
        existing = session.get(Theme, id_)
        if existing and existing.name != name:
            raise ValueError('Sample ID conflicts with existing theme')
        if existing is None:
            session.add(Theme(id=id_, name=name, description=description))
    for code, name in STOCKS:
        existing = session.get(Stock, code)
        if existing and (existing.name != name or existing.market != 'DEMO'):
            raise ValueError('Sample code conflicts with existing stock')
        if existing is None:
            session.add(Stock(code=code, name=name, market='DEMO', description='실제 상장사가 아닌 API 시연용 가상 기업'))
    session.flush()
    for theme_id, stock_code, reason in LINKS:
        if session.get(ThemeStock, (theme_id, stock_code)) is None:
            session.add(ThemeStock(theme_id=theme_id, stock_code=stock_code, reason=reason, source_title='프로젝트 시연용 가상 데이터', source_url=None, is_sample=True))
    session.commit()

if __name__ == '__main__':
    engine = make_engine()
    Base.metadata.create_all(engine)
    with session_factory(engine)() as session:
        seed(session)
    engine.dispose()
    print('Sample import complete (fresh DB: 3 themes, 4 fictional stocks, 5 links).')
