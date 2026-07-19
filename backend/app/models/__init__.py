# Import all model classes here so anything importing `app.models` (e.g. Alembic's
# env.py) registers every table on Base.metadata for autogenerate to discover.
from app.models.shop import Shop, User  # noqa: F401
from app.models.dataset import UploadedDataset  # noqa: F401
from app.models.sales_record import SalesRecord  # noqa: F401
from app.models.insight import InsightCard  # noqa: F401
from app.models.nl_query import NLQuery  # noqa: F401
