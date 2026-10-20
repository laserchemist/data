test = {
  'name': 'q1.1',
  'points': 1,
  'suites': [
    {
      'cases': [
        {
          'code': r"""
          >>> import io, contextlib
          >>> with contextlib.redirect_stdout(io.StringIO()):
          ...     test_means = simulate_sample_mean(Table.read_table('sf_salaries_2014.csv').select('salary'), 'salary', 100, 100)
          >>> len(test_means) == 100
          True
          >>> ### the average of the sample means should be near the population mean ($75,464)
          >>> 73000 < np.mean(test_means) < 78000
          True
          >>> ### samples of 100 should give an SD of sample means near 51,697/10 = 5,170
          >>> 3500 < np.std(test_means) < 7000
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
