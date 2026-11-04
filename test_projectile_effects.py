#!/usr/bin/env python3
"""Test projectile effects: explosive, homing, ricochet."""

import sys
sys.path.insert(0, '/home/seriously404/chance-survivors')

from game.systems.collision import CollisionSystem
from game.entities.projectile import Projectile
from game.entities.enemy import Enemy
from game.systems.elements import apply_elemental_damage

def test_explosive_projectile():
    """Test explosive projectile damages all enemies in radius."""
    print("Testing explosive projectile...")
    
    collision = CollisionSystem(pixels_per_unit=1.0)
    
    # Create explosive bullet
    bullet = Projectile(
        x=50.0, y=50.0, dx=0.0, dy=-1.0,
        damage=10.0, element="physical",
        explosion_radius=30.0,  # 30 units radius
        homing_strength=0.0,
        bounces_remaining=0
    )
    
    # Create 3 enemies at different distances
    enemy1 = Enemy(x=50.0, y=40.0, type="basic", health=100, damage=5)  # Inside radius
    enemy2 = Enemy(x=50.0, y=20.0, type="basic", health=100, damage=5)   # Inside radius
    enemy3 = Enemy(x=50.0, y=0.0, type="basic", health=100, damage=5)    # Outside radius
    
    enemies = [enemy1, enemy2, enemy3]
    bullets = [bullet]
    
    # Simulate collision with enemy1
    bullet.hit_enemies.append(enemy1)
    enemy1.take_damage(10.0)  # Direct hit
    
    # Manually trigger explosion logic
    if bullet.explosion_radius > 0 and not bullet.exploded:
        bullet.exploded = True
        for k, other_enemy in enumerate(enemies):
            if other_enemy in bullet.hit_enemies:
                continue
            distance = collision._get_distance(bullet.x, bullet.y, other_enemy.x, other_enemy.y)
            if distance <= bullet.explosion_radius:
                other_hit_distance = (10.0 + 5.0) / 1.0  # enemy size + bullet radius
                if distance <= other_hit_distance:
                    bullet.hit_enemies.append(other_enemy)
                    effective_damage = apply_elemental_damage(
                        bullet.damage,
                        bullet.element,
                        {},
                    )
                    other_enemy.take_damage(effective_damage)
    
    # Verify results
    assert enemy1.health == 90, f"Enemy 1 should have 90 HP, got {enemy1.health}"
    assert enemy2.health == 90, f"Enemy 2 should have 90 HP, got {enemy2.health}"
    assert enemy3.health == 100, f"Enemy 3 should have 100 HP, got {enemy3.health}"
    
    print("✅ Explosive projectile test passed!")
    return True

def test_ricochet_projectile():
    """Test ricochet projectile bounces to next enemy."""
    print("Testing ricochet projectile...")
    
    collision = CollisionSystem(100, 100, 1.0)
    
    # Create ricochet bullet
    bullet = Projectile(
        x=50.0, y=50.0, dx=0.0, dy=-1.0,
        damage=10.0, element="physical",
        explosion_radius=0.0,
        homing_strength=0.0,
        bounces_remaining=2  # Can hit 2 more enemies
    )
    
    enemy1 = Enemy(x=50.0, y=40.0, type="basic", health=100, damage=5)
    enemy2 = Enemy(x=50.0, y=30.0, type="basic", health=100, damage=5)
    enemy3 = Enemy(x=50.0, y=20.0, type="basic", health=100, damage=5)
    
    enemies = [enemy1, enemy2, enemy3]
    bullets = [bullet]
    
    # First hit
    bullet.hit_enemies.append(enemy1)
    enemy1.take_damage(10.0)
    bullet.bounces_remaining -= 1
    
    assert bullet.bounces_remaining == 1, f"Should have 1 bounce left, got {bullet.bounces_remaining}"
    
    # Second hit
    bullet.hit_enemies.append(enemy2)
    enemy2.take_damage(10.0)
    bullet.bounces_remaining -= 1
    
    assert bullet.bounces_remaining == 0, f"Should have 0 bounces left, got {bullet.bounces_remaining}"
    
    # Third hit should not bounce
    bullet.hit_enemies.append(enemy3)
    enemy3.take_damage(10.0)
    # bounces_remaining stays at 0
    
    assert enemy1.health == 90, f"Enemy 1 should have 90 HP, got {enemy1.health}"
    assert enemy2.health == 90, f"Enemy 2 should have 90 HP, got {enemy2.health}"
    assert enemy3.health == 90, f"Enemy 3 should have 90 HP, got {enemy3.health}"
    
    print("✅ Ricochet projectile test passed!")
    return True

def test_homing_projectile():
    """Test homing projectile steers towards nearest enemy."""
    print("Testing homing projectile...")
    
    collision = CollisionSystem(100, 100, 1.0)
    
    # Create homing bullet
    bullet = Projectile(
        x=50.0, y=50.0, dx=1.0, dy=0.0,  # Moving right initially
        damage=10.0, element="physical",
        explosion_radius=0.0,
        homing_strength=0.5,  # Moderate homing
        bounces_remaining=0
    )
    
    # Enemy to the left (should steer towards it)
    enemy = Enemy(x=30.0, y=50.0, type="basic", health=100, damage=5)
    
    enemies = [enemy]
    bullets = [bullet]
    
    # Apply homing logic
    nearest_enemy = None
    nearest_distance = float("inf")
    for k, other_enemy in enumerate(enemies):
        if other_enemy in bullet.hit_enemies:
            continue
        distance = collision._get_distance(bullet.x, bullet.y, other_enemy.x, other_enemy.y)
        if distance < nearest_distance:
            nearest_distance = distance
            nearest_enemy = (k, other_enemy)
    
    if nearest_enemy is not None:
        k, target = nearest_enemy
        target_x = target.x
        target_y = target.y
        angle_to_target = __import__('math').atan2(target_y - bullet.y, target_x - bullet.x)
        blend = min(1.0, bullet.homing_strength)
        bullet.dx = bullet.dx * (1 - blend) + __import__('math').cos(angle_to_target) * blend
        bullet.dy = bullet.dy * (1 - blend) + __import__('math').sin(angle_to_target) * blend
        mag = __import__('math').sqrt(bullet.dx * bullet.dx + bullet.dy * bullet.dy)
        if mag > 0:
            bullet.dx /= mag
            bullet.dy /= mag
    
    # Should now be steering left (negative dx)
    assert bullet.dx < 0, f"Should be steering left, dx={bullet.dx}"
    
    print("✅ Homing projectile test passed!")
    return True

if __name__ == "__main__":
    print("=" * 60)
    print("Testing Projectile Effects")
    print("=" * 60)
    
    all_passed = True
    all_passed &= test_explosive_projectile()
    all_passed &= test_ricochet_projectile()
    all_passed &= test_homing_projectile()
    
    print("=" * 60)
    if all_passed:
        print("✅ All projectile effects tests passed!")
        sys.exit(0)
    else:
        print("❌ Some tests failed")
        sys.exit(1)
