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
          >>> # correlation of the supernova data
          >>> abs(correlation(close_novas, 'Speed (parsecs/year)', 'Distance (million parsecs)') - 0.98211) < 0.0001
          True
          >>> # fit_line on the supernova data
          >>> abs(fit_line(close_novas, 'Speed (parsecs/year)', 'Distance (million parsecs)').item(0) - 14094.53) < 0.1
          True
          >>> abs(fit_line(close_novas, 'Speed (parsecs/year)', 'Distance (million parsecs)').item(1) - 2.409) < 0.01
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
