test = {
  'name': '1b',
  'points': 1,
  'suites': [
    {
      'cases': [
        {
          'code': r"""
          >>> # It looks like you have not defined the variable: average_distance
          >>> # Example:
          >>> # average_distance = sum_distance/5
          >>> 'average_distance' in vars()
          True
          """,
          'hidden': False,
          'locked': False
        },
        {
          'code': r"""
          >>> # Make sure average_distance is a number
          >>> # Example:
          >>> # sum_distance = .2 + 5.5 + .1 + 1.4 + 10.4
          >>> # average_distance = sum_distance/5
          >>> type(average_distance) in [float, int]
          True
          """,
          'hidden': False,
          'locked': False
        },
        {
          'code': r"""
          >>> # Make sure average_distance is actually the average of whatever
          >>> # distance variables you defined (d1, d2, ... -- your group can
          >>> # have any number of people, not just 5).
          >>> import re
          >>> distance_vars = [v for k, v in vars().items() if re.fullmatch(r'd\d+', k)]
          >>> len(distance_vars) >= 1
          True
          >>> np.abs(average_distance - sum(distance_vars) / len(distance_vars)) < 1e-9
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
