#!/usr/bin/python3
import numpy as np
import matplotlib.pyplot as plt
from signal_processing_algorithms.energy_statistics.energy_statistics import e_divisive

y = np.array([3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3,
              3, 3, 3, 3, 3, 3, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 3, 3,
              3, 3, 3, 3, 5, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 1, 3, 3,
              4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4,
              3.9, 3.8, 3.7, 3.6, 5, 3.5, 3.4, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 1, 3, 3,
              3, 3, 3, 3, 3, 3, 2, 2, 2, 2, 2, 2, 3, 3, 3, 3, 3, 3, 3, 3,
              2.9, 2.8, 2.7, 2.6, 2.5, 2.5, 2.5, 2.4, 2.3, 2.3, 2, 2, 2, 2, 2, 2, 2, 2, 3, 3,
              ], dtype=float)

changepoints = e_divisive(y,permutations=1000)
print(changepoints)

x = np.arange(0, len(y))

plt.title("Line graph")
plt.xlabel("X axis")
plt.ylabel("Y axis")
plt.plot(x, y, color="red")
for cp in changepoints:
    plt.plot(cp, y[cp], 'ro', color="blue")
plt.show()
