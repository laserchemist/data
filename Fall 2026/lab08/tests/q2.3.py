test = {
  'name': 'q2.3',
  'points': 1,
  'suites': [
    {
      'cases': [
        {
          'code': r"""
          >>> 0 <= my_slope <= 20 and 0 <= my_intercept <= 80
          True
          >>> ### allow for an SSE copied from the slider title, which is rounded to a whole number
          >>> np.isclose(my_sse, np.sum(line_errors(faithful.column('duration'), faithful.column('wait'), my_slope, my_intercept)**2), atol=1)
          True
          >>> ### no straight line can beat the least-squares SSE of 9,443
          >>> my_sse >= 9443
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
