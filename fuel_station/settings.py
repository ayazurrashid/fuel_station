from pathlib import Path
from decouple import config
from split_settings.tools import include, optional
from fuel_station.components.variables import ENV_DEVELOPMENT
from fuel_station.components.variables import ENV_LOCAL

BASE_DIR = Path(__file__).resolve().parent.parent

PROJECT_ENV = config('PROJECT_ENV', default=ENV_LOCAL)

ADD_CORS = PROJECT_ENV in [ENV_DEVELOPMENT, ENV_LOCAL]

base_settings = [
    'components/common.py',
    'components/databases.py',
    'components/apps.py',
    'components/auth.py',
    'components/cors.py',
    'components/logging.py',
    'components/rest.py',
    # Select the right environment (PROJECT_ENV):
    'environments/%s.py' % PROJECT_ENV,
]

# Include settings:
include(*base_settings)