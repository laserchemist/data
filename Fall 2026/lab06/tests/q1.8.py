test = {
  'name': 'q1.8',
  'points': 1,
  'suites': [
    {
      'cases': [
        {
          'code': r"""
          >>> sample_30.num_rows == 30
          True
          >>> set(sample_30.labels) == set(population_rolls.labels)
          True
          >>> population_rolls.column('modified_roll').min() <= sample_30_mean <= population_rolls.column('modified_roll').max()
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
