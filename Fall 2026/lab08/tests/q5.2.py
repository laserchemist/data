test = {
  'name': 'q5.2',
  'points': 1,
  'suites': [
    {
      'cases': [
        {
          'code': r"""
          >>> np.isclose(roh_r, 0.8674, atol=0.0005)
          True
          >>> np.isclose(roh_slope, 1.4633, atol=0.001)
          True
          >>> np.isclose(roh_intercept, 272.70, atol=0.05)
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
