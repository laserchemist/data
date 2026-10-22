test = {
  'name': 'q4.3c',
  'points': 1,
  'suites': [
    {
      'cases': [
        {
          'code': r"""
          >>> # slope is in millions of years; age in BILLIONS
          >>> abs(age_estimate_billion_years - 14.0945) < 0.001
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
