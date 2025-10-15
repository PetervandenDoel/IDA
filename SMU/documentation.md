## Integration documentation from PyOptomip 

Not that many methods

set voltage
set current
set lims -- I, V, P

get voltage A, B
get current A, B
get resistance A, B

ivsweep

Keithley 2400 -- Implements SCPI over VISA to a 2400
Keithley 2600 -- Keithley2600 third party wrapper (TSP-wrapped) and raw VISA/TSP commands

                 Keithley2600 API does not support automated sweeps (According to code-wise documentation)


Contact check -- Built in exluding (2604B Ida lol, 2614B, 2634B) 