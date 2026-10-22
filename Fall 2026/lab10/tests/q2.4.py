test = {
  'name': 'q2.4',
  'points': 1,
  'suites': [
    {
      'cases': [
        {'code': ">>> x, y = train_roh.column('MW'), train_roh.column('bp')\n>>> m, b = np.polyfit(x, y, 1)\n>>> np.isclose(roh_slope, m) and np.isclose(roh_intercept, b)\nTrue\n>>> np.allclose(line_predictions, m * test_roh.column('MW') + b)\nTrue", 'hidden': False, 'locked': False}
      ],
      'scored': True,
      'setup': '',
      'teardown': '',
      'type': 'doctest'
    }
  ]
}
