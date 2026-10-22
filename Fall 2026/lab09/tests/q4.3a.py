test = {
  'name': 'q4.3a',
  'points': 1,
  'suites': [
    {
      'cases': [
        {
          'code': r"""
          >>> # novas_slope and novas_intercept are items 0 and 1 of fit_line on close_novas
          >>> abs(novas_slope - 14094.53) < 0.1
          True
          >>> abs(novas_intercept - 2.409) < 0.01
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
