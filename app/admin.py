import os
import secrets
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Path
from fastapi.security import APIKeyHeader
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from .models import Theme, Stock, ThemeStock
from .schemas import ThemeWrite, StockCreate, StockWrite, StockOut, EvidenceWrite, Evidence


def admin_router(sessions):
    key_header = APIKeyHeader(name='X-Admin-Key', auto_error=False)

    def authorize(key: Annotated[str | None, Depends(key_header)]):
        expected = os.getenv('ADMIN_API_KEY', '')
        if not expected.strip():
            raise HTTPException(503, 'Admin API is disabled')
        if key is None or not secrets.compare_digest(key.encode(), expected.encode()):
            raise HTTPException(401, 'Invalid administrator key')

    router = APIRouter(prefix='/api/admin', tags=['관리자'], dependencies=[Depends(authorize)])

    def get_session():
        with sessions() as session:
            yield session
    DB = Annotated[Session, Depends(get_session)]
    ThemeId = Annotated[int, Path(ge=1)]
    Code = Annotated[str, Path(pattern=r'^[0-9A-Z]{6}$')]

    def find(session, model, identity):
        item = session.get(model, identity)
        if item is None:
            raise HTTPException(404, 'Item not found')
        return item

    def save(session, item, values):
        for field, value in values.items():
            setattr(item, field, value)
        session.add(item)
        try:
            session.commit()
        except IntegrityError:
            session.rollback()
            raise HTTPException(409, 'Item already exists or conflicts with stored data') from None
        return item

    @router.post('/themes', status_code=201)
    def create_theme(body: ThemeWrite, session: DB):
        item = save(session, Theme(), body.model_dump())
        return dict(id=item.id, name=item.name, description=item.description)

    @router.put('/themes/{theme_id}')
    def update_theme(theme_id: ThemeId, body: ThemeWrite, session: DB):
        item = save(session, find(session, Theme, theme_id), body.model_dump())
        return dict(id=item.id, name=item.name, description=item.description)

    @router.post('/stocks', response_model=StockOut, status_code=201)
    def create_stock(body: StockCreate, session: DB):
        return save(session, Stock(), body.model_dump())

    @router.put('/stocks/{code}', response_model=StockOut)
    def update_stock(code: Code, body: StockWrite, session: DB):
        return save(session, find(session, Stock, code), body.model_dump())

    def evidence_values(body):
        return body.model_dump(mode='json')

    @router.post('/themes/{theme_id}/stocks/{code}', response_model=Evidence, status_code=201)
    def create_link(theme_id: ThemeId, code: Code, body: EvidenceWrite, session: DB):
        find(session, Theme, theme_id)
        find(session, Stock, code)
        return save(session, ThemeStock(theme_id=theme_id, stock_code=code), evidence_values(body))

    @router.put('/themes/{theme_id}/stocks/{code}', response_model=Evidence)
    def update_link(theme_id: ThemeId, code: Code, body: EvidenceWrite, session: DB):
        return save(session, find(session, ThemeStock, (theme_id, code)), evidence_values(body))

    return router
