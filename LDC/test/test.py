from LDC.srs_controller import SrsLdc501

srs = SrsLdc501('GPIB0::2::INSTR', '0', [1,2,3], [1,2,3], 25.0)
srs.connect()
# srs.disconnect()