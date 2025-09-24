from activity_planner.gemini_planner import TitleCategorizer, GeminiClient, GeminiClientConfig
from activity_planner.models import Activity
from activity_planner.repositories import create_activity, create_title_mapping_rule
import httpx


class FakeClient(GeminiClient):  # inherit to reuse interface
    def __init__(self):  # type: ignore[override]
        pass

    def classify_title(self, title: str, candidate_categories):  # type: ignore[override]
        if "word" in title.lower():
            return {"category": "Reading", "confidence": 0.9, "raw": ""}
        return {"category": "Other", "confidence": 0.2, "raw": ""}


def test_title_categorizer_rule_short_circuit(db, qtbot):
    # Setup activities
    from activity_planner.activity_store import ActivityStore

    store = ActivityStore(db)
    store.load()
    reading = create_activity(db, Activity(id=None, title="Reading", description=None, effort_level=4))
    # Create rule mapping exact title
    create_title_mapping_rule(db, "Microsoft Word - Doc1", reading.id)  # type: ignore[arg-type]

    cat = TitleCategorizer(db, store, client=FakeClient())
    caught = {}

    def on_suggestion(category, confidence, original):
        caught["c"] = (category, confidence, original)

    cat.suggestion_ready.connect(on_suggestion)
    cat.submit_title("Microsoft Word - Doc1")
    # Manually force processing
    cat._process_next()  # type: ignore[attr-defined]
    assert caught["c"][0] == "Reading"
    assert caught["c"][1] == 1.0


def test_title_categorizer_model_path(db, qtbot):
    from activity_planner.activity_store import ActivityStore

    store = ActivityStore(db)
    # Create activities before load so initial load picks them up
    create_activity(db, Activity(id=None, title="Reading", description=None, effort_level=4))
    create_activity(db, Activity(id=None, title="Coding", description=None, effort_level=7))
    store.load()

    cat = TitleCategorizer(db, store, client=FakeClient(), confidence_threshold=0.5)
    results = {}

    def on_suggestion(category, confidence, original):
        results["r"] = (category, confidence, original)

    cat.suggestion_ready.connect(on_suggestion)
    cat.submit_title("Microsoft Word - notes")
    cat._process_next()  # type: ignore[attr-defined]
    assert results["r"][0] == "Reading"
    assert results["r"][1] >= 0.5
