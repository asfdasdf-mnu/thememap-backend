import os
from contextlib import asynccontextmanager
from typing import Annotated
from fastapi import Depends, FastAPI, HTTPException, Path, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from sqlalchemy import func, select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from .database import Base, make_engine, session_factory
from .models import Stock, Theme, ThemeStock
from .schemas import StockDetail, ThemeList, ThemeStocks

def create_app(database_url=None):
    engine = make_engine(database_url)
    sessions = session_factory(engine)

    @asynccontextmanager
    async def lifespan(app):
        Base.metadata.create_all(engine)
        yield
        engine.dispose()

    app = FastAPI(title='ThemeMap 조회 API', version='0.1.0', lifespan=lifespan,
                  description='주식 테마 탐색 백엔드. 샘플은 가상 기업이며 실제 시세·투자 정보가 아닙니다.')
    app.state.engine = engine
    app.state.sessions = sessions
    origins = [s.strip() for s in os.getenv('CORS_ORIGINS', 'http://localhost:5173,http://127.0.0.1:5173').split(',') if s.strip()]
    app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=['GET'], allow_headers=['Content-Type'])

    def get_session():
        with sessions() as session:
            yield session
    DB = Annotated[Session, Depends(get_session)]

    def theme_summary(session, theme):
        count = session.scalar(select(func.count()).select_from(ThemeStock).where(ThemeStock.theme_id == theme.id))
        return dict(id=theme.id, name=theme.name, description=theme.description, stock_count=count)

    def evidence(link):
        return {key: getattr(link, key) for key in ('reason', 'source_title', 'source_url', 'is_sample')}

    @app.get('/health', tags=['상태'])
    def health(session: DB):
        try:
            session.execute(text('SELECT 1'))
        except SQLAlchemyError:
            raise HTTPException(503, 'Database unavailable') from None
        return dict(status='ok', database=engine.dialect.name, version='0.1.0')

    @app.get('/api/themes', response_model=ThemeList, tags=['테마'])
    def themes(session: DB, q: Annotated[str, Query(max_length=100)] = '',
               limit: Annotated[int, Query(ge=1, le=100)] = 20,
               offset: Annotated[int, Query(ge=0)] = 0):
        stmt = select(Theme)
        if q.strip():
            stmt = stmt.where(Theme.name.contains(q.strip(), autoescape=True))
        total = session.scalar(select(func.count()).select_from(stmt.subquery()))
        items = session.scalars(stmt.order_by(Theme.id).offset(offset).limit(limit))
        return dict(items=[theme_summary(session, t) for t in items], total=total, limit=limit, offset=offset)

    @app.get('/api/themes/{theme_id}/stocks', response_model=ThemeStocks, tags=['테마'])
    def theme_stocks(session: DB, theme_id: Annotated[int, Path(ge=1)]):
        theme = session.get(Theme, theme_id)
        if theme is None:
            raise HTTPException(404, 'Theme not found')
        rows = session.execute(select(Stock, ThemeStock).join(ThemeStock, Stock.code == ThemeStock.stock_code)
                               .where(ThemeStock.theme_id == theme_id).order_by(Stock.code))
        return dict(theme=theme_summary(session, theme), items=[dict(code=s.code, name=s.name, market=s.market, description=s.description, **evidence(link)) for s, link in rows])

    @app.get('/api/stocks/{code}', response_model=StockDetail, tags=['종목'])
    def stock_detail(session: DB, code: Annotated[str, Path(pattern=r'^[0-9]{6}$')]):
        stock = session.get(Stock, code)
        if stock is None:
            raise HTTPException(404, 'Stock not found')
        rows = session.execute(select(Theme, ThemeStock).join(ThemeStock, Theme.id == ThemeStock.theme_id)
                               .where(ThemeStock.stock_code == code).order_by(Theme.id))
        return dict(code=stock.code, name=stock.name, market=stock.market, description=stock.description,
                    themes=[dict(id=t.id, name=t.name, **evidence(link)) for t, link in rows])

    @app.get('/', response_class=HTMLResponse, include_in_schema=False)
    def home():
        return '''<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>ThemeMap API</title>
        <style>body{font-family:system-ui,sans-serif;background:#f3f6fa;color:#192c46;max-width:850px;margin:10vh auto;padding:24px}h1{font-size:46px}a{color:#12634e}li{margin:18px 0}small{color:#526477}</style>
        <small>THEMEMAP · BACKEND PROTOTYPE · v0.1.0</small><h1>주식 테마 탐색 API</h1><p>테마와 종목의 연결 관계를 조회하는 백엔드 시연입니다.</p>
        <p>샘플은 모두 가상 기업입니다. 실제 주가·공시 데이터는 아직 연결하지 않았습니다.</p>
        <ul><li><a href="/docs">API 문서에서 직접 요청하기</a></li><li><a href="/api/themes">테마 목록</a></li><li><a href="/api/themes/1/stocks">반도체 테마의 관련 종목</a></li><li><a href="/api/stocks/900001">두 테마에 연결된 가상 종목</a></li><li><a href="/health">서버·DB 연결 확인</a></li></ul></html>'''
    return app

app = create_app()
