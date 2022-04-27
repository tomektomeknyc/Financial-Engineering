#!/usr/bin/python
# -*- coding: utf-8 -*-

def solve_it(input_data):
    # return a positive integer, as a string
    return '10'

if __name__ == '__main__':
    print('This script submits the integer: %s\n' % solve_it(''))

import math
def calculate_angle(u, v):
  dot_product = np.dot(u, v)

u_mag = np.linalg.norm(u)
v_mag = np.linalg.norm(v)
magnitude = u_mag * v_mag

# math.acos is just the inverse of cos
return math.degrees(math.acos(dot_product / magnitude))
print(calculate_angle([1,1,0], [1,0,1]))
