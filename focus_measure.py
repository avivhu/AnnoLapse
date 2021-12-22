# From: https://github.com/vismantic-ohtuprojekti/qualipy
# https://raw.githubusercontent.com/vismantic-ohtuprojekti/qualipy/master/qualipy/utils/focus_measure.py

# The MIT License (MIT)
# 
# Copyright (c) 2015 QualiPy developers
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
# 

"""
Python implementations for focus measure operators described
in "Analysis of focus measure operators for shape-from-focus"
(Pattern recognition, 2012) by Pertuz et al.
"""

import cv2
import numpy


def LAPV(img):
    """Implements the Variance of Laplacian (LAP4) focus measure
    operator. Measures the amount of edges present in the image.

    :param img: the image the measure is applied to
    :type img: numpy.ndarray
    :returns: numpy.float32 -- the degree of focus
    """
    return numpy.std(cv2.Laplacian(img, cv2.CV_64F)) ** 2


def LAPM(img):
    """Implements the Modified Laplacian (LAP2) focus measure
    operator. Measures the amount of edges present in the image.

    :param img: the image the measure is applied to
    :type img: numpy.ndarray
    :returns: numpy.float32 -- the degree of focus
    """
    kernel = numpy.array([-1, 2, -1])
    laplacianX = numpy.abs(cv2.filter2D(img, -1, kernel))
    laplacianY = numpy.abs(cv2.filter2D(img, -1, kernel.T))
    return numpy.mean(laplacianX + laplacianY)


def TENG(img):
    """Implements the Tenengrad (TENG) focus measure operator.
    Based on the gradient of the image.

    :param img: the image the measure is applied to
    :type img: numpy.ndarray
    :returns: numpy.float32 -- the degree of focus
    """
    gaussianX = cv2.Sobel(img, cv2.CV_64F, 1, 0)
    gaussianY = cv2.Sobel(img, cv2.CV_64F, 1, 0)
    return numpy.mean(gaussianX * gaussianX +
                      gaussianY * gaussianY)


def MLOG(img):
    """Implements the MLOG focus measure algorithm.

    :param img: the image the measure is applied to
    :type img: numpy.ndarray
    :returns: numpy.float32 -- the degree of focus
    """
    return numpy.max(cv2.convertScaleAbs(cv2.Laplacian(img, 3)))
