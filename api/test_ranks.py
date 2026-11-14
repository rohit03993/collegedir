import unittest

from api.ranks import engineering_rank, listing_category


class RankTests(unittest.TestCase):
    def test_iit_order(self):
        mumbai = engineering_rank("indian-institute-of-technology-iit-mumbai", "Indian Institute of Technology - [IIT], Mumbai")
        delhi = engineering_rank("indian-institute-of-technology-iit-new-delhi", "Indian Institute of Technology - [IIT], New Delhi")
        kharagpur = engineering_rank("iit-kharagpur", "IIT Kharagpur")
        self.assertLess(mumbai, delhi)
        self.assertLess(delhi, kharagpur)

    def test_department_is_not_ranked(self):
        rank = engineering_rank(
            "department-of-management-studies-indian-institute-of-technology-dmsiit-roorkee",
            "Department of Management Studies, Indian Institute of Technology - [DMSIIT], Roorkee",
        )
        self.assertIsNone(rank)

    def test_bombay_is_listed_as_engineering(self):
        self.assertEqual(
            listing_category("indian-institute-of-technology-iit-mumbai", "Indian Institute of Technology - [IIT], Mumbai", "Management"),
            "Engineering",
        )


if __name__ == "__main__":
    unittest.main()
