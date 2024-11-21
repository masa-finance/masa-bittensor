---
title: Masa Bittensor Release Notes
---

<!-- Release notes generated using configuration in .github/release.yml at main -->

This release of the subnet focuses on increased miner competition and fairness. Validators now fetch trending queries, ensuring there is ample volume for miners to scrape. Additionally, validators exhaust the list of miners before repeating, reducing the randomness in scoring. To increase miner competition, there is no longer a validator-defined maximum number of tweets per request - this maximum is now set by the miners themselves, through the --twitter.max_tweets_per_request argument.

### New Features
* feat: trending queries by @grantdfoster in https://github.com/masa-finance/masa-bittensor/pull/301
* feat: adding E2E test and coverage by @hide-on-bush-x in https://github.com/masa-finance/masa-bittensor/pull/288

### Bug Fixes
* fix: more fair queries by @grantdfoster in https://github.com/masa-finance/masa-bittensor/pull/286
* fix: spike to spike.yml by @Luka-Loncar in https://github.com/masa-finance/masa-bittensor/pull/285
* fix: update to python v3.12 in classifiers list by @5u6r054 in https://github.com/masa-finance/masa-bittensor/pull/293
* fix: update makefile to support axon_off for validator by @grantdfoster in https://github.com/masa-finance/masa-bittensor/pull/290
* fix: fix tests by adding registered miner and validator wallets as secrets, among other things by @5u6r054 in https://github.com/masa-finance/masa-bittensor/pull/306

### CI / CD
* ci: stop broken docker_publish.yml workflow from running on main branch until its fixed by @5u6r054 in https://github.com/masa-finance/masa-bittensor/pull/292
* chore: add spike template by @Luka-Loncar in https://github.com/masa-finance/masa-bittensor/pull/284

## New Contributors
* @Luka-Loncar made their first contribution in https://github.com/masa-finance/masa-bittensor/pull/284

**Full Changelog**: https://github.com/masa-finance/masa-bittensor/compare/v1.0.2...v1.1.0

[All Releases](https://github.com/masa-finance/masa-bittensor/releases)
