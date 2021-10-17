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
from Functions_IS_mixed import *

### Initiate Random Generator
a = random.SystemRandom().randrange(2 ** 32 - 1) #Init Random Generator
random_gen = np.random.RandomState(a)

### This script estimates the topological entanglement entropy S_topo of a state using importance sampling and uniform sampling.

N = 9 ## total number of qubits of the state in study
d = 2**N ## Hilbert space dimension

## load the toric code state:
rho = np.load("N_9_sites_7_11_17_12_16_20_15_21_25.npy") 

## returns the state rho for the considered partition 
def sub_system(rho,part):
    rho = Qobj(rho, [[2]*N,[2]*N])
    if (len(part) == 9):
        rho_traced = rho
    else:
        rho_traced = ptrace(rho,part)
    return rho_traced

## Partitions considered indexed by the qubit numbers of the 9 qubit sub-system
qubit_partitions = [[0,1,5],[2,3,7],[3,6,8],[0,1,2,3,5,7],[0,1,4,5,6,8],[2,3,4,6,7,8],[0,1,2,3,4,5,6,7,8]] ## indexed by thhe respective qubit numbers 
Traced_systems = [[2,3,4,6,7,8],[0,1,2,4,5,7],[0,1,2,4,5,7],[4,6,8],[2,3,7],[0,1,5],[]] ## qubit indices that are traced out for each sub-system
num_partitions = len(qubit_partitions) ## total number of partitions


Nu_uni = 1000 ## number of unitaries used for uniform sampling
NM_uni = 10000 ## number of measurements performed for each uniformly sampled unitary

## could tune these values for each partition of the state. Partitions ordered as given in 'qubit_partitions'
Nu_IS = [5]*6 +[35] ## number of unitaries used for importance sampling for each partition
NM_IS = [100000]*6 + [100000] ## number of measurements done for each importance sampled unitary for each partition
burn_in = 1
mode = 'CUE'

# Could consider realizing a noisy version ofthe state experimentally. Noise given by depolarization noise strength p_depo
p_depo = 0


print('Evalaution of S_topo using uniform sampling with Nu = '+str(Nu_uni)+' and NM = '+str(NM_uni)+' \n ')
## storing purities for each partitions
p2_subsystems_IS = np.zeros(num_partitions)
p2_subsystems_uni = np.zeros(num_partitions)
p2_theory = np.zeros(num_partitions)


### Perform randomized measurements with uniform sampling

Meas_Data_uni = np.zeros((Nu_uni,NM_uni),dtype='int64')
u = [0]*N
for iu in range(Nu_uni):
    print('Data acquisition {:d} % \r'.format(int(100*iu/(Nu_uni))),end = "",flush=True)
    for iq in range(N):
        u[iq] = SingleQubitRotation(random_gen,mode)
    Meas_Data_uni[iu,:] = Simulate_Meas_mixed(N, rho, NM_uni, u)
print('Measurement data generated for uniform sampling')

### Reconstruct purities from measured bitstrings

X = np.zeros((Nu_uni,len(qubit_partitions)))
for iu in range(Nu_uni):
    print('PostProcessing {:d} % \r'.format(int(100*iu/(Nu_uni))),end = "",flush=True)
    prob = get_prob(Meas_Data_uni[iu,:],N)
    for i_part in range(len(qubit_partitions)):
        prob_subsystem = reduce_prob(prob,N,Traced_systems[i_part])
        X[iu,i_part] = get_X(prob_subsystem,len(qubit_partitions[i_part]),NM_uni)
p2_subsystems_uni = np.mean(X,0)

## Evalauting purities with importance sampling

for iparts in range(num_partitions):
    print('Evaluating Importance sampled purity of the sub-system ' + str(qubit_partitions[iparts])+ ' with Nu = '+str(Nu_IS[iparts])+' and NM = '+str(NM_IS[iparts])+' \n ')
    
    N_subsystem = len(qubit_partitions[iparts]) ## number of qubits of the sub-system under study
    d_subsystem = 2**N_subsystem ## Hilbert space dimension
    rho_subsystem = np.array(sub_system(rho,qubit_partitions[iparts])) ## theoretical state modeling the state realized in the experiment
    
    
    ## Theoretical purity esitmates for each concerned partition:
    p2_theory[iparts] = np.real(np.trace(np.dot(rho_subsystem,rho_subsystem)))
    
    ### Step 1: Preprocessing for importance sampling

    # Importance sampling of the angles (theta_is) and (phi_is) using metropolis algorithm of the concerned system
    theta_is, phi_is, n_r, N_s, p_IS = MetropolisSampling_mixed(N_subsystem, rho_subsystem,Nu_IS[iparts], burn_in) 

    ## Perform randomized measurements with the generated importance sampled unitaries
    u = [0]*N
    Meas_Data_IS = np.zeros((Nu_IS[iparts],NM_IS[iparts]),dtype='int64')
    for iu in range(Nu_IS[iparts]):
        print('Data acquisition {:d} % \r'.format(int(100*iu/(Nu_IS[iparts]))),end = "",flush=True)
        for iq in range(N_subsystem):
            u[iq] = SingleQubitRotationIS(theta_is[iq,iu],phi_is[iq,iu])
        Meas_Data_IS[iu,:] = Simulate_Meas_mixed(N_subsystem, rho_subsystem, NM_IS[iparts], u)
    print('Measurement data generated for importance sampling \n')
    
    ## Estimation of the purity p2_IS
    X_imp = np.zeros(Nu_IS[iparts])
    for iu in range(Nu_IS[iparts]):
        print('Postprocessing {:d} % \r'.format(int(100*iu/(Nu_IS[iparts]))),end = "",flush=True)
        prob = get_prob(Meas_Data_IS[iu,:], N_subsystem)
        X_imp[iu] = get_X(prob,N_subsystem,NM_IS[iparts])
    
    p2_IS = 0 # purity given by importance sampling
    for iu in range(Nu_IS[iparts]):
        p2_IS += X_imp[iu]*n_r[iu]/p_IS[iu,0]/N_s
    p2_subsystems_IS[iparts] = np.real(p2_IS)


## Evaluating S_topo for both the sampling methods
S_topo_uni = -1*(np.sum(np.log2(p2_subsystems_uni)[0:3])-(np.sum(np.log2(p2_subsystems_uni)[3:6])) + np.log2(p2_subsystems_uni[6]))
S_topo_IS = -1*(np.sum(np.log2(p2_subsystems_IS)[0:3])-(np.sum(np.log2(p2_subsystems_IS)[3:6])) + np.log2(p2_subsystems_IS[6]))

## some performance summaries and results
## total number of meaurements that gives the number of times the concerned state was prepared in the experiment
 
print('Total number of uniform measurements used: ', Nu_uni*NM_uni)

## total number of importance sampling measurements is given by the sum of 4 different runs of the experiment 
## run(1): Evaluates the purity of partition[0] and its complement
## run(2): Evaluates the purity of partition[1] and its complement
## run(3): Evalautes the purity of partition[2] and its complement
## run(4): Evalautes the purity of the whole state (9 qubits)
print('Total number of IS measurements used: ', 3*Nu_IS[0]*NM_IS[0] + Nu_IS[6]*NM_IS[6])

print('True value of S_topo: ', -1)
print('S_topo (uniform sampling) = ', S_topo_uni)
print('S_topo (Importance sampling) = ', S_topo_IS)
print ('Error uniform: ', np.round(100*(np.abs(S_topo_uni+1)),2), '%')
print ('Error IS: ', np.round(100*(np.abs(S_topo_IS+1)),2), '%')

