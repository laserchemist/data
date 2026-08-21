test = {
  'name': 'q21 open ended',
  'points': 1,
  'suites': [
    {
      'cases': [
        {
          'code': r"""
          >>> ### Testing answer to open ended question if answer is not there or too short, fails
          >>> test_open('Write your reflection', notebook, 60) == 1
          True
          """,
          'hidden': False,
          'locked': False
        },
        {
          'code': r"""
          >>> ### Checking lab version:
          >>> # If wrong version be sure to refresh content by using link from Canvas
          >>> ver == '2026V103'
          True
          """,
          'hidden': False,
          'locked': False
        }
      ],
      'scored': True,
      'setup': '',
      'teardown': print('Note: this test only checks that you answered, not whether your answer is correct.'),
      'type': 'doctest'
    }
  ]
}