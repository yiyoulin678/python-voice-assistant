from __future__ import annotations

LIVE2D_VIEWPORT_FIT_MARGIN = 0.9


def compute_live2d_viewport_fit_scale(
    viewport_width: int,
    viewport_height: int,
    canvas_pixel_width: float,
    canvas_pixel_height: float,
    *,
    margin: float = LIVE2D_VIEWPORT_FIT_MARGIN,
) -> float:
    """按视口尺寸把 Live2D 画布等比缩放到完整可见。"""

    if (
        viewport_width <= 0
        or viewport_height <= 0
        or canvas_pixel_width <= 0
        or canvas_pixel_height <= 0
    ):
        return 1.0
    fit = min(
        viewport_width / canvas_pixel_width,
        viewport_height / canvas_pixel_height,
    )
    return max(0.02, fit * margin)


def read_model_canvas_pixel_size(model: object) -> tuple[float, float] | None:
    get_pixel_size = getattr(model, "GetCanvasSizePixel", None)
    if callable(get_pixel_size):
        try:
            pixel_size = get_pixel_size()
            if pixel_size and len(pixel_size) >= 2:
                width = float(pixel_size[0])
                height = float(pixel_size[1])
                if width > 0 and height > 0:
                    return width, height
        except Exception:
            pass

    get_canvas_size = getattr(model, "GetCanvasSize", None)
    get_pixels_per_unit = getattr(model, "GetPixelsPerUnit", None)
    if not callable(get_canvas_size) or not callable(get_pixels_per_unit):
        return None
    try:
        canvas_size = get_canvas_size()
        pixels_per_unit = float(get_pixels_per_unit())
        if not canvas_size or len(canvas_size) < 2 or pixels_per_unit <= 0:
            return None
        width = float(canvas_size[0]) * pixels_per_unit
        height = float(canvas_size[1]) * pixels_per_unit
        if width > 0 and height > 0:
            return width, height
    except Exception:
        return None
    return None
