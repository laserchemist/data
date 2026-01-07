test = {
  'name': 'Question 4.',
  'points': 1,
  'suites': [
    {
      'cases': [
          {
          'code': r"""
          >>> ### Checking lab version:
          >>> # If wrong version be sure to refresh content by using link from Canvas
          >>> ver == '2026V100'
          True
          """,
          'hidden': False,
          'locked': False
        },
        {
          'code': r"""
          >>> ### Testing answer to open ended question if answer is not there or too short, fails.
          >>> ### NOTE: Put in your response to the feedback questions in question 4.
          >>> test_open('Question 4.', notebook, 40) == 1
          True
          """,
          'hidden': False,
          'locked': False
        }
          
        
      ],
      'scored': True,
      'setup': '',
      'teardown': print('Note: this test only checks that you answered, not what you wrote in your feedback.'),
      'type': 'doctest'
    }
  ]
}

