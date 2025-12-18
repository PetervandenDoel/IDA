from NIR.config.nir_config import NIRConfiguration
from NIR.nir_manager import NIRManager

cfg = NIRConfiguration()
nm = NIRManager(cfg)
nm.connect()