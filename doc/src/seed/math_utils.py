from scipy.special import gammaln
import math

class MathUtils:
    """Mathematical utility functions for probability and statistics"""

    @staticmethod
    def lchoose(n, k):
        """log of n choose k, i.e., log(C(n, k))."""
        if k < 0 or k > n:
            raise ValueError("k must be between 0 and n")
        return gammaln(n + 1) - gammaln(k + 1) - gammaln(n - k + 1)

    @staticmethod
    def prob_all_types_seen(N, m, n, tol=1e-3):
        """
        Given total N items of m types, each type having q = N/m items,
        we randomly sample n items without replacement.
        What is the probability that we see at least one item of every type?
        This uses the inclusion-exclusion principle to compute the probability:
            sum_{j=0}^m (-1)^j * C(m, j) * [ C(N-j*q, n) / C(N, n) ].
        Let's denote this as sum_{j=0}^m (-1)^j * C1 * [C2 / C3].

        This function returns an approximation of that probability. (if at
        term j, its absolute contribution is less than tol, we stop summing).
        """
        q = N // m
        log_C3 = MathUtils.lchoose(N, n)

        total = 0.0
        for j in range(0, m + 1):
            # If there aren't enough items left to draw n, this term is zero.
            if N - j * q < n:
                break
            # ratio = exp (log_C2 - log_C1)
            log_C2 = MathUtils.lchoose(N - j * q, n)
            ratio = math.exp(log_C2 - log_C3)
            C1 = math.comb(m, j)
            term = ((-1) ** j) * C1 * ratio
            total += term

            if abs(term) < tol:
                break

        return total

    @staticmethod
    def find_n_for_probability(N, m, p_target, tol_term=1e-3):
        """
        Search n = 100, 200, 300, ... until probability >= p_target
        """
        if not (0.0 < p_target < 1.0):
            raise ValueError("p_target must be in (0,1).")

        # Coarse sweep
        n = 100
        while n <= N:
            p = MathUtils.prob_all_types_seen(N, m, n, tol=tol_term)
            print("Probability for n =", n, "is", p)
            if p >= p_target:
                break
            n += 100

        if n > N:
            return None

        return n
