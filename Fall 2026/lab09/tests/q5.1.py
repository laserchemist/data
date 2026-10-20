test = {
  'name': 'q5.1',
  'points': 1,
  'suites': [
    {
      'cases': [
        {
          'code': r"""
          >>> len(bootstrap_ages) == 1000
          True
          >>> # ages in billions of years, centered near 14.1
          >>> 13.9 < np.mean(bootstrap_ages) < 14.3
          True
          >>> # each age should come from a full-size resample with replacement
          >>> 0.15 < np.std(bootstrap_ages) < 0.32
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
