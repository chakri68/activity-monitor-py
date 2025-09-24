from activity_planner.planner_page import parse_timetable_response, detect_overlaps, Slot


def test_parse_timetable_response_extracts_slots():
    sample = "Here is your plan:\n[ {\"activity\": \"Coding\", \"start\": \"09:00\", \"end\": \"10:00\"}, {\"activity\": \"Reading\", \"start\": \"10:00\", \"end\": \"11:00\"} ]"
    slots, warning = parse_timetable_response(sample)
    assert len(slots) == 2
    assert slots[0].activity == "Coding"
    assert not warning


def test_parse_timetable_response_warning():
    sample = "Too many tasks to be chill today 😭 [ {\"activity\": \"Coding\", \"start\": \"09:00\", \"end\": \"10:00\"} ]"
    slots, warning = parse_timetable_response(sample)
    assert warning


def test_detect_overlaps():
    slots = [Slot("A", "09:00", "10:00"), Slot("B", "09:50", "10:30")]
    assert detect_overlaps(slots) is True
    slots2 = [Slot("A", "09:00", "10:00"), Slot("B", "10:00", "10:30")]
    assert detect_overlaps(slots2) is False
