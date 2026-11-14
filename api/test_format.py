import unittest

from api.format import fee_label, money, public_html, rating_value, shown_date


class FormatTests(unittest.TestCase):
    def test_indian_grouping(self):
        self.assertEqual(money(999), "999")
        self.assertEqual(money(1000), "1,000")
        self.assertEqual(money(110000), "1,10,000")
        self.assertEqual(money(10000000), "1,00,00,000")

    def test_fee_label_hides_empty_amounts(self):
        self.assertIsNone(fee_label(None, "Year"))
        self.assertIsNone(fee_label(0, "Semester"))
        self.assertEqual(fee_label(110000, "Semester"), "₹1,10,000 per semester")
        self.assertEqual(
            fee_label(110000, "Semester", prefix_from=True),
            "From ₹1,10,000 per semester",
        )
        self.assertEqual(fee_label(50000, "per year"), "₹50,000 per year")

    def test_rating_hides_zero(self):
        self.assertIsNone(rating_value(0))
        self.assertIsNone(rating_value(None))
        self.assertEqual(rating_value(4.26), 4.3)

    def test_public_html_strips_brand_and_empty_markup(self):
        self.assertIsNone(public_html("  "))
        self.assertIsNone(public_html("<p> <br> </p>"))
        cleaned = public_html(
            '<p onclick="alert(1)">Visit DekhoCampus</p><script>bad()</script>'
            '<a href="https://dekhocampus.com/colleges">link</a>'
        )
        self.assertNotIn("DekhoCampus", cleaned)
        self.assertNotIn("dekhocampus.com", cleaned)
        self.assertNotIn("script", cleaned.lower())
        self.assertNotIn("onclick", cleaned)
        self.assertIn("Admission Setu", cleaned)

    def test_blank_exam_dates_stay_blank(self):
        self.assertIsNone(shown_date("Not announced"))
        self.assertEqual(shown_date("15 April 2026"), "15 April 2026")


if __name__ == "__main__":
    unittest.main()
