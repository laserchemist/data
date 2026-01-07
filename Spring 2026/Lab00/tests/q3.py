test = {
  'name': 'Question 3',
  'points': 1,
  'suites': [
    {
      'cases': [
         {
          'code': r"""
          >>> # NOTE: You need to define your name above in question 1b
          >>> # This needs to be a string in quotes
          >>> # Example:
          >>> # name = 'Stella'
          >>> # Fix and rerun that cell and this cell...
          >>> type(name) == str
          True
          """,
          'hidden': False,
          'locked': False
        },
          {
          'code': r"""
          >>> # flour should be a number
          >>> # flour = 2.5
          >>> type(flour) == float
          True
          """,
          'hidden': False,
          'locked': False
        },
          {
          'code': r"""
          >>> # sugar should be a number
          >>> # Fix and rerun that cell and this cell...
          >>> # sugar = 1.75
          >>> type(sugar) == float
          True
          """,
          'hidden': False,
          'locked': False
        },
                    {
          'code': r"""
          >>> # sugar should be 1.75 given text
          >>> # sugar = 1.75
          >>> sugar == 1.75
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
