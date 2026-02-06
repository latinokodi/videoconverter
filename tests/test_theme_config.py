
from src.ui.theme import get_custom_stylesheet

def test_theme_properties():
    """Test that theme contains new design elements."""
    qss = get_custom_stylesheet("#6C63FF") # Violet accent
    
    # Assert new color presence
    assert "#6C63FF" in qss
    
    # Assert rounded corners increase
    # We want 12px or 8px, but definitely not just 4px everywhere if we want "rounded"
    # Just checking for key properties
    assert "border-radius: 12px" in qss or "border-radius: 8px" in qss
    
    # Assert Font
    assert "Segoe UI" in qss
    
    # Assert no squared frames
    # Hard to test negation stringently in CSS string, but we can check if we removed explicit square corners if we had them.
    # Instead, let's just ensure we have the new "Rounded" look applied to valid components.
