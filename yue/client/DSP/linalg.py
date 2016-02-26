#! python $this
import math
"""
    goals
    solve det(A) for nxn matrix
    solve system Ax = b.

    Linear Algebra with applications by Otto Bretscher
    page 251 nxn determinates (recursive)
    page 283 cramers rule

    Note: for the following indexing into an array is 1-based (like Matlab) instead of from zero
            as in python or C. for the code that follows indexing will be normal.

    det(A) = sum(i=1,N) { (-1)^(i+1) * a_i1 * det(A_i1)  }

    notation:
        a_ij means value at row i and column j
        A_ij means minor of matrix A, result after deleting the ith row and jth col
             the resultant matrix will be of size N-1 x N-1.
        det(A) when A is a 1x1 matrix equals a_11.

    Note: in the code below a_ij equals A[i][j].
    A matrix is defined as an array of row vectors.
"""

def __printm(A):
    print()
    for row in A:
        print (' '.join( [ "%7.2f"%r for r in row ]))

def matrix_row_swap(A,i,j):
    t = A[i]
    A[i] = A[j]
    A[j] = t

def matrix_row_mult(A,i,k):
    A[i] = [ k*item for item in A[i] ]

def matrix_row_addition(A,i,j,k=1):
    """ given a Matrix add row j to row i
        multiplies each element in j by k
        before adding.
    """
    for index,b in enumerate(A[j]):
        A[i][index] += k*b

def _get_abs_row(A,N,y,x):
    """ starting at row y and clumn x,
        look at each row below y
        find the greateset-absolute-value
        and return the row position and value of
        the greatest value.
        note: -10 is greater than 9.
    """
    abs_tmp = 0
    abs_pos = -1
    abs_val = 0
    for t in range(y,N):
        abs_tmp = abs(A[t][x])
        if abs_tmp > abs_val:
            abs_val = abs_tmp
            abs_pos = t

    return abs_val,abs_pos

def matrix_augment(A,b):
    """ return an augmented matrix
        for a linear system Ax=b
        where A is an NxN matrix and x,b are
        both column vectors of length N
        an augmented matrix is an Nx(N+1) matrix
        where each value in b is appended to the
        end of the corresponding row in A.

        for simplicity, b is a row-vector
        instead of a column vector.
    """
    B = [ row + [v,] for row,v in zip(A,b) ]
    return B;

def matrix_row_shift(A,i):
    """
        move row i to the last position
        and shift all rows up
        so that:
        A[i] = A[i+1]
        A[i+1] = A[i+2]
        and lastly:
        A[N-1] = A[i]
        implementation: use bubble sort all the way down.
    """
    for j in range(i,N-1):
        matrix_row_swap(A,j,j+1)

def gauss_jordan(A):
    """

        if A is an augmented matrix of AI, I being the identity matrix
        then the result of the function is to transform Matrix A
        into a new matrix IB where B is the inverse matrix of A.

        if A is an augmented matrix of Ab where b is a vector from
        Ax=b then the solution will be Ix where I is the identity matrix
        and x is the solution to the system.

        problems:
            if there is no solution strange things happen.

            1/3 - (1 - 2/3) may not equal zero.
            this floating point 'bug' is roughly solved by always
            swapping to a row that has the absolute maximum.
            the hope is some number exists that is greater than
            1E16, or some equivaltnly small value that should be zero.

        det(rref(A)) = (-1)^s * (1/k) * det(A) = 1
        det(A) = k/((-1)^s)

    """

    N = len(A) # specifically i want the height here as the width could be anything.
    cy = 0
    for cx in range(N):
        # find the absolute largest non zero row and swap into the cursor position
        max_val,max_pos = _get_abs_row(A,N,cy,cx);
        if max_val == 0: # all entries at and below cursor are zero
            continue # move to next column
        if max_pos != cy and max_pos > 0:
            #print "row swap %d %d"%(cy,max_pos)
            matrix_row_swap(A,cy,max_pos)

        if A[cy][cx] != 0:
            #print "row mult %d by k=%f"%(cy,1.0/A[cy][cx])
            matrix_row_mult(A,cy,1.0/A[cy][cx])
            for i in range(0,N):
                if i == cy: continue;
                # row addition can be optimized when the first i rows are all zero, for the current cy
                matrix_row_addition(A,i,cy,-A[i][cx])
        cy += 1

def solve(A,b):
    """
        use gauss jordan elimination to solve a
        linear system of equations.
        potentially numerically unstable.

        this function is undefined for systems with no solutions.
    """
    B = matrix_augment(A,b)
    gauss_jordan(B)
    return [ row[-1] for row in B ]

