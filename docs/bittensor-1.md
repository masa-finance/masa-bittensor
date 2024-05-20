# Bittensor MVP Subnet Documentation

## Overview
This MVP (Minimum Viable Product) subnet for Bittensor demonstrates a simple yet effective implementation of a decentralized network where validators query miners for data using GET requests. The subnet leverages Bittensor's framework to facilitate communication and data exchange between nodes, focusing on simplicity and efficiency.

### Components
- **Validator (`validator.py`)**: Acts as the orchestrator, querying miners for data and evaluating their responses.
- **Miner (`miner.py`)**: Responds to validators' queries with data fetched from external sources.
- **Protocol (`protocol.py`)**: Defines the [SimpleGETProtocol](/bittensor-1/alchemy/validator/forward.py), a custom protocol for handling GET requests and responses.
- **Forward Logic ([forward.py](/bittensor-1/alchemy/validator/forward.py))**: Contains the logic for validators to forward requests to miners and process their responses.
- **Reward System ([reward.py](/bittensor-1/alchemy/validator/reward.py))**: Implements a simple reward mechanism based on the validity of miners' responses.

## Query Shape
The shape of the query is defined by the [.env.example](/bittensor-1/.env.example) file, which specifies the request URL to be used by the validator when querying miners. This URL points to the data source that miners will fetch and return in response to the validator's queries.

```plaintext
REQUEST_URL=http://localhost:8080/api/v1/data/twitter/profile/brendanplayford
```

### Description
- **REQUEST_URL**: Specifies the endpoint that miners will query to fetch data. This URL is used by the [SimpleGETProtocol](/bittensor-1/alchemy/validator/forward.py) in the [forward](/bittensor-1/alchemy/validator/forward.py) function of the validator to define the data retrieval task for miners.

## How It Works
1. **Initialization**: The validator and miners initialize their Bittensor dendrite and metagraph instances, setting up the network topology and communication pathways.
2. **Data Querying**: The validator uses the [forward](/bittensor-1/alchemy/validator/forward.py) function to send a GET request to the miners, specifying the data it seeks through the `REQUEST_URL`.
3. **Data Retrieval**: Miners receive the request, fetch the specified data using the `perform_get_request` method, and return the data to the validator.
4. **Response Evaluation**: The validator receives responses from miners and uses the [get_rewards](/bittensor-1/alchemy/validator/forward.py) function to evaluate the data's validity, assigning rewards based on the accuracy and completeness of the data.
5. **Score Updating**: Based on the rewards, the validator updates the scores of each miner, reflecting their performance and reliability in the network.

## Key Features
- **Decentralized Data Retrieval**: Demonstrates a decentralized approach to data retrieval, where validators can request data from multiple sources (miners) without relying on a central server.
- **Custom Protocol Implementation**: Showcases the ability to define and use custom protocols ([SimpleGETProtocol](/bittensor-1/alchemy/validator/forward.py)) within the Bittensor framework, tailored to specific data retrieval tasks.
- **Reward Mechanism**: Implements a basic reward mechanism, incentivizing miners to provide accurate and complete data in response to validators' queries.

## Conclusion
This MVP subnet provides a foundational example of how Bittensor can be used to create decentralized networks for data retrieval and processing. It highlights the framework's flexibility in defining custom protocols and reward mechanisms, paving the way for more complex and feature-rich implementations.