"""License-aware access policy on OpenFGA (ADR-0007), via the official `openfga-sdk`.

- pre-filter:  `ListObjects(user, can_read, paper)` → readable paper ids → Qdrant payload filter
- post-filter: `BatchCheck` over the final sources (defense in depth)
- ingestion:   each paper is linked to its license collection (`paper:<id>#collection`)

The model, base memberships and authorization tests live in `infra/openfga/store.fga.yaml`.
"""

from collections.abc import Iterable
from functools import lru_cache
from pathlib import Path
from typing import Protocol

import yaml
from openfga_sdk.client import ClientConfiguration
from openfga_sdk.client.models import (
    ClientBatchCheckItem,
    ClientBatchCheckRequest,
    ClientListObjectsRequest,
    ClientTuple,
    ClientWriteRequest,
    ClientWriteRequestOnDuplicateWrites,
    ClientWriteRequestOnMissingDeletes,
    ConflictOptions,
)
from openfga_sdk.models.read_request_tuple_key import ReadRequestTupleKey
from openfga_sdk.sync import OpenFgaClient

from sdlcrag.core.config import get_settings
from sdlcrag.core.models import Classification, DemoPrincipal, Principal

WRITE_BATCH = 100  # OpenFGA's per-request tuple limit


class AccessPolicy(Protocol):
    def readable_paper_ids(self, principal: Principal) -> list[str]: ...

    def can_read(self, principal: Principal, paper_ids: Iterable[str]) -> dict[str, bool]: ...

    def register_papers(self, papers: dict[str, Classification]) -> None: ...

    def unregister_paper(self, paper_id: str) -> None: ...


def _paper(paper_id: str) -> str:
    return f"paper:{paper_id}"


def _user(principal: Principal) -> str:
    return f"user:{principal.user_id}"


class OpenFGAAccessPolicy:
    def __init__(self, client: OpenFgaClient) -> None:
        self._client = client

    def readable_paper_ids(self, principal: Principal) -> list[str]:
        response = self._client.list_objects(
            ClientListObjectsRequest(user=_user(principal), relation="can_read", type="paper")
        )
        return [obj.split(":", 1)[1] for obj in response.objects]

    def can_read(self, principal: Principal, paper_ids: Iterable[str]) -> dict[str, bool]:
        ids = list(dict.fromkeys(paper_ids))
        if not ids:
            return {}
        response = self._client.batch_check(
            ClientBatchCheckRequest(
                checks=[
                    ClientBatchCheckItem(
                        user=_user(principal), relation="can_read", object=_paper(i)
                    )
                    for i in ids
                ]
            )
        )
        allowed = {r.request.object.split(":", 1)[1]: bool(r.allowed) for r in response.result}
        return {i: allowed.get(i, False) for i in ids}

    def register_papers(self, papers: dict[str, Classification]) -> None:
        tuples = [
            ClientTuple(user=f"collection:{cls.value}", relation="collection", object=_paper(pid))
            for pid, cls in papers.items()
        ]
        for start in range(0, len(tuples), WRITE_BATCH):
            self._client.write(
                ClientWriteRequest(writes=tuples[start : start + WRITE_BATCH]),
                options={
                    # openfga-sdk requires ConflictOptions at runtime but its hint says dict
                    "conflict": ConflictOptions(  # pyrefly: ignore[bad-assignment]
                        on_duplicate_writes=ClientWriteRequestOnDuplicateWrites.IGNORE
                    )
                },
            )

    def unregister_paper(self, paper_id: str) -> None:
        response = self._client.read(ReadRequestTupleKey(object=_paper(paper_id)))
        deletes = [
            ClientTuple(user=t.key.user, relation=t.key.relation, object=t.key.object)
            for t in response.tuples
        ]
        if deletes:
            self._client.write(
                ClientWriteRequest(deletes=deletes),
                options={
                    "conflict": ConflictOptions(  # pyrefly: ignore[bad-assignment]
                        on_missing_deletes=ClientWriteRequestOnMissingDeletes.IGNORE
                    )
                },
            )


@lru_cache
def get_access_policy() -> AccessPolicy:
    """The configured policy. Fails closed: without an OpenFGA store nothing is readable."""
    s = get_settings()
    if not (s.openfga_store_id and s.openfga_model_id):
        raise RuntimeError(
            "OpenFGA is not configured (SDLCRAG_OPENFGA_STORE_ID / _MODEL_ID); "
            "run infra/openfga/bootstrap.sh"
        )
    client = OpenFgaClient(
        ClientConfiguration(
            api_url=s.openfga_api_url,
            store_id=s.openfga_store_id,
            authorization_model_id=s.openfga_model_id,
        )
    )
    return OpenFGAAccessPolicy(client)


@lru_cache
def demo_principals(path: Path) -> list[DemoPrincipal]:
    """Demo users (data/corpus.yaml); their group memberships live in the OpenFGA store."""
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return [DemoPrincipal.model_validate(p) for p in data.get("principals", [])]
