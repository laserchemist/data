test = {
  'name': 'q7d',
  'points': 1,
  'suites': [
    {
      'cases': [
        {
          'code': r"""
          >>> ### Open-ended: fails if the answer cell is missing or under 60 characters
          >>> test_open('At the end of each lab, please include a reflection', notebook, 60) == 1
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
