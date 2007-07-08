from __future__ import division
from hedge.tools import \
        cyl_bessel_j, \
        cyl_bessel_j_prime
from math import sqrt, pi, sin, cos, atan2
import cmath




# solution adapters -----------------------------------------------------------
class RealPartAdapter:
    def __init__(self, adaptee):
        self.adaptee = adaptee

    def __len__(self):
        return len(self.adaptee)

    def __call__(self, x):
        return [xi.real for xi in self.adaptee(x)]

class SplitComplexAdapter:
    def __init__(self, adaptee):
        self.adaptee = adaptee

    def __len__(self):
        return len(self.adaptee)*2

    def __call__(self, x):
        ad_x = self.adaptee(x)
        return [xi.real for xi in ad_x] + [xi.imag for xi in ad_x]

class CartesianAdapter:
    def __init__(self, adaptee):
        self.adaptee = adaptee

    def __len__(self):
        return len(self.adaptee)

    def __call__(self, x):
        xy = x[:2]
        r = sqrt(xy*xy)
        phi = atan2(x[1], x[0])

        prev_result = self.adaptee(x)
        result = []
        i = 0
        while i < len(prev_result):
            fr, fphi, fz = prev_result[i:i+3]
            result.extend([
                    cos(phi)*fr - sin(phi)*fphi, # ex
                    sin(phi)*fr + cos(phi)*fphi, # ey
                    fz,
                    ])
            i += 3

        return result




# actual solutions ------------------------------------------------------------
class CylindricalCavityMode:
    """A cylindrical TM cavity mode.

    Taken from:
    J.D. Jackson, Classical Electrodynamics, Wiley.
    3rd edition, 2001.
    ch 8.7, p. 368f.
    """
    
    def __init__(self,  m, n, p, radius, height, epsilon, mu, tm_scale=1):
        try:
            from bessel_zeros import bessel_zeros
        except ImportError:
            print "*** You need to generate the bessel root data file."
            print "*** Execute generate-bessel-zeros.py at the command line."
            raise

        assert m >= 0 and m == int(m)
        assert n >= 1 and n == int(n)
        assert p >= 0 and p == int(p)
        self.m = m
        self.n = n
        self.p = p
        self.phi_sign = 1

        R = self.radius = radius
        d = self.height = height

        self.epsilon = epsilon
        self.mu = mu

        self.t = 0
        self.tm_scale = tm_scale

        x_mn = bessel_zeros[m][n-1]

        self.omega = 1 / sqrt(mu*epsilon) * sqrt(
                x_mn**2 / R**2
                + p**2 * pi**2 / d**2)

        self.gamma_mn = x_mn/R

    def set_time(self, t):
        self.t = t

    def __len__(self):
        return 6

    def __call__(self, x):
        # coordinates -----------------------------------------------------
        xy = x[:2]
        r = sqrt(xy*xy)
        phi = atan2(x[1], x[0])
        z = x[2]

        # copy instance variables for easier access -----------------------
        m = self.m
        p = self.p
        gamma = self.gamma_mn
        phi_sign = self.phi_sign
        omega = self.omega
        d = self.height
        epsilon = self.epsilon

        # common subexpressions -------------------------------------------
        t_scale = self.tm_scale * cmath.exp(-1j * omega * self.t)
        phi_factor = cmath.exp(phi_sign * 1j * m * phi)

        # psi and derivatives ---------------------------------------------
        psi = cyl_bessel_j(m, gamma * r) * phi_factor
        psi_dr = gamma*cyl_bessel_j_prime(m, gamma*r) * phi_factor
        psi_dphi = (cyl_bessel_j(m, gamma * r) 
                * 1/r * phi_sign*1j*m * phi_factor)

        # field components in polar coordinates ---------------------------
        ez   = t_scale * cos(p * pi * z / d) * psi

        e_transverse_factor = (t_scale
                * (-p*pi/(d*gamma**2))
                * sin(p * pi * z / d))

        er   = e_transverse_factor * psi_dr
        ephi = e_transverse_factor * psi_dphi

        hz   = 0j

        # z x grad psi = z x (psi_x, psi_y)   = (-psi_y,   psi_x)
        # z x grad psi = z x (psi_r, psi_phi) = (-psi_phi, psi_r)
        h_transverse_factor = (t_scale
                * 1j*epsilon*omega/gamma**2
                * cos(p * pi * z / d))

        hr   = h_transverse_factor * (-psi_dphi)
        hphi = h_transverse_factor * psi_dr

        return [er, ephi, ez, hr, hphi, hz]

