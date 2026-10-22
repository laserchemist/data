test = {
  'name': 'q2.3',
  'points': 1,
  'suites': [
    {
      'cases': [
        {'code': ">>> preds = predict_all(train_roh, test_roh, 3, roh_features, roh_target)\n>>> np.isclose(knn_rmse, np.sqrt(np.mean((test_roh.column('bp') - preds) ** 2)))\nTrue", 'hidden': False, 'locked': False}
      ],
      'scored': True,
      'setup': '',
      'teardown': '',
      'type': 'doctest'
    }
  ]
}
