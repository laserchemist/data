test = {
  'name': 'q4.3b',
  'points': 1,
  'suites': [
    {
      'cases': [
        {
          'code': r"""
          >>> abs(novas_r_squared - 0.9645) < 0.001
          True
          >>> # residuals of the regression line: one per supernova, averaging 0
          >>> len(best_errors) == 156 and abs(np.mean(best_errors)) < 1e-6
          True
          >>> # MSE is the MEAN of the squared residuals
          >>> abs(best_mse - 109.87) < 0.01
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
