# Test inventory — 2026-10-12

346 unique final cases: 251 non-slow and 95 slow. Parameterized cases count separately. Every ID and its evidence are in test-results.json.

| File | Cases | Slow |
|---|---:|---:|
| `tests/lottery/test_ablation.py` | 1 | 0 |
| `tests/lottery/test_any_prize_coverage_engine.py` | 10 | 4 |
| `tests/lottery/test_backtest_report.py` | 1 | 0 |
| `tests/lottery/test_backtesting.py` | 13 | 0 |
| `tests/lottery/test_baseline.py` | 6 | 0 |
| `tests/lottery/test_coverage_engine.py` | 2 | 1 |
| `tests/lottery/test_dataset.py` | 16 | 0 |
| `tests/lottery/test_elite_config_validation.py` | 2 | 0 |
| `tests/lottery/test_elite_portfolio_coverage.py` | 2 | 2 |
| `tests/lottery/test_elite_pro.py` | 43 | 19 |
| `tests/lottery/test_elite_vs_pro_random.py` | 44 | 44 |
| `tests/lottery/test_evaluation.py` | 10 | 0 |
| `tests/lottery/test_generator.py` | 10 | 0 |
| `tests/lottery/test_integration.py` | 2 | 0 |
| `tests/lottery/test_multi_seed_evaluation.py` | 1 | 0 |
| `tests/lottery/test_optimizer.py` | 14 | 0 |
| `tests/lottery/test_p0_validation.py` | 21 | 0 |
| `tests/lottery/test_portfolio_coverage.py` | 8 | 0 |
| `tests/lottery/test_predictor.py` | 9 | 0 |
| `tests/lottery/test_prize_evaluation.py` | 19 | 0 |
| `tests/lottery/test_pro.py` | 4 | 0 |
| `tests/lottery/test_pro_backtest.py` | 1 | 0 |
| `tests/lottery/test_pro_portfolio_refinement.py` | 2 | 0 |
| `tests/lottery/test_pro_quality.py` | 10 | 6 |
| `tests/lottery/test_pro_random_baseline.py` | 1 | 1 |
| `tests/lottery/test_pro_random_baseline_robust.py` | 1 | 1 |
| `tests/lottery/test_pro_scoring_ablation.py` | 1 | 0 |
| `tests/lottery/test_pro_scoring_variants.py` | 1 | 0 |
| `tests/lottery/test_real_backtest.py` | 3 | 0 |
| `tests/lottery/test_real_dataset.py` | 3 | 0 |
| `tests/lottery/test_recommendation.py` | 6 | 0 |
| `tests/lottery/test_regular_vs_pro.py` | 1 | 1 |
| `tests/lottery/test_report_builder.py` | 2 | 0 |
| `tests/lottery/test_robustness.py` | 1 | 0 |
| `tests/lottery/test_selection.py` | 7 | 0 |
| `tests/lottery/test_smart.py` | 28 | 16 |
| `tests/lottery/test_strong_number_backtest.py` | 5 | 0 |
| `tests/lottery/test_strong_number_backtest_metrics.py` | 3 | 0 |
| `tests/lottery/test_strong_number_evaluation.py` | 6 | 0 |
| `tests/lottery/test_strong_number_pipeline.py` | 4 | 0 |
| `tests/lottery/test_strong_number_report.py` | 1 | 0 |
| `tests/lottery/test_ticket_count_details.py` | 1 | 0 |
| `tests/lottery/test_ticket_count_evaluation.py` | 1 | 0 |
| `tests/test_cli.py` | 2 | 0 |
| `tests/test_cli_recommend.py` | 10 | 0 |
| `tests/test_config.py` | 2 | 0 |
| `tests/test_database.py` | 2 | 0 |
| `tests/test_logging.py` | 2 | 0 |
| `tests/test_package.py` | 1 | 0 |
| `tests/lottery/test_statistics.py` | 0 | 0 |

The empty statistics file adds no coverage; related behavior is exercised elsewhere.
