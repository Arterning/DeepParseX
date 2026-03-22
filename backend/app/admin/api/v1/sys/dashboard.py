from datetime import timedelta

from backend.common.security.jwt import DependsJwtAuth
from backend.common.response.response_schema import ResponseModel, response_base
from backend.app.admin.service.doc_service import sys_doc_service
from fastapi import APIRouter, Request
from backend.database.db_pg import async_db_session
from backend.utils.timezone import timezone

router = APIRouter()


@router.get('/count', summary='获取首页面板数据',
    dependencies=[DependsJwtAuth]
 )
async def get_dashboard_index(request: Request) -> ResponseModel:
    user_id = request.user.id
    is_superuser = request.user.is_superuser
    data = await sys_doc_service.get_count(user_id=user_id, is_superuser=is_superuser)
    return response_base.success(data=data)


@router.get('/stats', summary='获取处理进度与定时任务统计',
    dependencies=[DependsJwtAuth]
)
async def get_processing_stats() -> ResponseModel:
    from sqlalchemy import select, func
    from backend.app.admin.model.sys_doc import SysDoc
    from backend.app.admin.model.sys_scheduler_log import SysSchedulerLog

    async with async_db_session() as db:
        # ── 文档处理进度 ──
        base = select(func.count()).select_from(SysDoc).where(SysDoc.status == 1)
        total = (await db.execute(base)).scalar() or 0
        entity_done = (await db.execute(
            select(func.count()).select_from(SysDoc)
            .where(SysDoc.status == 1, SysDoc.entity_extracted == 1)
        )).scalar() or 0
        graph_done = (await db.execute(
            select(func.count()).select_from(SysDoc)
            .where(SysDoc.status == 1, SysDoc.graph_extracted == 1)
        )).scalar() or 0
        summary_done = (await db.execute(
            select(func.count()).select_from(SysDoc)
            .where(SysDoc.status == 1, SysDoc.desc.isnot(None))
        )).scalar() or 0
        translation_done = (await db.execute(
            select(func.count()).select_from(SysDoc)
            .where(SysDoc.status == 1, SysDoc.translation.isnot(None))
        )).scalar() or 0

        # ── 定时任务统计（最近24小时）──
        since = timezone.now() - timedelta(hours=24)
        rows = (await db.execute(
            select(
                SysSchedulerLog.job_id,
                SysSchedulerLog.job_name,
                func.count().label('runs'),
                func.sum(SysSchedulerLog.processed).label('total_processed'),
                func.sum(SysSchedulerLog.success).label('total_success'),
                func.sum(SysSchedulerLog.error).label('total_error'),
                func.avg(SysSchedulerLog.duration_ms).label('avg_duration_ms'),
                func.max(SysSchedulerLog.started_at).label('last_run_at'),
            )
            # .where(SysSchedulerLog.started_at >= since)
            .where(SysSchedulerLog.status != 'running')
            .group_by(SysSchedulerLog.job_id, SysSchedulerLog.job_name)
            .order_by(SysSchedulerLog.job_id)
        )).all()

        MS_PER_DAY = 24 * 60 * 60 * 1000
        scheduler_stats = []
        for r in rows:
            avg_ms = int(r.avg_duration_ms or 0)
            batch = int(r.total_processed or 0)
            runs = r.runs or 0
            avg_batch_size = round(batch / runs) if runs else 0
            # 吞吐量 = (一天毫秒数 / 平均每批耗时) × 平均每批处理量
            daily_throughput = round((MS_PER_DAY / avg_ms) * avg_batch_size) if avg_ms and avg_batch_size else 0
            avg_per_doc_ms = round(avg_ms / avg_batch_size) if avg_ms and avg_batch_size else 0
            scheduler_stats.append({
                'job_id': r.job_id,
                'job_name': r.job_name,
                'runs': runs,
                'total_processed': batch,
                'total_success': int(r.total_success or 0),
                'total_error': int(r.total_error or 0),
                'avg_duration_ms': avg_ms,
                'daily_throughput': daily_throughput,
                'avg_per_doc_ms': avg_per_doc_ms,
                'last_run_at': r.last_run_at.isoformat() if r.last_run_at else None,
            })

    return response_base.success(data={
        'doc_stats': {
            'total': total,
            'entity_extracted': entity_done,
            'graph_extracted': graph_done,
            'has_summary': summary_done,
            'has_translation': translation_done,
        },
        'scheduler_stats': scheduler_stats,
    })

