#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from sqlalchemy import select, Select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy_crud_plus import CRUDPlus

from backend.app.admin.model.sys_text2sql_table import Text2SQLTable
from backend.app.admin.model.sys_text2sql_column import Text2SQLColumn
from backend.app.admin.model.sys_text2sql_example import Text2SQLExample
from backend.app.admin.model.sys_text2sql_query_log import Text2SQLQueryLog


class CRUDText2SQLTable(CRUDPlus[Text2SQLTable]):
    async def get(self, db: AsyncSession, pk: int) -> Text2SQLTable | None:
        return await self.select_model(db, pk)

    async def update(self, db: AsyncSession, pk: int, obj_in) -> int:
        return await self.update_model(db, pk, obj_in)

    async def delete(self, db: AsyncSession, pk: int) -> int:
        return await self.delete_model_by_column(db, id=pk)

    async def get_with_columns(self, db: AsyncSession, pk: int) -> Text2SQLTable | None:
        result = await db.execute(
            select(self.model)
            .options(selectinload(self.model.columns))
            .where(self.model.id == pk)
        )
        return result.scalars().first()

    async def get_active_with_columns(self, db: AsyncSession) -> list[Text2SQLTable]:
        result = await db.execute(
            select(self.model)
            .options(selectinload(self.model.columns))
            .where(self.model.is_active == True)
        )
        return list(result.scalars().all())

    def get_list(self) -> Select:
        return select(self.model).order_by(desc(self.model.created_time))

    async def get_by_table_name(
        self, db: AsyncSession, schema_name: str, table_name: str
    ) -> Text2SQLTable | None:
        result = await db.execute(
            select(self.model).where(
                self.model.schema_name == schema_name,
                self.model.table_name == table_name,
            )
        )
        return result.scalars().first()

    async def get_all_table_names(self, db: AsyncSession) -> list[tuple[str, str]]:
        result = await db.execute(select(self.model.schema_name, self.model.table_name))
        return list(result.all())

    async def vector_search(
        self, db: AsyncSession, embedding: list[float], top_k: int = 10
    ) -> list[Text2SQLTable]:
        result = await db.execute(
            select(self.model)
            .options(selectinload(self.model.columns))
            .where(self.model.is_active == True, self.model.embedding != None)
            .order_by(self.model.embedding.cosine_distance(embedding))
            .limit(top_k)
        )
        return list(result.scalars().all())

    async def keyword_search(
        self, db: AsyncSession, keywords: list[str], top_k: int = 10
    ) -> list[Text2SQLTable]:
        if not keywords:
            return []
        from sqlalchemy import or_
        conditions = [
            self.model.description.ilike(f'%{kw}%') for kw in keywords
        ] + [
            self.model.display_name.ilike(f'%{kw}%') for kw in keywords
        ] + [
            self.model.table_name.ilike(f'%{kw}%') for kw in keywords
        ]
        result = await db.execute(
            select(self.model)
            .options(selectinload(self.model.columns))
            .where(self.model.is_active == True, or_(*conditions))
            .limit(top_k)
        )
        return list(result.scalars().all())


class CRUDText2SQLColumn(CRUDPlus[Text2SQLColumn]):
    async def update(self, db: AsyncSession, pk: int, obj_in) -> int:
        return await self.update_model(db, pk, obj_in)

    async def get_by_table(self, db: AsyncSession, table_id: int) -> list[Text2SQLColumn]:
        result = await db.execute(
            select(self.model)
            .where(self.model.table_id == table_id)
            .order_by(self.model.ordinal_position)
        )
        return list(result.scalars().all())

    async def delete_by_table(self, db: AsyncSession, table_id: int) -> None:
        from sqlalchemy import delete
        await db.execute(delete(self.model).where(self.model.table_id == table_id))


class CRUDText2SQLExample(CRUDPlus[Text2SQLExample]):
    async def get(self, db: AsyncSession, pk: int) -> Text2SQLExample | None:
        return await self.select_model(db, pk)

    async def delete(self, db: AsyncSession, pk: int) -> int:
        return await self.delete_model_by_column(db, id=pk)

    def get_list(self) -> Select:
        return select(self.model).order_by(desc(self.model.created_time))

    async def vector_search(
        self, db: AsyncSession, embedding: list[float], top_k: int = 3
    ) -> list[Text2SQLExample]:
        result = await db.execute(
            select(self.model)
            .where(self.model.question_embedding != None)
            .order_by(self.model.question_embedding.cosine_distance(embedding))
            .limit(top_k)
        )
        return list(result.scalars().all())


class CRUDText2SQLQueryLog(CRUDPlus[Text2SQLQueryLog]):
    async def get(self, db: AsyncSession, pk: int) -> Text2SQLQueryLog | None:
        return await self.select_model(db, pk)

    def get_list(self, user_id: int | None = None) -> Select:
        stmt = select(self.model).order_by(desc(self.model.created_time))
        if user_id is not None:
            stmt = stmt.where(self.model.create_user == user_id)
        return stmt


crud_text2sql_table = CRUDText2SQLTable(Text2SQLTable)
crud_text2sql_column = CRUDText2SQLColumn(Text2SQLColumn)
crud_text2sql_example = CRUDText2SQLExample(Text2SQLExample)
crud_text2sql_query_log = CRUDText2SQLQueryLog(Text2SQLQueryLog)
