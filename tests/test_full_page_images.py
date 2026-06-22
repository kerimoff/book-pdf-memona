import unittest

from api.layout import get_full_page_image_rect, should_draw_full_page_image


class FullPageImageTests(unittest.TestCase):
    def test_exact_page_ratio_uses_full_page(self):
        self.assertTrue(should_draw_full_page_image(800, 1000, 800, 1000))

    def test_ten_percent_wider_uses_full_page(self):
        self.assertTrue(should_draw_full_page_image(880, 1000, 800, 1000))

    def test_more_than_ten_percent_wider_uses_contained_layout(self):
        self.assertFalse(should_draw_full_page_image(881, 1000, 800, 1000))

    def test_ten_percent_narrower_uses_full_page(self):
        self.assertTrue(should_draw_full_page_image(720, 1000, 800, 1000))

    def test_more_than_ten_percent_narrower_uses_contained_layout(self):
        self.assertFalse(should_draw_full_page_image(719, 1000, 800, 1000))

    def test_no_margin_exact_ratio_fills_page(self):
        # 800×1000 image on 800×1000 page, no margin → centered at (0, 0), fills page
        x, y, draw_w, draw_h = get_full_page_image_rect(800, 1000, 800, 1000, margin=0)
        self.assertAlmostEqual(x, 0)
        self.assertAlmostEqual(y, 0)
        self.assertAlmostEqual(draw_w, 800)
        self.assertAlmostEqual(draw_h, 1000)

    def test_no_margin_portrait_image_centered(self):
        # 900×1200 image on 800×1000 page, no margin
        # scale = min(800/900, 1000/1200) = min(0.888, 0.833) = 0.833
        # draw_w = 750, draw_h = 1000, x = 25, y = 0
        x, y, draw_w, draw_h = get_full_page_image_rect(900, 1200, 800, 1000, margin=0)
        self.assertAlmostEqual(x, 25)
        self.assertAlmostEqual(y, 0)
        self.assertAlmostEqual(draw_w, 750)
        self.assertAlmostEqual(draw_h, 1000)

    def test_margin_exact_ratio_centered_with_minimum_margin(self):
        # 800×1000 image on 800×1000 page, margin=10
        # avail = 780×980, scale = min(780/800, 980/1000) = min(0.975, 0.98) = 0.975
        # draw_w = 780, draw_h = 975, x = 10, y = 12.5
        x, y, draw_w, draw_h = get_full_page_image_rect(800, 1000, 800, 1000, margin=10)
        self.assertAlmostEqual(x, 10)
        self.assertAlmostEqual(y, 12.5)
        self.assertAlmostEqual(draw_w, 780)
        self.assertAlmostEqual(draw_h, 975)

    def test_margin_guarantees_minimum_gap_from_all_sides(self):
        # For any result, left/bottom gap must be >= margin, right/top gap >= margin
        margin = 15
        x, y, draw_w, draw_h = get_full_page_image_rect(900, 1200, 800, 1000, margin=margin)
        self.assertGreaterEqual(x, margin)
        self.assertGreaterEqual(y, margin)
        self.assertGreaterEqual(800 - (x + draw_w), margin - 1e-9)
        self.assertGreaterEqual(1000 - (y + draw_h), margin - 1e-9)


if __name__ == "__main__":
    unittest.main()
