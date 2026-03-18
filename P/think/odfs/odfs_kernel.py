"""P/think/odfs/odfs_kernel.py — Variable Depth Processing kernel (VDP + Runge-Kutta)."""
from __future__ import annotations
import math, random
from dataclasses import dataclass

ODFS_FIELDS = ["emotion","logic","reflection","visual","language","intuition"]
R_MAX  = 10.0
K_MAX  = 15
TAU1   = 0.6   # ASSIMILATE threshold
TAU2   = 0.2   # EXCRETE threshold
QUARANTINE_MAX = 6
NOISE_SCALE = 0.02

# OMEGA coupling (shared default)
OMEGA_DEFAULT = [
    [0.00, 0.25, 0.25, 0.25, 0.25, 0.75],  # emotion
    [0.25, 0.00, 0.75, 0.25, 0.25, 0.25],  # logic
    [0.25, 0.75, 0.00, 0.25, 0.25, 0.25],  # reflection
    [0.25, 0.25, 0.25, 0.00, 0.65, 0.25],  # visual
    [0.25, 0.25, 0.25, 0.65, 0.00, 0.25],  # language
    [0.75, 0.25, 0.25, 0.25, 0.25, 0.00],  # intuition
]

@dataclass
class ODFSReport:
    R_final:      list        # [6] final field values
    phi_eff:      float       # sum(R_final)
    rho_U:        float       # phi_eff / (6 * R_max)
    S_id:         float       # cosine(R,C_pos) - cosine(R,C_neg)
    S_combined:   float       # 0.5*rho_U + 0.5*max(0,S_id)
    verdict:      str         # ASSIMILATE | QUARANTINE | EXCRETE
    iterations:   int
    stream_awareness: str = None
    stream_spin:      str = None

def _cosine(a: list, b: list) -> float:
    dot = sum(x*y for x,y in zip(a,b))
    na  = math.sqrt(sum(x**2 for x in a))
    nb  = math.sqrt(sum(y**2 for y in b))
    if na == 0 or nb == 0: return 0.0
    return dot / (na * nb)

def _rk4_step(R: list, Omega: list, dt: float = 0.1) -> list:
    """One Runge-Kutta step: dR/dt = Omega @ R - R"""
    def dR(r): return [sum(Omega[i][j]*r[j] for j in range(6)) - r[i] for i in range(6)]
    k1 = dR(R)
    k2 = dR([R[i]+0.5*dt*k1[i] for i in range(6)])
    k3 = dR([R[i]+0.5*dt*k2[i] for i in range(6)])
    k4 = dR([R[i]+dt*k3[i]     for i in range(6)])
    return [R[i] + dt/6*(k1[i]+2*k2[i]+2*k3[i]+k4[i]) for i in range(6)]

def run_odfs(R_0: list, Omega: list, C_pos: list, C_neg: list,
             tau1: float = TAU1, tau2: float = TAU2,
             rng: random.Random = None) -> ODFSReport:
    """
    Variable Depth Processing (VDP) + Runge-Kutta.
    Runs until convergence or K_MAX steps.
    dR/dt = Omega @ R - R + noise
    """
    if rng is None: rng = random.Random()
    R = [min(R_MAX, max(0.0, x)) for x in R_0]

    for k in range(K_MAX):
        noise = [rng.gauss(0, NOISE_SCALE) for _ in range(6)]
        R_new = _rk4_step(R, Omega)
        R     = [min(R_MAX, max(0.0, R_new[i]+noise[i])) for i in range(6)]

    phi_eff    = sum(R)
    rho_U      = phi_eff / (6 * R_MAX)
    S_id       = _cosine(R, C_pos) - _cosine(R, C_neg)
    S_combined = 0.5 * rho_U + 0.5 * max(0.0, S_id)

    if S_combined > tau1:
        verdict = "ASSIMILATE"
    elif S_combined < tau2:
        verdict = "EXCRETE"
    else:
        # Quarantine: retry up to QUARANTINE_MAX times with nudged R_0
        for q in range(QUARANTINE_MAX):
            nudge = [R_0[i] + rng.gauss(0, 0.3) for i in range(6)]
            nudge = [min(R_MAX, max(0.0, x)) for x in nudge]
            report = run_odfs(nudge, Omega, C_pos, C_neg,
                              tau1=tau1, tau2=tau2, rng=rng)
            if report.verdict != "QUARANTINE":
                return report
        verdict = "QUARANTINE"

    return ODFSReport(R_final=R, phi_eff=phi_eff, rho_U=rho_U,
                      S_id=S_id, S_combined=S_combined,
                      verdict=verdict, iterations=K_MAX)
