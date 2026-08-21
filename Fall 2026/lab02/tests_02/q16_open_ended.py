test = {
  'name': 'q16_open_ended',
  'points': 1,
  'suites': [
    {
      'cases': [
        {
          'code': r"""
          >>> ### Testing answer to open ended question if answer is not there or too short, fails
          >>> test_open('Share your feedback', notebook, 60) == 1
          True
          """,
          'hidden': False,
          'locked': False
        },
          {
          'code': r"""
          >>> ### Checking lab version:
          >>> # If wrong version be sure to refresh content by using link from Canvas
          >>> ver == '2026V102'
          True
          """,
          'hidden': False,
          'locked': False
        }
          
      ],
      'scored': True,
      'setup': '',
      'teardown': print('Note: this test only checks that you answered.'),
      'type': 'doctest'
    }
  ]
}