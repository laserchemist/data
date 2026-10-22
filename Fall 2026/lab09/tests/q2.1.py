test = {
  'name': 'q2.1',
  'points': 1,
  'suites': [
    {
      'cases': [
        {
          'code': r"""
          >>> # standard_units of [1, 2, 3]
          >>> np.allclose(standard_units(make_array(1, 2, 3)), make_array(-1.22474487, 0, 1.22474487))
          True
          >>> # the line through (0, 1) and (1, 3): slope 2, intercept 1
          >>> np.allclose(fit_line(example_table, 'x', 'y'), make_array(2, 1))
          True
          >>> # correlation of the drivers data
          >>> abs(correlation(drivers, 'Speed moving away from us (miles per hour)', 'Current distance from us (miles)') - 0.985429) < 0.00001
          True
          >>> # fit_line on the drivers data: slope (hours) and intercept (miles)
          >>> abs(fit_line(drivers, 'Speed moving away from us (miles per hour)', 'Current distance from us (miles)').item(0) - 1.68377) < 0.0001
          True
          >>> abs(fit_line(drivers, 'Speed moving away from us (miles per hour)', 'Current distance from us (miles)').item(1) - (-1.12137)) < 0.0001
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
