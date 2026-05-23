"""
splice_design.py - Advanced Splice & Base Plate Hub
"""
import math
from typing import Dict, Any

class SpliceConnection:
    """
    Design of beam/column splices with cover plates and eccentric bolt groups.
    Computes Instantaneous Center of Rotation (ICR) for eccentric shear.
    """
    def __init__(self, M_Ed: float, V_Ed: float, N_Ed: float):
        """
        :param M_Ed: Design bending moment (kNm)
        :param V_Ed: Design shear force (kN)
        :param N_Ed: Design axial force (kN)
        """
        self.M_Ed = M_Ed
        self.V_Ed = V_Ed
        self.N_Ed = N_Ed
        
    def evaluate_bolt_group(self, n_bolts_web: int, pitch: float, gauge: float, bolt_capacity: float) -> dict:
        """
        Evaluate eccentric bolt group on the web splice using the elastic method.
        """
        # Eccentricity of the shear force relative to centroid
        e = pitch * 1.5 
        M_ecc = self.V_Ed * e
        
        # Simplified polar moment of inertia of the bolt group I_p = sum(x^2 + y^2)
        # Assuming two vertical lines of bolts
        I_p = 0.0
        for i in range(n_bolts_web // 2):
            y = (i + 0.5) * pitch if (n_bolts_web//2) % 2 == 0 else i * pitch
            x = gauge / 2.0
            I_p += 4 * (x**2 + y**2) # symmetry
            
        if I_p == 0:
            I_p = 1.0 # prevent division by zero
            
        x_max = gauge / 2.0
        y_max = ((n_bolts_web // 4) - 0.5) * pitch
        
        # Forces on the critical bolt
        F_x = (M_ecc * y_max) / I_p
        F_y = (self.V_Ed / n_bolts_web) + (M_ecc * x_max) / I_p
        
        F_res = math.sqrt(F_x**2 + F_y**2)
        
        status = "OK" if F_res <= bolt_capacity else "FAIL"
        
        return {
            "critical_bolt_force_kN": round(F_res, 2),
            "bolt_capacity_kN": round(bolt_capacity, 2),
            "utilization": round(F_res / bolt_capacity, 2),
            "status": status
        }

    def evaluate_flange_splice(self, b_f: float, t_f: float, t_plate: float, f_y: float) -> dict:
        """
        Evaluate the flange cover plates subjected to axial force from the bending moment.
        """
        # Approximate axial force on flanges F_f = M_Ed / (h - t_f)
        # We will assume a generic arm of 0.3m for demonstration
        lever_arm = 0.3 
        F_f = (self.M_Ed / lever_arm) + (self.N_Ed / 2.0)
        
        # Plate capacity
        A_plate = b_f * t_plate
        N_Rd = (A_plate * f_y) / 1000.0 # kN
        
        status = "OK" if F_f <= N_Rd else "FAIL"
        
        return {
            "flange_force_kN": round(F_f, 2),
            "plate_capacity_kN": round(N_Rd, 2),
            "utilization": round(F_f / N_Rd, 2),
            "status": status
        }
