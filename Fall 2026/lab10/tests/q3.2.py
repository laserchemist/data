test = {
  'name': 'q3.2',
  'points': 1,
  'suites': [
    {
      'cases': [
        {'code': '>>> f = pka_features.item(0)\n>>> np.isclose(np.mean(train_su.column(f)), 0)\nTrue\n>>> np.allclose(validation_su.column(f), (validation.column(f) - np.mean(train.column(f))) / np.std(train.column(f)))\nTrue\n>>> np.allclose(test_su.column(pka_features.item(-1)), (test.column(pka_features.item(-1)) - np.mean(train.column(pka_features.item(-1)))) / np.std(train.column(pka_features.item(-1))))\nTrue', 'hidden': False, 'locked': False}
      ],
      'scored': True,
      'setup': '',
      'teardown': '',
      'type': 'doctest'
    }
  ]
}
