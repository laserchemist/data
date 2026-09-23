test = {
  'name': 'q1.4',
  'points': 1,
  'suites': [
    {
      'cases': [
        {
          'code': r"""
          >>> # modifier is fixed at 11 here (not randomized until Q1.5), so the
          >>> # expected bins are hardcoded rather than recomputed from the live
          >>> # modifier variable, which Q1.5 later reassigns to a random value.
          >>> list(roll_bins) == list(np.arange(1, 33, 1))
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
