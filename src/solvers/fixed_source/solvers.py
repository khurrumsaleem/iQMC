#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Jun  7 13:18:01 2022

@author: sampasmann
"""

import numpy as np
import time
from mpi4py import MPI
from src.solvers.fixed_source.maps import SI_Map, RHS, MatVec_data, MatVec
from src.functions.save_data import SaveData
from scipy.sparse.linalg import gmres, lgmres, bicgstab, LinearOperator

class gmres_counter(object):
    def __init__(self, disp=True):
        self._disp = disp
        self.iter = 0
        self.callbacks = []
    def __call__(self, rk=None):
        self.callbacks.append(rk.copy())
        self.iter += 1
        if self._disp:
            #print(rk)
            if (self.iter>1):
                print("**********************")
                print("Iteration:", self.iter-1, "change: ",np.linalg.norm((rk - self.callbacks[self.iter-2])))
            
            
def Picard(qmc_data,tol=1e-5,maxit=40,save_data=True,report_progress=True):
    """
    Parameters
    ----------
    phi0 : Starting volumetric source
    SI_Map : Source Iteration Map Function
    tol : Iteration tolerance
    maxit : Maximum number of iterations
    qmc_data : Object from init_files
    report_progress: boolean, print progress of iterative method

    Returns
    -------
    None.

    """
    comm    = MPI.COMM_WORLD
    rank    = comm.Get_rank()
    nproc   = comm.Get_size()

    Nx      = qmc_data.Nx
    G       = qmc_data.G
    phi0    = qmc_data.source
    itc     = 0
    diff    = 1.0
    phic    = np.copy(phi0)
    phi     = np.copy(phi0)
    reshist = np.empty(0)
    start = time.time()
    while (itc < maxit) and (diff > tol):
        phi_out = SI_Map(phic, qmc_data)
        phi     = np.reshape(phi_out,(Nx,G))
        diff    = np.linalg.norm((phic-phi))
        reshist = np.append(reshist, diff)
        phic    = np.copy(phi)
        itc += 1
        if (report_progress) and (rank==0):
            print("**********************")
            print("Iteration:", itc, "change: ",diff)
    stop = time.time()
    run_time = stop-start
    if (rank==0):
        if (save_data==True):
            sim_data = SimData(phi_out, run_time, tol, nproc)
            SaveData(qmc_data, sim_data)
    return phi


def FixedSource(qmc_data, solver="LGMRES", tol=1e-5, maxit=100, save_data=True):
    """
    Parameters
    ----------
    qmc_data : TYPE
        DESCRIPTION.
    tol : TYPE, optional
        DESCRIPTION. The default is 1e-5.
    maxit : TYPE, optional
        DESCRIPTION. The default is 50.

    Returns
    -------
    phi : TYPE
        DESCRIPTION.

    """
    comm        = MPI.COMM_WORLD
    rank        = comm.Get_rank()
    nproc       = comm.Get_size()
    
    if (rank==0):
        print("--------- Fixed Source Problem ---------")
        print("Solver:",                             solver)
        print("Material: ",                          qmc_data.material_code)
        print("Random Number Generator: ",           qmc_data.generator)
        print("Number of Particles per Iteration: ", qmc_data.N)
        print("Number of Spatial Cells: ",           qmc_data.Nx)
    
    Nx          = qmc_data.Nx
    G           = qmc_data.G
    Nv          = Nx*G
    start       = time.time()
    matvec_data = MatVec_data(qmc_data)
    A           = LinearOperator((Nv,Nv), 
                              matvec=MatVec,
                              rmatvec=MatVec,
                              matmat= MatVec,
                              rmatmat=MatVec,
                              dtype=float)
    b           = matvec_data[0]
    phi0        = qmc_data.source
    phi0        = np.reshape(phi0,(Nv,1))
    if (solver=="LGMRES"):
        counter     = gmres_counter()
        gmres_out   = lgmres(A,b,x0=phi0,tol=tol,maxiter=maxit,callback=counter)
        phi         = gmres_out[0]
        exitCode    = gmres_out[1]
        phi         = np.reshape(phi, (Nx,G))
    elif (solver=="GMRES"):
        counter     = gmres_counter()
        gmres_out   = gmres(A,b,x0=phi0,tol=tol,maxiter=maxit,callback=counter)
        phi         = gmres_out[0]
        exitCode    = gmres_out[1]
        phi         = np.reshape(phi, (Nx,G))
    elif (solver=="BICGSTAB"):
        counter     = gmres_counter()
        gmres_out   = bicgstab(A,b,x0=phi0,tol=tol,maxiter=maxit,callback=counter)
        phi         = gmres_out[0]
        exitCode    = gmres_out[1]
        phi         = np.reshape(phi, (Nx,G))
    elif (solver=="Picard"):
        phi         = Picard(qmc_data,maxit=maxit,tol=tol,save_data=False)
        exitCode    = 0
    else:
        if (rank==0):
            print(" Invalid Solver ")
            Exception
            
    stop        = time.time()
    run_time    = stop - start
    
    if (rank==0):
        if (save_data):
            sim_data = SimData(phi, run_time, tol, nproc)
            SaveData(qmc_data, sim_data)
        if (exitCode>0):
            print("Convergence to tolerance not achieved: Maximum number of iterations.")
        elif (exitCode<0):
            print("Illegal input or breakdown")
        elif (exitCode==0):
            print("Successful Convergence.")
        
    return phi


def SimData(phi, time, tol, nproc):
    data = {
        "phi": phi,
        "run_time": time,
        "tolerance": tol,
        "nproc": nproc
        }
    return data

    
