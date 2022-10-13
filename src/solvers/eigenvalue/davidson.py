#!/usr/bin/env python3# -*- coding: utf-8 -*-"""Created on Tue Jun  7 13:17:55 2022@author: sampasmann"""import numpy as npimport scipy.linalg as spfrom src.solvers.eigenvalue.maps import SI_Mapdef AxV(V, qmc_data):    """    Linear operator for scattering term (I-L^(-1)S)*phi    """    v       = V[:,-1]    Nx      = qmc_data.Nx    G       = qmc_data.G    Nv      = int(Nx*G)    zed     = np.zeros((Nx,G))    phi_in  = np.reshape(v, (Nx,G))    axv     = (phi_in - SI_Map(zed, phi_in, qmc_data)).reshape(Nv)    V[:,-1] = axv        return Vdef BxV(V, qmc_data):    """    Linear operator for fission term (L^(-1)F*phi)    """    v       = V[:,-1]    Nx      = qmc_data.Nx    G       = qmc_data.G    Nv      = Nx*G    zed     = np.zeros((Nx,G))    phi_in  = np.reshape(v, (Nx,G))    bxv     = SI_Map(phi_in, zed, qmc_data).reshape(Nv)    V[:,-1] = bxv      return Vdef PreConditioner(V, qmc_data, numSweeps=8):    """    Linear operator approximation of L^(-1)S        In this case the preconditioner is a specified number of purely scattering    transport sweeps.    """    v       = V[:,-1]    maxit   = 10    tol     = 1e-6    Nx      = qmc_data.Nx    G       = qmc_data.G    Nv      = Nx*G    zed     = np.zeros((Nx,G))    phi_in  = np.reshape(v, (Nx,G))    for i in range(numSweeps):        phi_in = SI_Map(zed, phi_in, qmc_data)    preC    = phi_in        return preCdef Gram(V,u):    w1  = u - np.dot(V,np.dot(V.T,u))    v1  = w1 / np.linalg.norm(w1)    w2  = v1 - np.dot(V,np.dot(V.T,v1))    v2  = w2 / np.linalg.norm(w2)    V   = np.append(V, v2, axis=1)    return Vdef Davidson(qmc_data, k0=1.0, l=1, m=30, numSweeps=5, tol=1e-6, maxit=30):    """    Parameters    ----------    qmc_data : qmc_data structure    k0 : Float, optional        DESCRIPTION. The default is 1.0.    l : Int, optional        DESCRIPTION. Number of eigenvalues and vectors to solver for The default is 1.    m : Int, optional        DESCRIPTION. Restart parameter. The default is 5.    numSweeps : Int, optional        DESCRIPTION. The default is 5.    tol : Float, optional        DESCRIPTION. The default is 1e-6.    maxit : Int, optional        DESCRIPTION. The default is 30.    Returns    -------    phi : TYPE        DESCRIPTION.    keff :  TYPE        DESCRIPTION.    itt : TYPE        DESCRIPTION.    """        # Davidson Parameters    Nx      = qmc_data.Nx    G       = qmc_data.G    Nv      = int(Nx*G)    u       = qmc_data.source    u       = np.reshape(u, Nv)    V0      = np.array(u/np.linalg.norm(u).T) # orthonormalize initial guess    V       = np.empty((Nv,maxit))    Vsize   = 1    V[:,0]  = V0    k_old   = 0.0    dk      = 1.0    #Lambda0 = 1/k0    #r0      = AxV(V[:,:Vsize], qmc_data) - Lambda0*BxV(V[:,:Vsize], qmc_data) # residual    #r       = r0    itt     = 1    V[:,:Vsize] = PreConditioner(V[:,:Vsize], qmc_data, numSweeps)    # Davidson Routine    while (itt <= maxit) and (dk>=tol):        print(" Davidson Iteration: ", itt)        AV          = np.dot(V[:,:Vsize].T, AxV(V[:,:Vsize], qmc_data)) # Scattering linear operator        BV          = np.dot(V[:,:Vsize].T, BxV(V[:,:Vsize], qmc_data)) # Fission linear operator        [Lambda, w] = sp.eig(AV, b=BV)  # solve for eigenvalues and vectors        idx         = Lambda.argsort()  # get indices of eigenvalues from smallest to largest        Lambda      = Lambda[idx]       # sort eigenvalues from smalles to largest        assert(Lambda.imag.all() == 0.0)# there can't be any imaginary eigenvalues        Lambda      = Lambda[:l].real   # take the real component of the l largest eigenvalues        k           = 1/Lambda        dk          = abs(k - k_old)        print("K Effective: ",k)        print(V[:,:Vsize].shape)        k_old       = k        w           = w[:,idx]          # sort corresponding eigenvector        w           = w[:,:l].real      # take the l largest eigenvectors        u           = np.dot(V[:,:Vsize],w)       # Ritz vectors        res         = AxV(u, qmc_data) - Lambda*BxV(u, qmc_data) # residual        t           = PreConditioner(res, qmc_data, numSweeps)        if (Vsize <= m-l ):            Vsize += 1            V[:,:Vsize] = Gram(V[:,:Vsize-1],t) # appends new orthogonalization to V        else:            Vsize = 2            V[:,:Vsize] = Gram(u,t) # "restarts" by appending to a new array                     if (itt==maxit):            print("Maximum number of iterations")            break        itt += 1        keff = 1/Lambda    phi  = V[:,0]    phi = phi/np.linalg.norm(phi).T    return phi, keff, itt