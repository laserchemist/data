test = {
  'name': 'q5.1d',
  'points': 1,
  'suites': [
    {
      'cases': [
        {
          'code': r"""
          >>> ### Open-ended: fails if the answer cell is missing or under 60 characters
          >>> test_open('Describe the direction, form, and strength of the relationship. Notice the vertical stacks', notebook, 60) == 1
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
