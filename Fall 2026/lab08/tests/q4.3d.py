test = {
  'name': 'q4.3d',
  'points': 1,
  'suites': [
    {
      'cases': [
        {
          'code': r"""
          >>> ### Open-ended: fails if the answer cell is missing or under 60 characters
          >>> test_open('When would you tell the tourist to come back', notebook, 60) == 1
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
