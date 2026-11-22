"""Profile: per-topic knowledge-point progress."""

from __future__ import annotations

from fastapi import APIRouter, Request

from ..deps import CurrentUser, StorageDep
from ...practice.generate import load_knowledge_points

router = APIRouter(tags=["profile"])


@router.get(
    "/api/profile/mastery",
    summary="The signed-in user's per-topic knowledge-point progress",
    responses={401: {"description": "Not signed in."}},
)
def mastery(user: CurrentUser, storage: StorageDep, request: Request):
    """Return each topic's total, covered, and mastered knowledge points."""

    settings = request.app.state.settings
    points = load_knowledge_points(settings.repo_root)

    by_topic: dict[str, dict[str, set[str]]] = {}
    for row in storage.list_progress(user["id"]):
        entry = by_topic.setdefault(
            row["topic"], {"covered": set(), "mastered": set()}
        )
        if row["covered"]:
            entry["covered"].add(row["knowledge_point"])
        if row["mastered"]:
            entry["mastered"].add(row["knowledge_point"])

    topics = []
    for topic, point_list in points.items():
        entry = by_topic.get(topic, {"covered": set(), "mastered": set()})
        topics.append(
            {
                "topic": topic,
                "total": len(point_list),
                "covered_count": len(entry["covered"]),
                "mastered_count": len(entry["mastered"]),
            }
        )
    return {"topics": topics}
