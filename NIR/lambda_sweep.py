import logging
import pyvisa
import time
import numpy as np
import struct
from typing import Tuple, Optional, List

logging.basicConfig(level=logging.DEBUG, format='%(funcName)s - %(levelname)s: %(message)s')
pyvisa_logger = logging.getLogger('pyvisa')
pyvisa_logger.setLevel(logging.WARNING)

class LambdaScanProtocol:
    """
    Pass the activate VISA instrument instance, complete
    optical sweep using VISA protocol instead of DLL.
    """
    def __init__(self, inst=None):
        self.inst = inst

    def connect(self):
        """Connect using proven working method."""
        try:
            if self.inst is None:
                logging.error(f"[Lambda Sweep] Please pass a open ressource instance") 

            self.inst.timeout = 30000
        
            # Test connection
            resp = self._send_command("*IDN?").strip()
            logging.info(f"Connected to: {resp}")
            # self.configure_units()
            return resp
            
        except Exception as e:
            logging.error(f"Connection failed: {e}")
            return False
    
    def _send_command(self, command, expect_response=True):
        if not self.inst:
            raise RuntimeError("Not connected")
        try:
            if expect_response:
                self.inst.write(command)
                time.sleep(0.05)
                return self.inst.read().strip()
            else:
                self.inst.write(command)
                return ""
                
        except Exception as e:
            logging.error(f"Command failed: {command}, Error: {e}")
            raise
    
    def _write(self, command):
        """Write command without expecting response."""
        return self._send_command(command, expect_response=False)
    
    def _query(self, command):
        """Query command expecting response."""
        return self._send_command(command, expect_response=True)
    
    def _query_binary(self, command):
        """Query command expecting binary response."""
        if not self.inst:
            raise RuntimeError("Not connected")
        
        try:
            self.inst.write(command)
            time.sleep(0.1)
            raw_data = self.inst.read_raw()
            return raw_data
        
        except Exception as e:
            logging.error(f"Binary query failed: {command}, Error: {e}")
            raise

    def _query_binary_and_parse(self, command):
        if not self.inst:
            raise RuntimeError("Not connected")
        self.inst.write(command)

        # Read header first
        header = self.inst.read_bytes(2)  
        if header[0:1] != b"#":
            raise ValueError("Invalid SCPI block header")

        num_digits = int(header[1:2].decode())
        len_field = self.inst.read_bytes(num_digits)
        data_len = int(len_field.decode())

        # Read binary data in chunks until complete
        data_block = b""
        remaining = data_len
        while remaining > 0:
            chunk = self.inst.read_bytes(min(remaining, 4096))
            data_block += chunk
            remaining -= len(chunk)

        # Flush leftovers 
        try:
            self.inst.read()  # Read trailing \n
        except Exception:
            pass

        data = struct.unpack("<" + "f" * (len(data_block)//4), data_block)
        data = np.array(data)

        if data[0] > 0:
            # W
            data = 10*np.log10(data) + 30 
        return data
    
    def sweep(self):
        return self.optical_sweep(self.start_wavelength, self.stop_wavelength, self.step_size, self.laser_power)
    
    def optical_sweep(self, start_nm, stop_nm, step_nm, laser_power_dbm, averaging_time_s=0.02):
        """Call full optical sweep procedure"""
        try:
            # points calc
            points_f = (float(stop_nm) - float(start_nm)) / float(step_nm)
            points = int(points_f + 1.0000001)  # guard for fp rounding
            stitching = False

            # segmentation width
            if points > 20001:
                stitching = True

            if stitching:
                segments = int(np.ceil(points / 20001.0))
                seg_span = int(np.ceil((stop_nm - start_nm) / segments))  # in nm, positive
                bottom = int(start_nm)
                flag = False
                while bottom <= stop_nm:
                    top = min(bottom + seg_span, stop_nm)
                    self.configure_and_start_lambda_sweep(bottom, top, step_nm, laser_power_dbm, averaging_time_s)
                    self.execute_lambda_scan()
                    wls, ch1, ch2 = self.retrieve_scan_data()
                    if not flag:
                        # First case
                        wavelengths = wls; power_ch1 = ch1; power_ch2 = ch2; flag = True
                    else:
                        # Rest of stitching
                        power_ch1 = np.concatenate([power_ch1, ch1])
                        power_ch2 = np.concatenate([power_ch2, ch2])
                        wavelengths = np.concatenate([wavelengths, wls])
                    bottom = top + step_nm
            else:
                self.configure_and_start_lambda_sweep(start_nm, stop_nm, step_nm, laser_power_dbm, averaging_time_s)
                self.execute_lambda_scan()
                wavelengths, power_ch1, power_ch2 = self.retrieve_scan_data()

            # sanitize
            power_ch1 = np.where(power_ch1 > 0, np.nan, power_ch1)
            power_ch2 = np.where(power_ch2 > 0, np.nan, power_ch2)
            out = {
                'wavelengths_nm': wavelengths,
                'channels_dbm': [power_ch1, power_ch2]
            }
            return out
        except Exception as e:
            logging.error(f"Found error in optical sweep: {e}")
            return {'wavelengths_nm': [], 'channels_dbm': []}
        
    def configure_units(self):
        """Configure all channels to use consistent units."""
        # Set laser source to dBm
        self._write("SOUR0:POW:UNIT 0")  # 0 = dBm
        
        # Set all detector channels to dBm
        self._write("SENS1:CHAN1:POW:UNIT 0")  # 0 = dBm
        self._write("SENS1:CHAN2:POW:UNIT 0")  # 0 = dBm
        
        # # Verify settings
        # source_unit = self._query("SOUR0:POW:UNIT?")
        # det1_unit = self._query("SENS1:CHAN1:POW:UNIT?")
        # det2_unit = self._query("SENS1:CHAN2:POW:UNIT?")
        
        # logging.info(f"Units configured - Source: {source_unit}, Det1: {det1_unit}, Det2: {det2_unit}")
    
    def parse_binary_block(self, raw_data):
        """
        Parse SCPI binary block format: #<H><Len><Block>
        where H = number of digits, Len = number of bytes, Block = data
        """
        try:
            if not raw_data.startswith(b'#'):
                raise ValueError("Not a valid binary block")
            logging.debug(f"raw dogging: {raw_data} \nis it the same?")
            # Get number of digits in length field
            num_digits = int(raw_data[1:2].decode())
            
            # Get length of data block, extract
            data_len = int(raw_data[2:2+num_digits].decode())
            binary_data = raw_data[2+num_digits:2+num_digits+data_len] # everything after header
            
            # Parse as 4-byte floats little endian
            float_data = struct.unpack(
                "<" + "f"*(len(binary_data)//4), binary_data 
            )
            float_data = np.array(float_data) 
            
            if float_data[0] > 0:
                # data is in watts
                float_data = 10*np.log10(float_data) + 30 
            return float_data
            
        except Exception as e:
            logging.error(f"Binary block parsing failed: {e}")
            return None
    
    
    def configure_and_start_lambda_sweep(self, start_nm, stop_nm, step_nm,
                                         laser_power_dbm=-10, avg_time_s=0.01):
        try:
            # Convert to meters for SCPI commands
            self.start_wavelength = start_nm * 1e-9
            self.stop_wavelength = stop_nm * 1e-9
            self.step_size = str(step_nm) + "NM" 
            self.laser_power = laser_power_dbm
            self.averaging_time = avg_time_s

            # Calculate number of points
            self.num_points = int((stop_nm - start_nm) / step_nm) + 1
            self.step_width_nm = step_nm 

            # 1. Clear system and set power
            # self._write("*CLS")
            self._write(f"SOUR0:POW {laser_power_dbm}")
            time.sleep(0.1)
            self._write("SOUR0:POW:STAT ON")
            time.sleep(0.1)
            # 2. Initial wavelength
            self._write(f"SOUR0:WAV {self.start_wavelength}")
            time.sleep(0.1)
            # 3. Configure sweep
            self._write("SOUR0:WAV:SWE:MODE CONT")
            time.sleep(0.1)
            self._write(f"SOUR0:WAV:SWE:STAR {self.start_wavelength}")
            time.sleep(0.1)            
            self._write(f"SOUR0:WAV:SWE:STOP {self.stop_wavelength}")
            time.sleep(0.1)            
            self._write(f"SOUR0:WAV:SWE:STEP {self.step_width_nm}NM")
            time.sleep(0.1)
            self._write("SOUR0:WAV:SWE:REP ONEW")
            time.sleep(0.1)
            self._write("SOUR0:WAV:SWE:CYCL 1")
            time.sleep(0.1)
            # 4. Configure logging
            self._write("SENS1:FUNC 'POWer'")
            time.sleep(0.1)
            self._write(f"SENS1:FUNC:PAR:LOGG {self.num_points},{avg_time_s}")
            time.sleep(0.1)
            self._write("SENS1:FUNC:STAT LOGG,START")
            
            # 5. Start sweep
            self._write("SOUR0:WAV:SWE:STAT START")
            _ = self._query('*OPC?').strip()
            logging.info("Lambda sweep started.")
            return True
            
        except Exception as e:
            logging.error(f"Failed to configure and start lambda sweep: {e}")
            err = self._query("SYST:ERR?")
            logging.error(f"Instrument error: {err}")
            return False
   
    # def execute_lambda_scan(self):
    #     """
    #     Execute the complete lambda scan with data logging.
    #     """
    #     try: 
    #         # Monitor sweep progress
    #         sweep_complete = False
    #         flag = True
    #         scan_start_time = time.time()
    #         timeout = 300  # 5 minute timeout
            
    #         while not sweep_complete and (time.time() - scan_start_time) < timeout:
    #             # Check sweep status
    #             sweep_status = self._query("SOUR0:WAV:SWE:STAT?").strip()
    #             time.sleep(0.15)
    #             # Check logging function status
    #             func_status = self._query("SENS1:CHAN1:FUNC:STAT?").strip()
    #             time.sleep(0.15)
    #             if "COMPLETE" in func_status:
    #                 sweep_complete = True
                
    #             time.sleep(1.0)  # Check every second
            
    #         if time.time() - scan_start_time >= timeout:
    #             logging.error("Lambda scan timed out")
    #             return False
            
    #         logging.info("Lambda scan completed successfully")
    #         return True
            
    #     except Exception as e:
    #         logging.error(f"Lambda scan execution failed: {e}")
    #         error = self._query("SYST:ERR?")
    #         logging.error(f"System error: {error}")
    #         return False
    
    def execute_lambda_scan(self):
        """
        Execute the complete lambda scan with data logging.
        Uses *OPC? to wait for sweep+logging to fully complete.
        """
        try:
            # Estimate how long this segment will take
            # N points * averaging time + 10s margin
            if self.num_points is not None and self.averaging_time is not None:
                est_time_s = self.num_points * self.averaging_time + 30.0
            else:
                est_time_s = 30.0  # fallback

            # Ensure VISA timeout is long enough
            if self.inst.timeout < est_time_s * 1000:
                self.inst.timeout = int(est_time_s * 1000)

            # ---- WAIT FOR SWEEP + LOGGING IN ONE GO ----
            # This will block until the sweep engine AND the logging engine finish.
            _ = self._query("*OPC?").strip()

            logging.info("Lambda scan completed successfully")
            return True

        except Exception as e:
            logging.error(f"Lambda scan execution failed: {e}")

            # Try to un-stuff the I/O if possible
            try:
                self.inst.clear()
                self._write("*CLS")
            except Exception:
                pass

            return False
    def retrieve_scan_data(self):
        """
        Retrieve logged data from a measurement, without stitching
        """
        try:
            logging.info("[NEW] Attempting to retrieve logged binary data...")
            time.sleep(1) # give some time to stop the logging

            # Try to get the logged data
            raw_data = self._query_binary_and_parse("SENS1:CHAN1:FUNC:RES?") # CORRECT DATAAAAAAAAAAAAAAAAAAAAA
            time.sleep(0.4) 
            rd2 = self._query_binary_and_parse("SENS1:CHAN2:FUNC:RES?")
            logging.debug(f"rawdata: {raw_data}\n s2: {rd2}")
            # time.sleep(0.4)

            # Parse the binary block
            power_data = raw_data # self.parse_binary_block(raw_data)
            pow_data = rd2  # self.parse_binary_block(rd2)

            if power_data is not None and len(power_data) > 0:
                # Calculate corresponding wavelengths
                wavelengths_nm = np.linspace(
                    self.start_wavelength * 1e9,
                    self.stop_wavelength * 1e9,
                    len(power_data)
                )
                return wavelengths_nm, power_data, pow_data
            else:
                logging.error("No valid power data retrieved from logging")
                return None, None, None
                
        except Exception as e:
            logging.error(f"Logged data retrieval failed: {e}")
            return None, None, None
        
    def cleanup_scan(self):
        """Clean up after scan - stop functions and turn off laser."""
        try:
            # Stop logging function
            self._write("SENS1:CHAN1:FUNC:STAT LOGG,STOP")
            
            # Stop sweep
            self._write("SOUR0:WAV:SWE:STAT STOP")
            
            # Turn off laser
            self._write("SOUR0:POW:STAT OFF")
            
            logging.info("Scan cleanup complete")
            
        except Exception as e:
            logging.error(f"Cleanup failed: {e}")
    
    def disconnect(self):
        """Safely disconnect from instrument."""
        try:
            if self.inst:
                self.cleanup_scan()
                self.inst = None
            logging.info("Disconnected successfully")
            return True
        except Exception as e:
            logging.error(f"Error during disconnect: {e}")
            return False
        