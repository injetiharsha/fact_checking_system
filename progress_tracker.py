import threading
import time


def _stage_templates(mode):
    if mode == "image":
        return [
            {"id": "input", "label": "Input"},
            {"id": "ocr", "label": "OCR"},
            {"id": "claim_selection", "label": "Claim Selection"},
            {"id": "language", "label": "Language"},
            {"id": "structured_api", "label": "Structured APIs"},
            {"id": "web_search", "label": "Web Search"},
            {"id": "extraction", "label": "Extraction"},
            {"id": "relevance", "label": "Relevance"},
            {"id": "stance", "label": "Stance"},
            {"id": "verdict", "label": "Verdict"},
        ]
    if mode == "pdf":
        return [
            {"id": "input", "label": "Input"},
            {"id": "document_parse", "label": "Document Parsing"},
            {"id": "claim_selection", "label": "Claim Selection"},
            {"id": "language", "label": "Language"},
            {"id": "structured_api", "label": "Structured APIs"},
            {"id": "web_search", "label": "Web Search"},
            {"id": "extraction", "label": "Extraction"},
            {"id": "relevance", "label": "Relevance"},
            {"id": "stance", "label": "Stance"},
            {"id": "verdict", "label": "Verdict"},
        ]
    return [
        {"id": "input", "label": "Input"},
        {"id": "language", "label": "Language"},
        {"id": "structured_api", "label": "Structured APIs"},
        {"id": "web_search", "label": "Web Search"},
        {"id": "extraction", "label": "Extraction"},
        {"id": "relevance", "label": "Relevance"},
        {"id": "stance", "label": "Stance"},
        {"id": "verdict", "label": "Verdict"},
    ]


class ProgressTracker:
    def __init__(self):
        self._lock = threading.Lock()
        self._items = {}

    def start(self, progress_id, mode, preview=""):
        now = time.time()
        with self._lock:
            self._items[progress_id] = {
                "progress_id": progress_id,
                "mode": mode,
                "preview": preview,
                "status": "running",
                "started_at": now,
                "updated_at": now,
                "stages": [
                    {
                        "id": row["id"],
                        "label": row["label"],
                        "status": "pending",
                        "detail": "",
                        "substeps": [],
                    }
                    for row in _stage_templates(mode)
                ],
            }

    def emit(self, progress_id, stage, status=None, detail=None, substep=None, substatus=None):
        now = time.time()
        with self._lock:
            item = self._items.get(progress_id)
            if not item:
                return
            item["updated_at"] = now
            stage_row = None
            for row in item["stages"]:
                if row["id"] == stage:
                    stage_row = row
                    break
            if stage_row is None:
                stage_row = {
                    "id": stage,
                    "label": stage.replace("_", " ").title(),
                    "status": "pending",
                    "detail": "",
                    "substeps": [],
                }
                item["stages"].append(stage_row)
            if status:
                if status == "active":
                    for row in item["stages"]:
                        if row is not stage_row and row.get("status") == "active":
                            row["status"] = "done"
                if status == "pending" and not substep:
                    stage_row["substeps"] = []
                stage_row["status"] = status
            if detail is not None:
                stage_row["detail"] = str(detail)
            if substep:
                sub_row = None
                for row in stage_row["substeps"]:
                    if row["id"] == substep:
                        sub_row = row
                        break
                if sub_row is None:
                    sub_row = {
                        "id": substep,
                        "label": substep.replace("_", " ").title(),
                        "status": "pending",
                        "detail": "",
                    }
                    stage_row["substeps"].append(sub_row)
                if substatus:
                    sub_row["status"] = substatus
                elif status:
                    sub_row["status"] = status
                if detail is not None:
                    sub_row["detail"] = str(detail)

    def complete(self, progress_id, detail="Analysis complete"):
        now = time.time()
        with self._lock:
            item = self._items.get(progress_id)
            if not item:
                return
            item["status"] = "done"
            item["updated_at"] = now
            item["completed_at"] = now
            item["final_detail"] = detail
            for row in item["stages"]:
                if row["status"] == "active":
                    row["status"] = "done"

    def error(self, progress_id, detail="Analysis failed"):
        now = time.time()
        with self._lock:
            item = self._items.get(progress_id)
            if not item:
                return
            item["status"] = "error"
            item["updated_at"] = now
            item["final_detail"] = detail

    def cancel(self, progress_id, detail="Analysis cancelled"):
        now = time.time()
        with self._lock:
            item = self._items.get(progress_id)
            if not item:
                return
            item["status"] = "cancelled"
            item["updated_at"] = now
            item["final_detail"] = detail

    def get(self, progress_id):
        with self._lock:
            item = self._items.get(progress_id)
            if not item:
                return None
            return {
                **item,
                "stages": [
                    {
                        **row,
                        "substeps": [dict(sub) for sub in row.get("substeps", [])],
                    }
                    for row in item.get("stages", [])
                ],
            }


progress_tracker = ProgressTracker()
