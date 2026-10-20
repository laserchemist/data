test = {
  'name': 'q1.5',
  'points': 1,
  'suites': [
    {
      'cases': [
        {
          'code': r"""
          >>> ### hand-checkable: [1, 2, 3] has mean 2 and SD 0.8165
          >>> np.allclose(standard_units(make_array(1, 2, 3)), make_array(-1.22474487, 0, 1.22474487))
          True
          >>> np.isclose(z_150k, 1.4418, atol=0.001)
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
