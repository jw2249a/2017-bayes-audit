# 2017-bayes-audit

This branch, which diverged from several other branches back in 2017-02-07, contains
Experiment 24, "tracing path of subjective probabilities (uniform prior), dirichlet."
It also has a variety of forms of instrumentation added to bayes.py to save csv files that can be
used to plot more detailed results, study variance in workload etc.

The stratify branch has a much cleaner instrumentation approach, with bayes.setup_csv_logger().

Note: still very messy, but helpful for reference and cherrypicking.
