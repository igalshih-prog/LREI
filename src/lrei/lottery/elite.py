            origin = len(dataset) - origin_index * validation_size
            if origin - validation_size < minimum_train:
                break
            train = LotteryDataset(dataset.draws[:origin - validation_size])
            validation = dataset.draws[origin - validation_size:origin]
            if not train.draws or not validation:
                continue

            frequencies = self._frequency(train)
            recent_3 = self._window_frequency(train, 3)
            recent_1 = self._window_frequency(train, 1)
            recent_draws = self._recent_draw_frequency(train, 60)
            ewma = self._ewma_frequency(train, self.config.ewma_half_life)
            pair_counts = self._combination_counts(train, 2)
            triple_counts = self._combination_counts(train, 3)
            structure = self._structure_profile(train)
            source_scores = (
                engines[0][0]._individual_scores(frequencies, recent_3, recent_1, recent_draws, {}),
                engines[1][0]._individual_scores(frequencies, recent_3, recent_1, recent_draws, {}),
                engines[2][0]._individual_scores(frequencies, recent_3, recent_1, recent_draws, ewma),
            )
            baseline = 6.0 * 6.0 / 37.0
            for source_index, scores in enumerate(source_scores):
                rng = random.Random(13579 + len(dataset) * 11 + origin_index * 101 + source_index * 1009)
                candidates = [
                    self._generate_candidate(
                        scores, pair_counts, triple_counts, structure, rng
                    )
                    for _ in range(self.config.candidate_calibration_candidate_count)
                ]
                portfolio = self._select_portfolio(
                    candidates, scores, frequencies, pair_counts, triple_counts, structure
                )
                if not portfolio:
                    source_performance[source_index].append(0.05)
                    continue
                mean_hits = mean(
                    mean(len(set(ticket) & set(draw.numbers)) for ticket in portfolio)
                    for draw in validation
                )
                source_performance[source_index].append(max(0.05, mean_hits / baseline))

        if not all(source_performance):
            return default
        performance = [mean(values) for values in source_performance]
        default_total = sum(default)
        prior = [x / default_total for x in default]
        performance_total = sum(performance)
        if performance_total <= 0:
            return default
        learned = [x / performance_total for x in performance]