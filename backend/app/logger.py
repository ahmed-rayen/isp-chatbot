import logging
import json
from datetime import datetime

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_record = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "message": record.getMessage()
        }
        if hasattr(record, 'session_id'): log_record["session_id"] = record.session_id
        if hasattr(record, 'user_id'): log_record["user_id"] = record.user_id
        if hasattr(record, 'tool_name'): log_record["tool_name"] = record.tool_name
        if hasattr(record, 'latency_ms'): log_record["latency_ms"] = record.latency_ms
        return json.dumps(log_record)

logger = logging.getLogger("ISP_Bot")
handler = logging.StreamHandler()
handler.setFormatter(JSONFormatter())
logger.addHandler(handler)
logger.setLevel(logging.INFO)