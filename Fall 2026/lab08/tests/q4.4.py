test = {
  'name': 'q4.4',
  'points': 1,
  'suites': [
    {
      'cases': [
        {
          'code': r"""
          >>> ### hand-checkable: y = 2x exactly
          >>> up = Table().with_columns('x', make_array(1, 2, 3), 'y', make_array(2, 4, 6))
          >>> np.isclose(correlation(up, 'x', 'y'), 1) and np.isclose(slope(up, 'x', 'y'), 2) and np.isclose(intercept(up, 'x', 'y'), 0)
          True
          >>> ### hand-checkable: y = 8 - 2x exactly
          >>> down = Table().with_columns('x', make_array(1, 2, 3), 'y', make_array(6, 4, 2))
          >>> np.isclose(correlation(down, 'x', 'y'), -1) and np.isclose(slope(down, 'x', 'y'), -2) and np.isclose(intercept(down, 'x', 'y'), 8)
          True
          >>> np.isclose(slope(faithful, 'duration', 'wait'), 10.7296, atol=0.001)
          True
          >>> np.isclose(intercept(faithful, 'duration', 'wait'), 33.4744, atol=0.001)
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
