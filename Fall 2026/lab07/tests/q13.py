# True value is 1121 (five tied two-year comparisons). Four of the ties differ only by
# floating-point noise (~1e-15) in temp_per_country.csv, so environments report 1118-1121.
# The range covers +/-1 for each of the five ties; plausible mistakes land far outside
# (adjacent years 1053, no cleaning 1141, mean 4.8). Ties-as-decreases is caught by q11.
test = {
  'name': 'Question 13',
  'points': 1,
  'suites': [
    {
      'cases': [
        {
          'code': r"""
          >>> 1116 <= test_stat <= 1126
          True
          """,
          'hidden': False,
          'locked': False
        }
      ],
      'scored': True,
      'setup': '',
      'teardown': '',
      'type': 'doctest'
    }
  ]
}
