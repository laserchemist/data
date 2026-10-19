test = {
  'name': 'q4.1',
  'points': 1,
  'suites': [
    {
      'cases': [
        {
          'code': r"""
          >>> np.isclose(faithful_slope, 10.7296, atol=0.001)
          True
          >>> np.isclose(faithful_intercept, 33.4744, atol=0.001)
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
