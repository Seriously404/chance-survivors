#!/usr/bin/env python3
"""
Test script to verify Bazaar UI rendering
This script tests the tab-based Bazaar implementation
"""

import sys
sys.path.insert(0, '/home/seriously404/chance-survivors')

from client.render import Renderer
import pygame

def test_bazaar_tab_structure():
    """Test that Bazaar tab structure is correct"""
    print("Testing Bazaar tab structure...")
    
    # Create a mock renderer instance to check method existence
    renderer_methods = dir(Renderer)
    
    # Check for new helper methods
    required_methods = [
        '_draw_bazaar_market',
        '_draw_bazaar_crates', 
        '_draw_bazaar_fusion'
    ]
    
    missing = []
    for method in required_methods:
        if method not in renderer_methods:
            missing.append(method)
    
    if missing:
        print(f"❌ Missing methods: {missing}")
        return False
    
    print("✅ All Bazaar tab methods exist")
    return True

def test_bazaar_menu_structure():
    """Test that _draw_bazaar_menu calls the correct helper methods"""
    import inspect
    from client.render import Renderer
    
    print("\nTesting _draw_bazaar_menu structure...")
    
    # Get source code
    source = inspect.getsource(Renderer._draw_bazaar_menu)
    
    # Check for tab-based structure
    checks = [
        ('_bazaar_tab', 'Tab state variable'),
        ('_draw_bazaar_market()', 'Market tab handler'),
        ('_draw_bazaar_crates()', 'Crates tab handler'),
        ('_draw_bazaar_fusion()', 'Fusion tab handler'),
    ]
    
    all_good = True
    for check, desc in checks:
        if check in source:
            print(f"✅ {desc} found")
        else:
            print(f"❌ {desc} missing")
            all_good = False
    
    return all_good

def main():
    """Run all tests"""
    print("=" * 60)
    print("Bazaar UI Refactoring Verification")
    print("=" * 60)
    
    results = []
    results.append(("Tab Structure", test_bazaar_tab_structure()))
    results.append(("Menu Structure", test_bazaar_menu_structure()))
    
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    
    all_passed = True
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name}")
        if not passed:
            all_passed = False
    
    print("=" * 60)
    
    if all_passed:
        print("\n🎉 All Bazaar UI tests passed!")
        return 0
    else:
        print("\n⚠️  Some tests failed")
        return 1

if __name__ == "__main__":
    exit(main())
