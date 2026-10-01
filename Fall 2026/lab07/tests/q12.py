test = {
  'name': 'Question 12',
  'points': 1,
  'suites': [
    {
      'cases': [
        {
          'code': r"""
          >>> changes_by_country.num_rows == 233
          True
          """,
          'hidden': False,
          'locked': False
        }, 
          {
          'code': r"""
          >>> changes_by_country.labels
          ('country', 'avg changes')
          >>> changes_by_country.column('avg changes').take(np.arange(4)).tolist()
          [18, -22, 9, -3]
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
