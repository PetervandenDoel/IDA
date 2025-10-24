from motors.hal.stage_factory import _registry as motors_reg
from NIR.hal.nir_factory import _registry as nir_reg
from SMU.hal.smu_factory import _registry as smu_reg
from LDC.hal.LDC_factory import _registry as ldc_reg

def list_available_drivers(driver_type):
    """
    Get the list of registered drivers for a driver type

    :param driver[str]: Instrument type eg. "SMU", "NIR", "motors"
                        **Registered under names of folders**
    """
    if driver_type == "motors":
        return list(motors_reg.key())
    if driver_type == "NIR":
        return list(nir_reg.key())
    if driver_type == "SMU":
        return list(smu_reg.key())
    if driver_type == "LDC":
        return list(ldc_reg.keys())
    else:
        raise ValueError("Please enter a valid instrument type")