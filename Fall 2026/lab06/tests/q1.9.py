test = {
  'name': 'q1.9',
  'points': 1,
  'suites': [
    {
      'cases': [
        {
          'code': r"""
          >>> darwin_sample_50.num_rows == 50
          True
          >>> set(darwin_sample_50.labels) == set(darwin_population.labels)
          True
          >>> darwin_population.column('word_length').min() <= darwin_sample_mean <= darwin_population.column('word_length').max()
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
