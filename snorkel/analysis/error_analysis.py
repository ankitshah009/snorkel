from collections import Counter, defaultdict
from typing import Any, List, Mapping, Optional, Sequence, Tuple

import numpy as np

from snorkel.types import ArrayLike

from .utils import arraylike_to_numpy


def error_buckets(
    golds: ArrayLike, preds: ArrayLike, X: Optional[Sequence[Any]] = None
) -> Mapping[Tuple[int, int], Any]:
    """Returns examples (or their indices) bucketed by gold label/pred label combination

    Parameters
    ----------
    gold
        An ArrayLike of gold (int) labels
    pred
        An ArrayLike of (int) predictions
    X
        Optional, a sequence of examples corresponding to golds/preds
        If not provided, indices will be returned instead

    Returns
    -------
    Dict
        A mapping of each error bucket to its corresponding indices/examples
        If X is None, return indices
            instead.

    Returned buckets[i,j] is a list of items with predicted label i and true label j.
    For a binary problem with (1=positive, 2=negative):
        buckets[1,1] = true positives
        buckets[1,2] = false positives
        buckets[2,1] = false negatives
        buckets[2,2] = true negatives
    """
    buckets: Mapping[Tuple[int, int], List[Any]] = defaultdict(list)
    golds = arraylike_to_numpy(golds)
    preds = arraylike_to_numpy(preds)
    for i, (y, l) in enumerate(zip(preds, golds)):
        buckets[y, l].append(X[i] if X is not None else i)
    return dict(buckets)


def confusion_matrix(
    golds: ArrayLike,
    preds: ArrayLike,
    null_pred: bool = False,
    null_gold: bool = False,
    normalize: bool = False,
    pretty_print: bool = True,
) -> np.ndarray:
    """Returns a confusion matrix for a set of golds/preds

    Parameters
    ----------
    golds
        an ArrayLike of gold (int) labels
    preds
        An Arraylike of (int) predictions
    null_pred
        If True, include the row corresponding to null predictions
    null_gold
        If True, include the col corresponding to null gold labels
    normalize
        If True, divide counts by the total number of items
    pretty_print
        If True, pretty-print the matrix before returning

    Returns
    -------
    np.ndarray
        A confusion matrix when mat[p, y] is the number of examples with prediction p
        and true label y (following the typical convention).
    """

    conf = ConfusionMatrix(null_pred=null_pred, null_gold=null_gold)
    golds = arraylike_to_numpy(golds)
    preds = arraylike_to_numpy(preds)
    conf.add(golds, preds)
    mat = conf.compile()

    if normalize:
        mat = mat / len(golds)

    if pretty_print:
        conf.display(normalize=normalize)

    return mat


class ConfusionMatrix(object):
    """
    An iteratively built abstention-aware confusion matrix with pretty printing

    Assumed axes are true label on top, predictions on the side.
    """

    def __init__(self, null_pred: bool = False, null_gold: bool = False) -> None:
        """
        Parameters
        ----------
        null_pred
            If True, include the row corresponding to null predictions
        null_gold
            If True, include the col corresponding to null gold labels
        """
        self.counter = Counter()
        self.mat = None
        self.null_pred = null_pred
        self.null_gold = null_gold

    def __repr__(self) -> str:
        if self.mat is None:
            self.compile()
        return str(self.mat)

    def add(self, golds: ArrayLike, preds: ArrayLike) -> None:
        """
        Parameters
        ----------
        golds
            an ArrayLike of gold (int) labels
        preds
            An Arraylike of (int) predictions
        """
        self.counter.update(zip(golds, preds))

    def compile(self) -> np.ndarray:
        """Compile a confusion matrix from the stored (gold, pred) pairs

        Returns
        -------
        np.ndarray
            The confusion matrix
        """
        k = max([max(tup) for tup in self.counter.keys()]) + 1  # include 0

        mat = np.zeros((k, k), dtype=int)
        for (y, p), v in self.counter.items():
            mat[p, y] = v

        if not self.null_pred:
            mat = mat[1:, :]
        if not self.null_gold:
            mat = mat[:, 1:]

        self.mat = mat
        return mat

    def display(
        self,
        normalize: bool = False,
        indent: int = 0,
        spacing: int = 2,
        decimals: int = 3,
        mark_diag: bool = True,
    ) -> None:
        """Displays a pretty printed confusion matrix

        Parameters
        ----------
        normalize
            If True, divide counts by the total number of items
        indent
            How much to indent on the left side of the matrix
        spacing
            How many spaces to put between columns
        decimals
            How many decimal points to show on floats
        mark_diag
            Whether to highlight the diagonal (correct answers) with an asterisk
        """
        mat = self.compile()
        m, n = mat.shape
        tab = " " * spacing
        margin = " " * indent

        # Print headers
        s = margin + " " * (5 + spacing)
        for j in range(n):
            if j == 0 and not self.null_gold:
                continue
            s += f" y={j} " + tab
        print(s)

        # Print data
        for i in range(m):
            # Skip null predictions row if necessary
            if i == 0 and not self.null_pred:
                continue
            s = margin + f" l={i} " + tab
            for j in range(n):
                # Skip null gold if necessary
                if j == 0 and not self.null_gold:
                    continue
                else:
                    if i == j and mark_diag and normalize:
                        s = s[:-1] + "*"
                    if normalize:
                        s += f"{mat[i,j]/sum(mat[i,1:]):>5.3f}" + tab
                    else:
                        s += f"{mat[i,j]:^5d}" + tab
            print(s)