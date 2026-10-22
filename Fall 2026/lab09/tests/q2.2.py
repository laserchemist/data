test = {
  'name': 'q2.2',
  'points': 1,
  'suites': [
    {
      'cases': [
        {
          'code': r"""
          >>> # driver_slope is item 0 of driver_line
          >>> abs(driver_slope - 1.68377) < 0.0001
          True
          >>> # driver_intercept is item 1 of driver_line
          >>> abs(driver_intercept - (-1.12137)) < 0.0001
          True
          >>> abs(driving_start_time_hours - 1.68377) < 0.0001
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
