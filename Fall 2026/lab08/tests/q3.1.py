test = {
  'name': 'q3.1',
  'points': 1,
  'suites': [
    {
      'cases': [
        {
          'code': r"""
          >>> faithful_standard.labels == ('duration (standard units)', 'wait (standard units)')
          True
          >>> faithful_standard.num_rows == 272
          True
          >>> np.isclose(np.mean(faithful_standard.column(0)), 0) and np.isclose(np.std(faithful_standard.column(0)), 1)
          True
          >>> np.isclose(np.mean(faithful_standard.column(1)), 0) and np.isclose(np.std(faithful_standard.column(1)), 1)
          True
          >>> np.isclose(faithful_standard.column(0).item(0), 0.0985, atol=0.0001)
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
