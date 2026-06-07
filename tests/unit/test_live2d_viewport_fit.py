from app.ui.live2d_viewport_fit import (
    compute_live2d_viewport_fit_scale,
    read_model_canvas_pixel_size,
)


class _ModelStub:
    def GetCanvasSizePixel(self) -> tuple[float, float]:
        return (2400.0, 4500.0)


def test_compute_live2d_viewport_fit_scale_fits_tall_canvas() -> None:
    scale = compute_live2d_viewport_fit_scale(360, 450, 2400.0, 4500.0)
    assert scale < 0.2
    assert scale > 0.05


def test_read_model_canvas_pixel_size() -> None:
    assert read_model_canvas_pixel_size(_ModelStub()) == (2400.0, 4500.0)
