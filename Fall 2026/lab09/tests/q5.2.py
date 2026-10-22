test = {
  'name': 'q5.2',
  'points': 1,
  'suites': [
    {
      'cases': [
        {
          'code': r"""
          >>> lower_end == percentile(2.5, bootstrap_ages)
          True
          >>> upper_end == percentile(97.5, bootstrap_ages)
          True
          >>> 13.3 < lower_end < 13.9 and 14.2 < upper_end < 14.8
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
