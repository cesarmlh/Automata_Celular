import numpy as np


class LifeModel:
    """Modelo de Conway: Game of Life."""
    @staticmethod
    def step(grid):
        rows, cols = grid.shape
        new = grid.copy()
        for i in range(rows):
            for j in range(cols):
                total = np.sum(grid[max(0, i-1):min(rows, i+2),
                                    max(0, j-1):min(cols, j+2)]) - grid[i, j]
                if grid[i, j] == 1 and (total < 2 or total > 3):
                    new[i, j] = 0
                elif grid[i, j] == 0 and total == 3:
                    new[i, j] = 1
        return new


class FireModel:
    """Modelo de incendios forestales."""
    @staticmethod
    def step(grid, p_growth=0.01, p_lightning=0.001):
        rows, cols = grid.shape
        new = grid.copy()
        for i in range(rows):
            for j in range(cols):
                if grid[i, j] == 2:
                    new[i, j] = 0
                elif grid[i, j] == 1:
                    neighbors = grid[max(0, i-1):min(rows, i+2),
                                     max(0, j-1):min(cols, j+2)]
                    if np.any(neighbors == 2) or np.random.random() < p_lightning:
                        new[i, j] = 2
                elif grid[i, j] == 0 and np.random.random() < p_growth:
                    new[i, j] = 1
        return new
