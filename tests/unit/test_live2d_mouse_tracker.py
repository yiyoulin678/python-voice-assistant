from __future__ import annotations

from app.ui.live2d_mouse_tracker import compute_mouse_tracking_targets


def test_compute_mouse_tracking_targets_center_is_neutral() -> None:
    targets = compute_mouse_tracking_targets(
        local_x=100.0,
        local_y=150.0,
        width=200,
        height=300,
        max_angle=30.0,
    )
    assert targets.head_angle_x == 0.0
    assert targets.head_angle_y == 0.0
    assert targets.eye_ball_x == 0.0
    assert targets.eye_ball_y == 0.0


def test_compute_mouse_tracking_targets_follows_cursor() -> None:
    targets = compute_mouse_tracking_targets(
        local_x=180.0,
        local_y=60.0,
        width=200,
        height=300,
        max_angle=30.0,
        max_eye_offset=0.8,
        body_factor=0.4,
    )
    assert targets.head_angle_x > 0.0
    assert targets.head_angle_y > 0.0
    assert targets.body_angle_x > 0.0
    assert targets.body_angle_y > 0.0
    assert targets.eye_ball_x > 0.0
    assert targets.eye_ball_y > 0.0
    assert targets.body_angle_x == targets.head_angle_x * 0.4
