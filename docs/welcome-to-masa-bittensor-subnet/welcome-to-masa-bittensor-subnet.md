---
title: Welcome to Masa Bittensor Subnet
---

## Welcome to Masa Bittensor Subnet

The Masa Bittensor Subnet is a specialized subnet that scores miners based on their ability to return Twitter data for requested handles through the Validator API.

## Features

### Validator API Endpoints

1. **Followers Endpoint**

   - `GET /data/twitter/followers/{handle}`

2. **Profiles Endpoint**

   - `GET /data/twitter/profile/{handle}`

3. **Recent Tweets Endpoint**
   - `POST /data/twitter/tweets/recent`
   - **Body:** `{ "query": "keyword", "count": 10 }`
