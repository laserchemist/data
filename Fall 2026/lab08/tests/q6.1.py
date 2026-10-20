test = {
  'name': 'q6.1',
  'points': 1,
  'suites': [
    {
      'cases': [
        {
          'code': r"""
          >>> np.isclose(pf_slope, 10.7296, atol=0.001) and np.isclose(pf_intercept, 33.4744, atol=0.001)
          True
          >>> bool(matches)
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
