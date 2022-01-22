#from __future__ import annotations

import numpy as np
from lb_pidsim_train.utils import getBinCounts


def chi2_test ( x_obs , 
                x_exp , 
                bins  = 100  , 
                w_obs = None , 
                w_exp = None ) -> np.ndarray:
  """Return the Pearson's chi-squared test of the two input datasets.

  Parameters
  ----------
  x_obs : array_like
    Array containing the observed dataset.

  x_exp : array_like
    Array containing the expected dataset.

  bins : `int`, optional
    Number of equal-width bins in the computed range used to approximate 
    the two distributions with binned data (`100`, by default).

  w_obs : `int` or `float` or array_like, optional
    An array of weights, of the same length as `x_obs`. Each value in `x_obs` 
    only contributes its associated weight towards the bin count (instead of 1).

  w_exp : `int` or `float` or array_like, optional
    An array of weights, of the same length as `x_exp`. Each value in `x_exp` 
    only contributes its associated weight towards the bin count (instead of 1).

  Returns
  -------
  chi2_test : `np.ndarray`
    Array containing the chi-squared test for each feature of the two input datasets.

  See Also
  --------
  lb_pidsim_train.utils.getBinCounts : 
    Internal function used to compute the bin counts of the input datasets.

  lb_pidsim_train.metrics.chi2_test_from_counts : 
    Function used to compute the chi-squared test of two datasets from bin counts.

  Notes
  -----
  In probability theory and statistics, the **Jensen–Shannon divergence** is 
  a method of measuring the similarity between two probability distributions. 
  It is also known as **information radius** (IRad) [1]_ or **total divergence 
  to the average** [2]_.

  Consider the set :math:`M_{+}^{1}(A)` of probability distributions where 
  :math:`A` is a set provided with some :math:`\sigma`-algebra of measurable 
  subsets. In particular we can take :math:`A` to be a finite or countable 
  set with all subsets being measurable. The Jensen–Shannon divergence 
  :math:`D_{JS}: M_{+}^{1}(A) \times M_{+}^{1}(A) \to [0, \infty)` is 
  a symmetrized and smoothed version of the Kullback–Leibler divergence 
  :math:`D_{KL} (F \parallel G)`. It is defined by

  .. math::

    D_{JS} (F \parallel G) = \frac{1}{2} D_{KL} (F \parallel M) + \frac{1}{2} D_{KL} (G \parallel M),
  
  where :math:`M = \frac{1}{2} (F + G)`.

  References
  ----------
  .. [1] C.D. Manning and H. Schutze, "Foundations of Statistical Natural Language 
     Processing", MIT Press, Cambridge, 1999.

  .. [2] I. Dagan, L. Lee and F. Pereira, "Similarity-Based Methods For Word 
     Sense Disambiguation", in Proceedings of the Thirty-Fifth Annual Meeting 
     of the Association for Computational Linguistics and Eighth Conference of 
     the European Chapter of the Association for Computational Linguistics, 
     ACL-EACL 1997.

  Examples
  --------
  >>> import numpy as np
  >>> a = np.random.normal ( 0. , 1., 10000 )
  >>> b = np.random.normal ( 0.5, 1., 10000 )
  >>> from lb_pidsim_train.metrics import chi2_test
  >>> chi2_test ( a, b )
  [0.27883223]
  """
  n_obs , n_exp = getBinCounts (x_obs, x_exp, bins, w_obs, w_exp)
  return chi2_test_from_counts (n_obs, n_exp)


def chi2_test_from_counts (f, g):
  """Return the Pearson's chi-squared test of the two input datasets from bin counts.

  Parameters
  ----------
  f : array_like
    Array containing the bin counts of the observed dataset.

  g : array_like
    Array containing the bin counts of the expected dataset.

  Returns
  -------
  js_div : `np.ndarray`
    Array containing the chi-squared test for each feature of the two input datasets.

  See Also
  --------
  lb_pidsim_train.metrics.JS_div :
    Function used to compute the chi-squared test of two datasets.

  Notes
  -----
  In probability theory and statistics, the **Jensen–Shannon divergence** is 
  a method of measuring the similarity between two probability distributions. 
  It is also known as **information radius** (IRad) [1]_ or **total divergence 
  to the average** [2]_.

  Consider the set :math:`M_{+}^{1}(A)` of probability distributions where 
  :math:`A` is a set provided with some :math:`\sigma`-algebra of measurable 
  subsets. In particular we can take :math:`A` to be a finite or countable 
  set with all subsets being measurable. The Jensen–Shannon divergence 
  :math:`D_{JS}: M_{+}^{1}(A) \times M_{+}^{1}(A) \to [0, \infty)` is 
  a symmetrized and smoothed version of the Kullback–Leibler divergence 
  :math:`D_{KL} (F \parallel G)`. It is defined by

  .. math::

    D_{JS} (F \parallel G) = \frac{1}{2} D_{KL} (F \parallel M) + \frac{1}{2} D_{KL} (G \parallel M),
  
  where :math:`M = \frac{1}{2} (F + G)`.

  References
  ----------
  .. [1] C.D. Manning and H. Schutze, "Foundations of Statistical Natural Language 
     Processing", MIT Press, Cambridge, 1999.

  .. [2] I. Dagan, L. Lee and F. Pereira, "Similarity-Based Methods For Word 
     Sense Disambiguation", in Proceedings of the Thirty-Fifth Annual Meeting 
     of the Association for Computational Linguistics and Eighth Conference of 
     the European Chapter of the Association for Computational Linguistics, 
     ACL-EACL 1997.

  Examples
  --------
  >>> import numpy as np
  >>> a = [15, 33, 59, 93, 101, 85, 68, 42, 18, 5]
  >>> b = [10, 45, 67, 104, 92, 93, 55, 31, 27, 2]
  >>> from lb_pidsim_train.metrics import chi2_test_from_counts
  >>> chi2_test_from_counts ( a, b )
  [0.04641751]
  """
  ## Input samples --> Numpy arrays
  f = np.array (f)
  g = np.array (g)

  ## Promotion to 2-D arrays
  if len (f.shape) == 1:
    f = f [np.newaxis,:]
  if len (g.shape) == 1:
    g = g [np.newaxis,:]

  ## Normalize distributions
  f = f / np.cumsum (f, axis = 1)[:,-1][:,np.newaxis]
  g = g / np.cumsum (g, axis = 1)[:,-1][:,np.newaxis]

  ## Cleaning datasets from 0s
  g = np.where (g > 0, g, 1e-12)
  res = np.where (g != 1e-12, (f - g)**2 / g, 0)

  ## chi-squared test computation
  return np.sum ( res, axis = 1 )



if __name__ == "__main__":
  ## SAMPLE N. 1
  gauss_1 = np.random.normal  ( 0.   , 1.  , size = int(1e6) )
  unif_1  = np.random.uniform ( -0.5 , 0.5 , size = int(1e6) )
  sample_1 = np.c_ [gauss_1, unif_1]

  ## SAMPLE N. 2
  gauss_2 = np.random.normal  ( 0.5  , 1.  , size = int(1e6) )
  unif_2  = np.random.uniform ( -0.4 , 0.6 , size = int(1e6) )
  sample_2 = np.c_ [gauss_2, unif_2]

  binnings = [10, 100, 1000, 10000]
  for bins in binnings:
    js_div = chi2_test (sample_1, sample_2, bins)
    print ( "chi2 test (bins - {:.2e}) : {}" . format (bins, js_div) )