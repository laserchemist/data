test = {
  'name': 'q4.3',
  'points': 1,
  'suites': [
    {
      'cases': [
        {
          'code': r"""
          >>> abs(novas_r_squared - 0.9645) < 0.001
          True
          >>> len(best_errors) == 156 and abs(np.mean(best_errors)) < 1e-6
          True
          >>> abs(best_mse - 109.87) < 0.01
          True
          >>> # slope is in millions of years; age in BILLIONS
          >>> abs(age_estimate_billion_years - 14.0945) < 0.001
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
