test = {
  'name': 'Question 14',
  'points': 1,
  'suites': [
    {
      'cases': [
        {
          'code': r"""
          >>> -40 < simulate_under_null(100) < 40
          True
          """,
          'hidden': False,
          'locked': False
        }, 
        {
          'code': r"""
          >>> max(samples) < 1200
          True
          >>> min(samples) > -1200
          True
          >>> 180 < np.std(samples) < 230
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
