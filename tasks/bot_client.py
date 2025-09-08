from __future__ import annotations

import requests
import os
from tasks.models import Assignment, Task


BOT_BASE_URL: str | None = os.environ.get('TASK_BOT_BASE_URL')
BOT_SEND_PATH: str = '/send-assignment'
BOT_HEALTH_PATH: str = '/health'


def bot_ping() -> bool:
    try:
        r = requests.get(f'{BOT_BASE_URL}{BOT_HEALTH_PATH}', timeout=5)
        if r.status_code == 200:
            data = r.json()
            return bool(data.get('bot_available', True))
        return False
    except Exception:
        return False


def bot_send_assignment(assignment_id: int) -> dict:
    if not Assignment.objects.filter(pk=assignment_id).exists():
        return {
            'assignment_id': assignment_id,
            'status': 'failed',
            'undelivered_tg': [],
            'error': 'assignment_not_found',
            'http_status': 404,
        }

    try:
        resp = requests.post(
            f'{BOT_BASE_URL}{BOT_SEND_PATH}',
            params={'argument': assignment_id},
            timeout=15,
        )

        if resp.status_code == 200:
            payload = resp.json()
            undelivered = payload.get('errors') or []
            return {
                'assignment_id': assignment_id,
                'status': 'sent' if not undelivered else 'partially_sent',
                'undelivered_tg': undelivered,
                'error': None,
                'http_status': 200,
            }

        try:
            payload = resp.json()
        except Exception:
            payload = {'detail': resp.text}

        return {
            'assignment_id': assignment_id,
            'status': 'failed',
            'undelivered_tg': [],
            'error': (payload.get('detail') if isinstance(payload, dict) else str(payload)) or 'unknown_error',
            'http_status': resp.status_code,
        }

    except Exception as e:
        return {
            'assignment_id': assignment_id,
            'status': 'failed',
            'undelivered_tg': [],
            'error': str(e),
            'http_status': None,
        }
