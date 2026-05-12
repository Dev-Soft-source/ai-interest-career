from utils import sanitize_user_facing_text


def test_sanitize_user_facing_text_removes_parenthetical_item_ranges():
    text = (
        "Your strong preference for helping others, evident in advising and mediating (E1-E8), "
        "aligns well with the social worker role."
    )
    cleaned = sanitize_user_facing_text(text)
    assert "E1" not in cleaned
    assert "E8" not in cleaned
    assert "advising and mediating" in cleaned


def test_sanitize_user_facing_text_removes_single_item_codes():
    assert "A1" not in sanitize_user_facing_text("Creation items A1 and A2 stood out.")
    assert "Creation items and stood out." in sanitize_user_facing_text(
        "Creation items A1 and A2 stood out."
    )
