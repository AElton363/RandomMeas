#   Copyright 2020 Benoit Vermersch, Andreas Elben, Aniket Rath
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

# Codes to reconstruct the purity via Importance Sampling

import numpy as np
import math
import cmath
from qutip import *
import random 
from scipy import linalg
import sys
sys.path.append("src")
from ObtainMeasurements import *
from AnalyzeMeasurements import *
from PreprocessingImportanceSampling import *

### Initiate Random Generator
a = random.SystemRandom().randrange(2 ** 32 - 1) #Init Random Generator
random_gen = np.random.RandomState(a)

### This script estimates the purity of a noisy GHZ realized in the experiment using uniform sampling and importance sampling from an ideal pure GHZ state
### Capable of simulating noisy GHZ state till N = 25 qubits !!!

N = 15 ## Number of qubits of the GHZ state
d = 2**N ## Hilbert space dimension

# Consider realizing a noisy version of the GHZ state experimentally. Noise given by depolarization noise strength p_depo
p_depo = 0.25

## Theoretical purity esitmates:
p2_exp = (1-p_depo)**2 + (1-(1-p_depo)**2)/d ## purity of the realized noisy GHZ state
p2_theory = 1 ## Purity of the ideal pure GHZ state
fid = (1-p_depo) + p_depo/d ## Fidelity between the ideal and the experimenetal GHZ state

### Creating the ideal pure GHZ state:
GHZ = np.zeros(d)
GHZ[0] = (1/2)**(0.5)
GHZ[-1] = (1/2)**(0.5)
GHZ_state = np.reshape(GHZ, [2]*N)


### Importance sampling provides best performances for Nu ~ O(N) and NM ~O(2^N) !!
Nu = 50 # number of unitaries to be used
NM = d*4 # number of measurements to be performed for each unitary
burn_in = 1 # determines the number of samples to be rejected during metropolis: (nu*burn_in) 
mode = 'CUE'
### Step 1: Preprocessing step for importance sampling Sample Y and Z rotation angles (2N angles for each unitary u)  

# Importance sampling of the angles (theta_is) and (phi_is) using metropolis algorithm from a pure GHZ state
theta_is, phi_is, n_r, N_s, p_IS = MetropolisSampling_pure(N, GHZ_state,Nu, burn_in) 

### Step 2: Perform Randomized measurements classically to get bit string data 
## This step can be replaced by the actual experimentally recorded bit strings for the applied unitaries

Meas_Data_uni = np.zeros((Nu,NM),dtype='int64')
Meas_Data_IS = np.zeros((Nu,NM),dtype='int64')

## Perform randomized measurements using uniformly sampled unitaries
u = [0]*N
for iu in range(Nu):
    print('Data acquisition {:d} % \r'.format(int(100*iu/(Nu))),end = "",flush=True)
    for iq in range(N):
        u[iq] = SingleQubitRotation(random_gen,mode)
    Meas_Data_uni[iu,:] = Simulate_Meas_pseudopure(N, GHZ_state, p_depo, NM, u)
    #Meas_Data[iu,:] = Simulate_Meas_mixed(N, rho, NM, u)
print('Measurement data generated for uniform sampling')

## Perform randomized measurements with the generated the importance sampled unitaries
u = [0]*N
for iu in range(Nu):
    print('Data acquisition {:d} % \r'.format(int(100*iu/(Nu))),end = "",flush=True)
    for iq in range(N):
        u[iq] = SingleQubitRotationIS(theta_is[iq,iu],phi_is[iq,iu])
    Meas_Data_IS[iu,:] = Simulate_Meas_pseudopure(N, GHZ_state, p_depo, NM, u)
    #Meas_Data[iu,:] = Simulate_Meas_mixed(N, rho, NM, u)
print('Measurement data generated for importance sampling')

## Step 3: Estimation of the purities p2_uni and p2_IS
X_uni = np.zeros(Nu)
X_imp = np.zeros(Nu)
for iu in range(Nu):
    print('Postprocessing {:d} % \r'.format(int(100*iu/(Nu))),end = "",flush=True)
    prob = get_prob(Meas_Data_uni[iu,:], N)
    X_uni[iu] = get_X(prob,N,NM)
    prob = get_prob(Meas_Data_IS[iu,:], N)
    X_imp[iu] = get_X(prob,N,NM)

p2_uni = 0 # purity given by uniform sampling
p2_uni = np.mean(X_uni)
p2_IS = 0 # purity given by importance sampling
for iu in range(Nu):
    p2_IS += X_imp[iu]*n_r[iu]/p_IS[iu,0]/N_s

print('Fidelity of the sampler: ', np.round(100*fid,2), '%')
print('p2 (True value) = ', p2_exp)
print('p2 (uniform sampling) = ', p2_uni)
print('p2 (Importance sampling) = ', p2_IS)
print ('Error uniform: ', np.round(100*(np.abs(p2_uni-p2_exp)/p2_exp),2), '%')
print ('Error IS: ', np.round(100*(np.abs(p2_IS-p2_exp)/p2_exp),2), '%')
