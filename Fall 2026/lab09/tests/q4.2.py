test = {
  'name': 'q4.2',
  'points': 1,
  'suites': [
    {
      'cases': [
        {
          'code': r"""
          >>> # MSE is the MEAN of the squared residuals of your line
          >>> abs(my_mse - np.mean(errors(close_novas, 'Speed (parsecs/year)', 'Distance (million parsecs)', my_slope, my_intercept)**2)) < 0.001
          True
          >>> # your slider line should beat the trial line (MSE 402)
          >>> my_mse < 401.98
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
