"""evaluation: golden set, DeepEval metrics (Claude judge via the gateway), runner, reports.

Layer: application (top). May use: generation, extraction, ingestion, retrieval, lower layers, core.
ADR: 0008.
"""

import os

# DeepEval sends anonymous telemetry to its vendor by default; this project opts out.
os.environ.setdefault("DEEPEVAL_TELEMETRY_OPT_OUT", "YES")
os.environ.setdefault("DEEPEVAL_UPDATE_WARNING_OPT_IN", "NO")
# DeepEval bounds a whole evaluate() batch by the per-task budget (default 180 s) plus a 30 s
# buffer; 15+ cases x 5 judged metrics at 4 concurrent calls take longer and get cancelled.
os.environ.setdefault("DEEPEVAL_PER_TASK_TIMEOUT_SECONDS_OVERRIDE", "1200")
