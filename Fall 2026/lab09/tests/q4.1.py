test = {
  'name': 'q4.1',
  'points': 1,
  'suites': [
    {
      'cases': [
        {
          'code': r"""
          >>> len(example_errors) == 156
          True
          >>> # error = actual - predicted (check the sign)
          >>> abs(example_errors.item(0) - (-22.43)) < 0.01
          True
          >>> abs(np.mean(example_errors) - (-15.41)) < 0.01
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
