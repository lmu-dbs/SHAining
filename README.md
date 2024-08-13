# SHAining 

Codebase for the paper "SHAining a Light on Feature Impact for Automated Process Discovery Benchmarks" 

## Table of Contents

- [Overview](#overview)
- [ED Generation](#ed-generation)
- [Benchmarking](#benchmarking)
    - [Requirements](#requirements)
    - [Installation](#installation)
- [Feature Impact Calculation](#feature-impact-calculation)
- [References](#references)

## Overview
Process mining is a powerful technique for automatically monitoring and enhancing real-world processes by analyzing event data (ED). Automated process discovery (PD) is often the first step in this analysis. SHAining is a novel pipeline that aims to provide a comprehensive understanding of the impact of features on the performance of PD algorithms.

The SHAining pipeline consists of three main steps: ED generation, Benchmarking, and Feature impact calculation. In the ED generation step, logs are generated based on specific feature values. The benchmarking step evaluates the performance of PD algorithms on the generated logs, while the last step analyzes the impact of features on the algorithm's performance. The pipeline is designed to be modular, allowing for easy integration of new PD algorithms and feature sets. SHAining is implemented in Python and is available as an open-source repository.

## ED Generation
The event logs are generated with the help of [GEDI](https://github.com/lmu-dbs/gedi/tree/bpm24). The logs are generated based on the features specified in the configuration file. 
```markdown
config_files/
└── gen_triangle_config/
```

The resulting data used for the benchmarking is stored in the following directory:
```markdown
data/
├── gen_triangle.zip
```
Note: Please unzip the file before using it for benchmarking.
## Benchmarking
For benchmarking the following miners are supported:
- [Inductive Miner](https://pm4py.fit.fraunhofer.de/documentation)
- [Heuristics Miner](https://pm4py.fit.fraunhofer.de/documentation)
- [ILP Miner](https://pm4py.fit.fraunhofer.de/documentation)
- [Inductive Miner Infrequent](https://pm4py.fit.fraunhofer.de/documentation)
- [Split-Miner-2.0](https://link.springer.com/article/10.1007/s10115-018-1214-x)
    - [Source Code](https://figshare.com/articles/software/Split_Miner_2_0/12910139)
    - [Additional dependencies](https://mvnrepository.com/artifact/javax.xml.bind/jaxb-api/2.3.1)
- Split-Miner-1.0

Before running the benchmarking, make sure you have the necessary requirements.
### Requirements
- [Miniconda](https://docs.conda.io/en/latest/miniconda.html)

### Installation
To run the benchmarking, follow the steps below:

#### Note: For Unix-based servers: 
Install virtual framebuffer, a display server:
```
sudo apt-get install -y xvfb
Xvfb :99 -screen 0 1024x768x16 & export DISPLAY=:99
```

#### Startup
```bash
conda env create -f .conda.yml
conda activate shaining
```
This step will create a new conda environment with the necessary dependencies specified in ```.conda.yml```.
#### Usage
```console
python main.py -a config_files/benchmark.json
```
This command computes the benchmarking for all the above specified miners. To change the miners and other parameters, modify the the following file:
```markdown
config_files/
├── benchmark.json
```

## Feature Impact Calculation
The feature impact calculation is done by using Shapely values. The Shapely values are calculated for each feature and the impact is visualized using various intuitive plots. The feature impact calculation is done in the following directory:
```markdown
notebooks/
├── calculate_shapely.ipynb
```

## References
- [GEDI](https://github.com/lmu-dbs/gedi/tree/bpm24)
- [Shapley](https://papers.nips.cc/paper_files/paper/2017/file/8a20a8621978632d76c43dfd28b67767-Paper.pdf)
- [FEEED](https://github.com/lmu-dbs/feeed)