from motors.stage_manager import StageManager as SM
from typing import Tuple

"""
Eo paired coordinate getter and transformation functions

Measured each stage relative to fixed fiber array s.t.
the FA is the origin
"""


class PairCoords:
    def __init__(self, optical_stage_manager: SM, elec_stage_manager: SM,
                 elec_dims: Tuple):
        """
        Args:
            optical_stage_manager[StageManager] : Optical stage controlleer
            elec_stage_manager[StageManager]    : Electric stage controller
            elec_dims[Tuple(float,float,float)] :
                                                 (x,y,z) Distance away at homed    
        """
    
    def 