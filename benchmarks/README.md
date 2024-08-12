# DipDup benchmarks

This directory contains scripts and configs to run various DipDup benchmarks. They don't mean to compare with the competition, but rather for us to track progress in optimizing the framework for different workloads.

When performed correctly these benchmarks show excellent consistency, with a multiple-second skew between 10+ minute runs.

## TODO

- [ ] A shorter version for CI
- [ ] Extract metrics from reports

## Configuration

All runs were performed on the @droserasprout laptop.

- **Host:** ASUS Zephyrus G14 GA401IV laptop
- **OS:** Arch Linux, kernel 6.9.4-1-ck
- **CPU:** Ryzen 7 4800HS
- **RAM:** 32 GB, DDR4-3200 running on 3600 MHz
- **SSD:** Intel SSD 660p 1TB SSDPEKNW010T8

(we need just 1/16 of these RAM amount and CPU cores)

To get consistent results enable frequency boost and change governor to `performance`:

```shell
echo 1 | sudo tee /sys/devices/system/cpu/cpufreq/boost
sudo cpupower frequency-info -g performance
```

## Running tests

```shell
make run_in_memory run_in_postgres down shortstat DEMO=demo_evm_events
```

See the Makefile for details.

## Results

### evm.events

- project: `demo_evm_events`
- interval: 10,000,000 to 10,100,000 (100,000 levels, 93,745 non-empty)
- database: in-memory sqlite

| run              | time                                                 | bps       | vs. asyncio | vs. 7.5 |
| ---------------- | ---------------------------------------------------- | --------- | ----------- | ------- |
| 7.5.9, asyncio   | 1044,56s user 258,07s system 102% cpu 21:06,02 total | 79        |             |         |
| 7.5.10, uvloop   | 924,94s user 182,33s system 102% cpu 18:04,67 total  | 92        | 1.15        |         |
| 8.0.0b4, asyncio | 832,32s user 163,20s system 101% cpu 16:19,93 total  | 102       |             | 1.29    |
| 8.0.0b5, uvloop  | 721,13s user 84,17s system 98% cpu 13:33,88 total    | 123 (116) | 1.18        | 1.31    |

#### Without CPU boost

The same tests run without frequency boost, which increases frequency from 2.9 GHz base up to 4.2 GHz. Gives some understanding of the impact of CPU performance.

Run `echo 0 | sudo tee /sys/devices/system/cpu/cpufreq/boost`.

| run                       | time                                                 | bps | vs. boost |
| ------------------------- | ---------------------------------------------------- | --- | --------- |
| 7.5.10, uvloop, no boost  | 1329,36s user 231,93s system 101% cpu 25:31,69 total | 65  | 0.82      |
| 8.0.0b5, uvloop, no boost | 1048,85s user 115,34s system 99% cpu 19:35,61 total  | 85  | 0.70      |

In the subsequent runs, we will skip the 7.5 branch; speedup vs 8.0 is pretty stable.

#### With PostgreSQL

| run             | time                                                | bps     | vs. in-memory |
| --------------- | --------------------------------------------------- | ------- | ------------- |
| 8.0.0b5, uvloop | 1083,66s user 214,23s system 57% cpu 37:33,04 total | 46 (42) | 0.36          |

### starknet.events

- project: `demo_starknet_events`
- interval: 500,000 to 600,000 (100,000)
- database: in-memory sqlite

| run              | time                                              | bps | speedup |
| ---------------- | ------------------------------------------------- | --- | ------- |
| 8.0.0b4, asyncio | 246,94s user 61,67s system 100% cpu 5:07,54 total | 326 | 1       |
| 8.0.0b5, uvloop  | 213,01s user 33,22s system 96% cpu 4:14,32 total  | 394 | 1.20    |

#### With PostgreSQL

| run             | time                                        | bps | vs. in-memory |
| --------------- | ------------------------------------------- | --- | ------------- |
| 8.0.0b5, uvloop | real 12m6,394s user 5m24,683s sys 1m14,761s | 138 | 0.35          |

### tezos.big_maps

- project: `demo_tezos_domains`
- interval:  1417362 + 500k
- database: in-memory sqlite

Only our code. And only 7% of blocks are non-empty.

| run              | time                                             | bps        | speedup |
| ---------------- | ------------------------------------------------ | ---------- | ------- |
| 8.0.0b4, asyncio | 136,63s user 17,91s system 98% cpu 2:37,40 total | 3185 (221) | 1       |
| 8.0.0b5, uvloop  | 124,44s user 9,75s system 98% cpu 2:16,80 total  | 3650 (254) | 1.15    |
