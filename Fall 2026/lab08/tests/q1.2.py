test = {
  'name': 'q1.2',
  'points': 1,
  'suites': [
    {
      'cases': [
        {
          'code': r"""
          >>> len(means_400) == 10000 and len(means_625) == 10000
          True
          >>> 2300 < np.std(means_400) < 2900
          True
          >>> 1850 < np.std(means_625) < 2300
          True
          >>> np.allclose(predicted_sd, pop_sd / np.sqrt(make_array(100, 400, 625)))
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
